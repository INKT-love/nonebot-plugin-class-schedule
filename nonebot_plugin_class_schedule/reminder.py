"""提醒功能模块"""

from datetime import datetime, timedelta
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot

try:
    from nonebot_plugin_apscheduler import scheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    scheduler = None

from .manager import ScheduleManager
from .utils import get_current_period, parse_time_string
from .holidays import is_holiday

# 初始化管理器
manager = ScheduleManager()

# 已注册的提醒任务
_reminder_jobs = {}


def init_reminder_scheduler():
    """初始化提醒调度器"""
    if not HAS_SCHEDULER:
        logger.warning("未安装 nonebot_plugin_apscheduler，提醒功能不可用")
        return
    
    # 每分钟检查一次
    scheduler.add_job(
        check_reminders,
        "cron",
        minute="*",
        id="class_schedule_reminder",
        replace_existing=True,
    )
    logger.info("课程表提醒调度器已启动")


async def check_reminders():
    """检查并发送提醒"""
    if not HAS_SCHEDULER:
        return
    
    now = datetime.now()
    
    # 检查是否是节假日
    if is_holiday(now.date()):
        return
    
    # 获取所有用户
    for user_id, prefs in manager._prefs_cache.items():
        reminder_settings = prefs.get("reminder", {})
        if not reminder_settings.get("enabled", False):
            continue
        
        minutes_before = reminder_settings.get("minutes_before", 5)
        
        # 获取用户作息表
        custom_schedule = prefs.get("custom_schedule")
        if not custom_schedule:
            continue
        
        # 检查是否有即将开始的课程
        await check_user_reminder(user_id, custom_schedule, minutes_before, now)


async def check_user_reminder(user_id: str, schedule: dict, minutes_before: int, now: datetime):
    """检查单个用户的提醒
    
    Args:
        user_id: 用户ID
        schedule: 作息表
        minutes_before: 提前提醒分钟数
        now: 当前时间
    """
    current_time = now.strftime("%H:%M")
    
    # 遍历所有时间段
    for period_name, times in schedule.items():
        start_time = times.get("start", "")
        if not start_time:
            continue
        
        # 计算提醒时间
        start_dt = datetime.strptime(start_time, "%H:%M")
        reminder_dt = start_dt - timedelta(minutes=minutes_before)
        reminder_time = reminder_dt.strftime("%H:%M")
        
        # 检查是否到达提醒时间 (当前时间 == 提醒时间)
        if current_time == reminder_time:
            # 检查该时间段是否有课
            await send_reminder(user_id, period_name, start_time)


async def send_reminder(user_id: str, period_name: str, start_time: str):
    """发送提醒消息
    
    Args:
        user_id: 用户ID
        period_name: 节次名称
        start_time: 开始时间
    """
    try:
        # 获取课程信息
        from nonebot import get_bot
        bot = get_bot()
        
        # 获取今天的课程
        weekday = datetime.now().weekday()
        schedule = manager.get_schedule(user_id)
        
        if not schedule:
            return
        
        courses = schedule.get("courses", [])
        current_course = None
        
        for course in courses:
            if course.get("day") == weekday and course.get("period_name") == period_name:
                current_course = course
                break
        
        if not current_course:
            return
        
        # 构建提醒消息
        course_name = current_course.get("name", "未知课程")
        teacher = current_course.get("teacher", "")
        location = current_course.get("location", "")
        
        message_parts = [
            "⏰ 课前提醒",
            f"",
            f"即将开始: {period_name}",
            f"课程: {course_name}",
        ]
        
        if teacher:
            message_parts.append(f"老师: {teacher}")
        if location:
            message_parts.append(f"地点: {location}")
        
        message_parts.append(f"开始时间: {start_time}")
        
        message = "\n".join(message_parts)
        
        # 发送私聊消息
        await bot.send_private_msg(user_id=int(user_id), message=message)
        logger.info(f"已发送课前提醒给用户 {user_id}: {course_name}")
        
    except Exception as e:
        logger.error(f"发送提醒失败 {user_id}: {e}")


def register_user_reminder(user_id: str, enabled: bool = True, minutes_before: int = 5):
    """注册用户提醒
    
    Args:
        user_id: 用户ID
        enabled: 是否启用
        minutes_before: 提前提醒分钟数
    """
    manager.set_reminder_settings(user_id, enabled=enabled, minutes_before=minutes_before)
    logger.info(f"用户 {user_id} 提醒设置已更新: enabled={enabled}, minutes_before={minutes_before}")


def unregister_user_reminder(user_id: str):
    """注销用户提醒
    
    Args:
        user_id: 用户ID
    """
    manager.set_reminder_settings(user_id, enabled=False)
    logger.info(f"用户 {user_id} 提醒已禁用")


# 假期提醒相关
async def check_holiday_reminders():
    """检查假期提醒"""
    if not HAS_SCHEDULER:
        return
    
    from .holidays import get_next_holiday
    
    now = datetime.now()
    
    # 获取所有用户
    for user_id, prefs in manager._prefs_cache.items():
        if not prefs.get("holiday_reminder", False):
            continue
        
        # 获取下一个假期
        next_holiday = get_next_holiday(now.date())
        if not next_holiday:
            continue
        
        holiday_date, name, days_left = next_holiday
        
        # 提前5天每天提醒
        if 1 <= days_left <= 5:
            # 只在早上8点提醒
            if now.strftime("%H:%M") == "08:00":
                await send_holiday_reminder(user_id, name, days_left)


async def send_holiday_reminder(user_id: str, holiday_name: str, days_left: int):
    """发送假期提醒
    
    Args:
        user_id: 用户ID
        holiday_name: 假期名称
        days_left: 距离天数
    """
    try:
        from nonebot import get_bot
        bot = get_bot()
        
        message = f"🎉 假期提醒\n\n距离{holiday_name}还有 {days_left} 天！"
        
        await bot.send_private_msg(user_id=int(user_id), message=message)
        logger.info(f"已发送假期提醒给用户 {user_id}: {holiday_name}")
        
    except Exception as e:
        logger.error(f"发送假期提醒失败 {user_id}: {e}")


# 初始化
if HAS_SCHEDULER:
    init_reminder_scheduler()
