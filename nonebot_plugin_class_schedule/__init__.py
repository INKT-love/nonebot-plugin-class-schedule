"""nonebot-plugin-class-schedule - 课程表插件

一个功能完善的 NoneBot2 课程表插件
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.exception import FinishedException
from nonebot.plugin import PluginMetadata
from datetime import date, timedelta
from typing import Tuple, List, Dict, Optional

try:
    from nonebot_plugin_htmlrender import html_to_pic
    HAS_HTMLRENDER = True
except ImportError:
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
    supported_adapters={"~onebot.v11"},
)

# 初始化管理器
manager = ScheduleManager()

# ===== 命令注册 =====

help_cmd = on_command("课程表帮助", aliases={"class help"}, priority=5)
style_cmd = on_command("课表风格", priority=5)
reminder_cmd = on_command("课前提醒", priority=5)
holiday_reminder_cmd = on_command("假期订阅", priority=5)
holiday_cmd = on_command("放假没", aliases={"节假日", "今天放假吗"}, priority=5)
import_cmd = on_command("导入课表", aliases={"导入", "设置课表"}, priority=5)
cancel_import_cmd = on_command("取消导入", priority=5)
confirm_import_cmd = on_command("确认导入", priority=5)
import_schedule_cmd = on_command("导入作息表", aliases={"作息表导入", "导入作息"}, priority=5)
cancel_schedule_cmd = on_command("取消导入作息", priority=5)
confirm_schedule_cmd = on_command("确认导入作息", priority=5)
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
  /确认导入        确认导入课表
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


def _get_day_courses(user_id: str, day_index: int, week: int) -> list:
    """获取某天的课程列表。"""
    return manager.get_courses_for_day(user_id, day_index, week)


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


# ===== 其他命令处理函数 =====
# 这里省略其他命令的处理函数，与原始代码相同
# 包括: handle_help, handle_style, handle_reminder, handle_holiday_reminder,
#       handle_holiday, handle_now, handle_next, handle_search, handle_today,
#       handle_tomorrow, handle_week, handle_weeknum, handle_my_schedule,
#       以及各星期命令的处理函数

# 导入提醒模块
from . import reminder
