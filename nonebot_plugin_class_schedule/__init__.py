"""nonebot-plugin-class-schedule - 课程表插件

一个功能完善的 NoneBot2 课程表插件
"""

from nonebot import on_command, on_startswith, require
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata
from datetime import date, timedelta
from importlib.util import find_spec

from .config import Config

try:
    if find_spec("nonebot_plugin_htmlrender") is not None:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import html_to_pic
        HAS_HTMLRENDER = True
    else:
        HAS_HTMLRENDER = False
except Exception:
    HAS_HTMLRENDER = False

from .manager import ScheduleManager
from .utils import (
    calculate_week_info,
    parse_day_input,
    day_to_chinese,
    format_day_output,
    format_weekly_overview,
    format_my_schedule,
    format_periods,
    get_current_period,
    format_now_output,
    format_next_output,
    WEEKDAY_NAMES,
    WEEKDAY_FULL,
)
from .templates import (
    render_day_schedule_html,
    render_now_course_html,
    render_next_course_html,
    render_week_overview_html,
    render_my_schedule_html,
)
from .parser import (
    parse_schedule_text,
    validate_schedule,
    format_schedule_for_review,
    IMPORT_COMMAND_GUIDE,
    IMPORT_FORMAT,
)
from .schedule_parser import (
    parse_schedule_text as parse_time_schedule,
    validate_schedule as validate_time_schedule,
    format_schedule_for_review as format_time_schedule_for_review,
    schedule_to_dict,
    SCHEDULE_IMPORT_GUIDE,
)
from .holidays import is_holiday, get_holiday_name, get_workday_reason, get_next_holiday

__plugin_meta__ = PluginMetadata(
    name="课程表插件",
    description="课程表查询、课前提醒、节假日识别",
    usage="发送 /课程表帮助 查看帮助",
    type="application",
    homepage="https://github.com/INKT-love/nonebot-plugin-class-schedule",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "INKT-love",
        "version": "1.0.4",
    },
)

# 初始化管理器
manager = ScheduleManager()

# ===== 帮助文本 =====

HELP_TEXT = """\
课程表插件 帮助

【实时查询】
  /现在什么课    当前节次课程（上课中/课间/放学）
  /等会什么课    下一节课程及倒计时

【每日查询】
  /今天什么课    今日课程 (别名: /课表)
  /明天什么课    明日课程
  /周一 ~ /周五  直接查询某天课程

【设置】
  /课表风格 文字  切换为文字输出
  /课表风格 图片  切换为图片输出
  /课前提醒 开    开启课前提醒（私聊通知）
  /课前提醒 关    关闭提醒
  /课前提醒 提前5分钟  设置提前时间
  /假期订阅 开    开启假期提醒（提前5天）
  /假期订阅 关    关闭假期提醒

【课表导入】
  /导入课表        导入课表
  /确认导入        确认导入课表（也可发 /确定导入）
  /取消导入        取消导入

【作息表导入】
  /导入作息表      导入作息表
  /确认导入作息    确认导入作息表
  /取消导入作息    取消导入作息

【其他】
  /放假没  查询今天是否放假/下一个假期
  /查课 <课目>   搜索某门课今天在第几节

【汇总查询】
  /本周课表      本周一到周五概览
  /第几周        当前第几周及单双周
  /我的课表      查看完整课表

发送 /课程表帮助 或 /class help 查看本帮助"""


# ===== 辅助函数 =====

def _load_schedule(user_id: str) -> tuple:
    """加载用户课表，返回 (schedule, error_msg)。"""
    schedule = manager.get_schedule(user_id)
    if schedule is None:
        return None, (
            "你还没有课表哦~\n\n"
            "导入方式:\n"
            "  1. 按以下格式发送课表给管理员（或直接发给本机器人）:\n\n"
            "  周一：\n"
            "  早读 物理（钱晓晶）\n"
            "  第1节 生物(张建坤)\n"
            "  ...\n"
            "  周二：\n"
            "  ...\n\n"
            "  2. 管理员会帮你导入，导入后即可使用所有查询命令\n\n"
            "  发送 /课程表帮助 查看所有可用命令"
        )
    if not isinstance(schedule, dict):
        return None, "课表数据异常，请联系管理员检查。"
    if "semester_start" not in schedule:
        return None, "课表缺少学期起始日期 (semester_start)，请联系管理员完善。"
    return schedule, None


async def _send_output(bot: Bot, event: MessageEvent, user_id: str, text: str, html: str = None):
    """根据用户偏好发送文字或图片输出。"""
    style = manager.get_user_style(user_id)
    
    if style == "image" and HAS_HTMLRENDER and html:
        try:
            pic = await html_to_pic(
                html=html,
                viewport={"width": 800, "height": 10},
                device_scale_factor=2.0,
            )
            await bot.send(event, MessageSegment.image(pic))
            return
        except Exception as e:
            logger.warning(f"图片渲染失败，回退到文字: {e}")
    
    await bot.send(event, text)


# 导入模式状态
_import_mode: dict = {}
_import_schedule_mode: dict = {}


# ===== 命令注册 =====

help_cmd = on_command("课程表帮助", aliases={"class help"}, priority=5)
style_cmd = on_command("课表风格", priority=5)
reminder_cmd = on_command("课前提醒", priority=5)
holiday_reminder_cmd = on_command("假期订阅", priority=5)
holiday_cmd = on_command("放假没", aliases={"节假日", "今天放假吗"}, priority=5)
import_cmd = on_command("导入课表", aliases={"导入", "设置课表"}, priority=5)
cancel_import_cmd = on_command("取消导入", priority=5)
confirm_import_cmd = on_command("确认导入", aliases={"确定导入"}, priority=5)
import_schedule_cmd = on_command("导入作息表", aliases={"作息表导入", "导入作息"}, priority=5)
cancel_schedule_cmd = on_command("取消导入作息", priority=5)
confirm_schedule_cmd = on_command("确认导入作息", aliases={"确定导入作息"}, priority=5)
now_cmd = on_command("现在什么课", aliases={"正在上什么课"}, priority=5)
next_cmd = on_command("等会什么课", aliases={"下一节什么课"}, priority=5)
search_cmd = on_command("查课", priority=5)
today_cmd = on_command("今天什么课", aliases={"课表"}, priority=5)
tomorrow_cmd = on_command("明天什么课", priority=5)
week_cmd = on_command("本周课表", priority=5)
weeknum_cmd = on_command("第几周", priority=5)
my_schedule_cmd = on_command("我的课表", priority=5)

# 支持多种格式: /周几 周一, /周一, /星期一, /周一课表
monday_cmd = on_command("周一", aliases={"星期一", "周一课表", "星期一课表"}, priority=5)
tuesday_cmd = on_command("周二", aliases={"星期二", "周二课表", "星期二课表"}, priority=5)
wednesday_cmd = on_command("周三", aliases={"星期三", "周三课表", "星期三课表"}, priority=5)
thursday_cmd = on_command("周四", aliases={"星期四", "周四课表", "星期四课表"}, priority=5)
friday_cmd = on_command("周五", aliases={"星期五", "周五课表", "星期五课表"}, priority=5)
saturday_cmd = on_command("周六", aliases={"星期六", "周六课表", "星期六课表"}, priority=5)
sunday_cmd = on_command("周日", aliases={"星期日", "周末", "周日课表", "星期日课表"}, priority=5)


# ===== 导入课表命令 =====

@import_cmd.handle()
async def handle_import(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """引导用户导入课表。"""
    try:
        user_id = str(event.user_id)
        arg = args.extract_plain_text().strip()
        
        if arg:
            courses, errors = parse_schedule_text(arg)
            if not courses:
                await bot.send(event, f"无法识别课表内容\n{IMPORT_COMMAND_GUIDE}")
                return
            
            _import_mode[user_id] = {
                "mode": "confirm",
                "courses": courses,
                "text": arg,
            }
            
            preview = format_schedule_for_review(courses)
            warnings = validate_schedule(courses)
            warning_text = ""
            if warnings:
                warning_text = "\n\n提示:\n" + "\n".join(f"• {w}" for w in warnings)
            
            await bot.send(
                event,
                f"{preview}{warning_text}\n\n"
                f"共识别 {len(courses)} 门课\n"
                "确认导入？回复 /确认导入 保存\n"
                "回复 /取消导入 取消"
            )
        else:
            _import_mode[user_id] = {"mode": "waiting"}
            await bot.send(event, IMPORT_COMMAND_GUIDE)
            
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/导入课表 error: {e}")
        await bot.send(event, f"操作失败: {e}")


@cancel_import_cmd.handle()
async def handle_cancel_import(bot: Bot, event: MessageEvent):
    """取消导入。"""
    try:
        user_id = str(event.user_id)
        if user_id in _import_mode:
            del _import_mode[user_id]
        await bot.send(event, "已取消导入")
    except Exception as e:
        logger.error(f"/取消导入 error: {e}")


# 接收课表文本（当用户处于 waiting 模式时，匹配以星期关键字开头的消息）
_import_text_matcher = on_startswith(("周一", "周二", "周三", "周四", "周五", "周六", "周日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日", "早读", "第1节", "第2节"), priority=6)

@_import_text_matcher.handle()
async def handle_import_text(bot: Bot, event: MessageEvent):
    """接收用户发送的课表文本。"""
    try:
        user_id = str(event.user_id)

        # 只处理处于 waiting 模式的用户
        if user_id not in _import_mode or _import_mode[user_id].get("mode") != "waiting":
            return

        text = event.get_plaintext().strip()

        if not text:
            return

        # 尝试解析
        courses, errors = parse_schedule_text(text)
        if not courses:
            await bot.send(event, f"无法识别课表内容，请检查格式\n{IMPORT_COMMAND_GUIDE}")
            return

        # 进入确认模式
        _import_mode[user_id] = {
            "mode": "confirm",
            "courses": courses,
            "text": text,
        }

        preview = format_schedule_for_review(courses)
        warnings = validate_schedule(courses)
        warning_text = ""
        if warnings:
            warning_text = "\n\n提示:\n" + "\n".join(f"• {w}" for w in warnings)

        await bot.send(
            event,
            f"{preview}{warning_text}\n\n"
            f"共识别 {len(courses)} 门课\n"
            "确认导入？回复 /确认导入 保存\n"
            "回复 /取消导入 取消"
        )

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"导入课表文本处理 error: {e}")
        await bot.send(event, f"处理失败: {e}")


# 接收作息表文本（匹配以时间或节次关键字开头的消息）
_import_schedule_text_matcher = on_startswith(("早读", "第1节", "第2节", "第3节", "第4节", "第5节", "第6节", "第7节", "第8节", "晚自习", "午休", "0", "1", "2", "3", "4", "5", "6", "7"), priority=6)

@_import_schedule_text_matcher.handle()
async def handle_import_schedule_text(bot: Bot, event: MessageEvent):
    """接收用户发送的作息表文本。"""
    try:
        user_id = str(event.user_id)

        # 只处理处于 waiting 模式的用户
        if user_id not in _import_schedule_mode or _import_schedule_mode[user_id].get("mode") != "waiting":
            return

        text = event.get_plaintext().strip()

        if not text:
            return

        # 尝试解析
        schedule, errors = parse_time_schedule(text)
        if not schedule:
            await bot.send(event, f"无法识别作息表内容，请检查格式\n{SCHEDULE_IMPORT_GUIDE}")
            return

        # 进入确认模式
        _import_schedule_mode[user_id] = {
            "mode": "confirm",
            "schedule": schedule,
            "text": text,
        }

        preview = format_time_schedule_for_review(schedule)
        warnings = validate_time_schedule(schedule)
        warning_text = ""
        if warnings:
            warning_text = "\n\n提示:\n" + "\n".join(f"• {w}" for w in warnings)

        await bot.send(
            event,
            f"{preview}{warning_text}\n\n"
            f"共识别 {len(schedule)} 个时间段\n"
            "确认导入？回复 /确认导入作息 保存\n"
            "回复 /取消导入作息 取消"
        )

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"导入作息表文本处理 error: {e}")
        await bot.send(event, f"处理失败: {e}")



@confirm_import_cmd.handle()
async def handle_confirm_import(bot: Bot, event: MessageEvent):
    """确认导入课表。"""
    try:
        user_id = str(event.user_id)
        
        if user_id not in _import_mode:
            await bot.send(event, "没有待确认的导入，请先 /导入课表")
            return
        
        data = _import_mode[user_id]
        if data.get("mode") != "confirm":
            await bot.send(event, "没有待确认的导入，请先 /导入课表")
            return
        
        courses = data["courses"]
        
        today = date.today()
        schedule = {
            "semester_start": today.strftime("%Y-%m-%d"),
            "total_weeks": 20,
            "courses": courses,
        }
        
        manager.save_schedule(user_id, schedule)
        
        course_count = len(courses)
        
        # 检查是否导入了作息表
        prefs = manager._prefs_cache.get(user_id, {})
        has_schedule = "custom_schedule" in prefs and prefs["custom_schedule"]
        
        del _import_mode[user_id]
        
        if has_schedule:
            await bot.send(event, f"课表导入成功！共 {course_count} 门课\n\n发送 /我的课表 查看完整课表")
        else:
            await bot.send(event, f"课表导入成功！共 {course_count} 门课\n\n建议发送 /导入作息表 导入作息表，这样 /现在什么课 和 /等会什么课 才能正常工作")
        
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/确认导入 error: {e}")
        await bot.send(event, f"导入失败: {e}")


# ===== 导入作息表命令 =====

@import_schedule_cmd.handle()
async def handle_import_schedule(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """引导用户导入作息表。"""
    try:
        user_id = str(event.user_id)
        arg = args.extract_plain_text().strip()
        
        if arg:
            schedule, errors = parse_time_schedule(arg)
            if not schedule:
                await bot.send(event, f"无法识别作息表内容\n{SCHEDULE_IMPORT_GUIDE}")
                return
            
            _import_schedule_mode[user_id] = {
                "mode": "confirm",
                "schedule": schedule,
                "text": arg,
            }
            
            preview = format_time_schedule_for_review(schedule)
            warnings = validate_time_schedule(schedule)
            warning_text = ""
            if warnings:
                warning_text = "\n\n提示:\n" + "\n".join(f"• {w}" for w in warnings)
            
            await bot.send(
                event,
                f"{preview}{warning_text}\n\n"
                f"共识别 {len(schedule)} 个时间段\n"
                "确认导入？回复 /确认导入作息 保存\n"
                "回复 /取消导入作息 取消"
            )
        else:
            _import_schedule_mode[user_id] = {"mode": "waiting"}
            await bot.send(event, SCHEDULE_IMPORT_GUIDE)
            
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/导入作息表 error: {e}")
        await bot.send(event, f"操作失败: {e}")


@cancel_schedule_cmd.handle()
async def handle_cancel_schedule_import(bot: Bot, event: MessageEvent):
    """取消导入作息表。"""
    try:
        user_id = str(event.user_id)
        if user_id in _import_schedule_mode:
            del _import_schedule_mode[user_id]
        await bot.send(event, "已取消导入作息表")
    except Exception as e:
        logger.error(f"/取消导入作息 error: {e}")


@confirm_schedule_cmd.handle()
async def handle_confirm_schedule_import(bot: Bot, event: MessageEvent):
    """确认导入作息表。"""
    try:
        user_id = str(event.user_id)
        
        if user_id not in _import_schedule_mode:
            await bot.send(event, "没有待确认的导入，请先 /导入作息表")
            return
        
        data = _import_schedule_mode[user_id]
        if data.get("mode") != "confirm":
            await bot.send(event, "没有待确认的导入，请先 /导入作息表")
            return
        
        schedule = data["schedule"]
        time_schedule = schedule_to_dict(schedule)
        
        if user_id not in manager._prefs_cache:
            manager._prefs_cache[user_id] = {}
        manager._prefs_cache[user_id]["custom_schedule"] = time_schedule
        manager._save_preferences()
        
        del _import_schedule_mode[user_id]
        
        period_count = len(schedule)
        
        # 检查是否导入了课表
        has_courses = manager.get_schedule(user_id) is not None
        
        if has_courses:
            await bot.send(event, f"作息表导入成功！共 {period_count} 个时间段\n\n现在 /现在什么课 和 /等会什么课 可以正常工作了")
        else:
            await bot.send(event, f"作息表导入成功！共 {period_count} 个时间段\n\n建议发送 /导入课表 导入课程表，这样就可以使用 /现在什么课 等查询功能了")
        
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/确认导入作息 error: {e}")
        await bot.send(event, f"导入失败: {e}")


# ===== 帮助命令 =====

@help_cmd.handle()
async def handle_help(bot: Bot, event: MessageEvent):
    """显示帮助信息。"""
    await bot.send(event, HELP_TEXT)


# ===== 课表风格命令 =====

@style_cmd.handle()
async def handle_style(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """设置输出风格。"""
    try:
        user_id = str(event.user_id)
        arg = args.extract_plain_text().strip().lower()
        
        if arg in ("文字", "text"):
            manager.set_user_style(user_id, "text")
            await bot.send(event, "已切换为文字输出模式")
        elif arg in ("图片", "image"):
            if not HAS_HTMLRENDER:
                await bot.send(event, "图片输出依赖 nonebot-plugin-htmlrender，请安装后再切换。")
                return
            manager.set_user_style(user_id, "image")
            await bot.send(event, "已切换为图片输出模式")
        else:
            current = manager.get_user_style(user_id)
            await bot.send(
                event,
                f"当前输出风格: {current}\n\n"
                "使用方法:\n"
                "  /课表风格 文字  切换为文字输出\n"
                "  /课表风格 图片  切换为图片输出"
            )
    except Exception as e:
        logger.error(f"/课表风格 error: {e}")
        await bot.send(event, f"设置失败: {e}")


# ===== 课前提醒命令 =====

@reminder_cmd.handle()
async def handle_reminder(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """管理课前提醒。"""
    try:
        from .reminder import set_reminder, get_reminder, get_reminder_minutes, set_reminder_minutes
        
        user_id = str(event.user_id)
        arg = args.extract_plain_text().strip().lower()

        if arg in ("开", "开启", "on", "打开"):
            set_reminder(user_id, True)
            minutes = get_reminder_minutes(user_id)
            await bot.send(event, f"已开启课前提醒（提前{minutes}分钟）\n提醒将以私聊方式发送")
        elif arg in ("关", "关闭", "off"):
            set_reminder(user_id, False)
            await bot.send(event, "已关闭课前提醒")
        elif arg.startswith(("提前", "分钟")):
            import re
            m = re.search(r'(\d+)', arg)
            if m:
                minutes = int(m.group(1))
                if minutes < 1 or minutes > 30:
                    await bot.send(event, "提醒时间范围为 1-30 分钟")
                    return
                set_reminder_minutes(user_id, minutes)
                set_reminder(user_id, True)
                await bot.send(event, f"已设置提前{minutes}分钟提醒")
            else:
                await bot.send(event, "请输入分钟数，例如:\n  /课前提醒 提前5分钟\n  /课前提醒 10")
        else:
            enabled = get_reminder(user_id)
            minutes = get_reminder_minutes(user_id)
            status = "已开启" if enabled else "已关闭"
            await bot.send(
                event,
                f"课前提醒: {status}\n"
                f"提前时间: {minutes}分钟\n\n"
                "使用方法:\n"
                "  /课前提醒 开    开启提醒\n"
                "  /课前提醒 关    关闭提醒\n"
                "  /课前提醒 提前5分钟  设置提前时间"
            )
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/课前提醒 error: {e}")
        await bot.send(event, f"操作失败: {e}")


# ===== 假期订阅命令 =====

@holiday_reminder_cmd.handle()
async def handle_holiday_reminder(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """管理假期订阅提醒。"""
    try:
        from .reminder import set_holiday_reminder, get_holiday_reminder
        
        user_id = str(event.user_id)
        arg = args.extract_plain_text().strip().lower()

        if arg in ("开", "开启", "on", "打开"):
            set_holiday_reminder(user_id, True)
            await bot.send(event, "已开启假期订阅\n假期前5天每天早上8点会发送提醒")
        elif arg in ("关", "关闭", "off"):
            set_holiday_reminder(user_id, False)
            await bot.send(event, "已关闭假期订阅")
        else:
            enabled = get_holiday_reminder(user_id)
            status = "已开启" if enabled else "已关闭"
            await bot.send(
                event,
                f"假期订阅: {status}\n\n"
                "使用方法:\n"
                "  /假期订阅 开    开启假期提醒\n"
                "  /假期订阅 关    关闭假期提醒\n\n"
                "开启后，每个假期前5天内每天早上8点会发送提醒"
            )
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/假期订阅 error: {e}")
        await bot.send(event, f"操作失败: {e}")


# ===== 节假日命令 =====

@holiday_cmd.handle()
async def handle_holiday(bot: Bot, event: MessageEvent):
    """查询今天/最近的节假日信息。"""
    try:
        today = date.today()

        if is_holiday(today):
            name = get_holiday_name(today)
            await bot.send(event, f"今天是{name}，放假！")
            return

        reason = get_workday_reason(today)
        if reason:
            await bot.send(event, f"今天是{reason}补班日，要上课！")
            return

        next_h = get_next_holiday(today)
        if next_h:
            await bot.send(
                event,
                f"今天正常上课\n"
                f"下一个假期: {next_h['name']}（{next_h['date'].strftime('%m月%d日')}）\n"
                f"还有 {next_h['days_left']} 天"
            )
        else:
            await bot.send(event, "今天正常上课")
    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/放假没 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 现在什么课命令 =====

@now_cmd.handle()
async def handle_now(bot: Bot, event: MessageEvent):
    """查询当前课程。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        day_index = today.isoweekday()

        if is_holiday(today):
            name = get_holiday_name(today)
            await bot.send(event, f"今天是{name}，放假！")
            return

        if day_index >= 6:
            await bot.send(event, "今天是周末，没有课哦~")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        # 获取作息表
        prefs = manager._prefs_cache.get(user_id, {})
        custom_schedule = prefs.get("custom_schedule", [])
        time_schedule = [(s["period"], s["start"], s["end"]) for s in custom_schedule] if custom_schedule else []

        period_info = get_current_period(schedule=time_schedule)
        current_course = None
        next_course = None

        if period_info and courses:
            current_period = period_info.get("period")
            next_period = period_info.get("next_period")
            for c in courses:
                periods = c.get("periods", [])
                if current_period is not None and current_period in periods:
                    current_course = c
                if next_period is not None and next_period in periods:
                    next_course = c

        text = format_now_output(period_info, current_course, next_course)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/现在什么课 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 等会什么课命令 =====

@next_cmd.handle()
async def handle_next(bot: Bot, event: MessageEvent):
    """查询下一节课。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        day_index = today.isoweekday()

        if is_holiday(today):
            name = get_holiday_name(today)
            await bot.send(event, f"今天是{name}，放假！")
            return

        if day_index >= 6:
            await bot.send(event, "今天是周末，没有课哦~")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        # 获取作息表
        prefs = manager._prefs_cache.get(user_id, {})
        custom_schedule = prefs.get("custom_schedule", [])
        time_schedule = [(s["period"], s["start"], s["end"]) for s in custom_schedule] if custom_schedule else []

        period_info = get_current_period(schedule=time_schedule)
        current_course = None
        next_course = None

        if period_info and courses:
            current_period = period_info.get("period")
            next_period = period_info.get("next_period")
            for c in courses:
                periods = c.get("periods", [])
                if current_period is not None and current_period in periods:
                    current_course = c
                if next_period is not None and next_period in periods:
                    next_course = c

        text = format_next_output(period_info, next_course, current_course)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/等会什么课 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 今天什么课命令 =====

@today_cmd.handle()
async def handle_today(bot: Bot, event: MessageEvent):
    """查询今日课程。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        day_index = today.isoweekday()

        if is_holiday(today):
            name = get_holiday_name(today)
            await bot.send(event, f"今天是{name}，放假！")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        if not courses:
            await bot.send(event, "今天没有课程安排~")
            return

        text = format_day_output(today, day_index, week_info, courses)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/今天什么课 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 明天什么课命令 =====

@tomorrow_cmd.handle()
async def handle_tomorrow(bot: Bot, event: MessageEvent):
    """查询明日课程。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        tomorrow = date.today() + timedelta(days=1)
        day_index = tomorrow.isoweekday()

        if is_holiday(tomorrow):
            name = get_holiday_name(tomorrow)
            await bot.send(event, f"明天是{name}，放假！")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], tomorrow, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        if not courses:
            await bot.send(event, "明天没有课程安排~")
            return

        text = format_day_output(tomorrow, day_index, week_info, courses)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/明天什么课 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 本周课表命令 =====

@week_cmd.handle()
async def handle_week(bot: Bot, event: MessageEvent):
    """查询本周课表概览。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        # 收集每天的课表
        days_data = {}
        for day in range(1, 6):
            days_data[day] = manager.get_courses_for_day(user_id, day, week_info["current"])

        text = format_weekly_overview(week_info, days_data, today)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/本周课表 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 第几周命令 =====

@weeknum_cmd.handle()
async def handle_weeknum(bot: Bot, event: MessageEvent):
    """查询当前是第几周。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        week_type = "单周" if week_info["is_odd"] else "双周"
        await bot.send(
            event,
            f"今天是 {today.strftime('%Y年%m月%d日')}\n"
            f"当前是第 {week_info['current']} 周 ({week_type})\n"
            f"本学期共 {week_info['total']} 周"
        )

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/第几周 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 我的课表命令 =====

@my_schedule_cmd.handle()
async def handle_my_schedule(bot: Bot, event: MessageEvent):
    """查询完整课表。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        text = format_my_schedule(schedule)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/我的课表 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 查课命令 =====

@search_cmd.handle()
async def handle_search(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """搜索课程。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        query = args.extract_plain_text().strip()
        if not query:
            await bot.send(event, "请输入要搜索的课程名，例如：\n  /查课 物理")
            return

        today = date.today()
        day_index = today.isoweekday()

        if is_holiday(today):
            name = get_holiday_name(today)
            await bot.send(event, f"今天是{name}，放假！")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], today, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        if not courses:
            await bot.send(event, "今天没有课程安排~")
            return

        # 搜索匹配的课程
        matches = []
        for c in courses:
            if query.lower() in c.get("name", "").lower():
                matches.append(c)

        if not matches:
            await bot.send(event, f"今天没有找到包含「{query}」的课程")
            return

        # 格式化输出
        lines = [f"今天包含「{query}」的课程：", ""]
        for c in matches:
            periods = c.get("periods", [])
            p = periods[0] if periods else 0
            p_name = ["早读","第1节","第2节","第3节","第4节","第5节","第6节","第7节","第8节","晚自习"][p]
            
            name = c.get("name", "")
            teacher = c.get("teacher", "")
            location = c.get("location", "")
            
            info = name
            if teacher:
                info += f" ({teacher})"
            if location:
                info += f" @{location}"
            
            lines.append(f"  {p_name} {info}")

        await bot.send(event, "\n".join(lines))

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/查课 error: {e}")
        await bot.send(event, f"查询失败: {e}")


# ===== 星期命令 =====

@monday_cmd.handle()
async def handle_monday(bot: Bot, event: MessageEvent):
    """查询周一课程。"""
    await _handle_weekday(bot, event, 1)

@tuesday_cmd.handle()
async def handle_tuesday(bot: Bot, event: MessageEvent):
    """查询周二课程。"""
    await _handle_weekday(bot, event, 2)

@wednesday_cmd.handle()
async def handle_wednesday(bot: Bot, event: MessageEvent):
    """查询周三课程。"""
    await _handle_weekday(bot, event, 3)

@thursday_cmd.handle()
async def handle_thursday(bot: Bot, event: MessageEvent):
    """查询周四课程。"""
    await _handle_weekday(bot, event, 4)

@friday_cmd.handle()
async def handle_friday(bot: Bot, event: MessageEvent):
    """查询周五课程。"""
    await _handle_weekday(bot, event, 5)

@saturday_cmd.handle()
async def handle_saturday(bot: Bot, event: MessageEvent):
    """查询周六课程。"""
    await _handle_weekday(bot, event, 6)

@sunday_cmd.handle()
async def handle_sunday(bot: Bot, event: MessageEvent):
    """查询周日课程。"""
    await _handle_weekday(bot, event, 7)


async def _handle_weekday(bot: Bot, event: MessageEvent, day_index: int):
    """处理星期查询。"""
    try:
        user_id = str(event.user_id)
        schedule, error = _load_schedule(user_id)
        if error:
            await bot.send(event, error)
            return

        today = date.today()
        target_date = today + timedelta(days=(day_index - today.isoweekday()))

        if is_holiday(target_date):
            name = get_holiday_name(target_date)
            await bot.send(event, f"{WEEKDAY_FULL[day_index]}是{name}，放假！")
            return

        week_info = calculate_week_info(
            schedule["semester_start"], target_date, schedule.get("total_weeks", 20)
        )

        courses = manager.get_courses_for_day(user_id, day_index, week_info["current"])

        if not courses:
            await bot.send(event, f"{WEEKDAY_FULL[day_index]}没有课程安排~")
            return

        text = format_day_output(target_date, day_index, week_info, courses)
        await bot.send(event, text)

    except FinishedException:
        raise
    except Exception as e:
        logger.error(f"/{WEEKDAY_NAMES[day_index]} error: {e}")
        await bot.send(event, f"查询失败: {e}")


try:
    if find_spec("nonebot_plugin_apscheduler") is not None:
        require("nonebot_plugin_apscheduler")
        from . import reminder  # noqa: F401
    else:
        reminder = None
        logger.warning("课前提醒定时任务未启用，请安装 nonebot-plugin-apscheduler。")
except Exception as exc:
    reminder = None
    logger.warning(f"课前提醒定时任务未启用，请安装 nonebot-plugin-apscheduler: {exc}")
