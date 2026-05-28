"""nonebot-plugin-class-schedule - 课前提醒模块"""

import asyncio
from datetime import datetime, timedelta
from nonebot import get_bot, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from .manager import ScheduleManager
from .utils import get_current_period, calculate_week_info, format_periods
from . import manager as _manager

# ===== 提醒偏好存储 =====

def get_reminder(user_id: str) -> bool:
    """获取用户提醒开关状态。"""
    prefs = _manager._prefs_cache.get(user_id, {})
    return prefs.get("reminder", False)

def get_reminder_users() -> list:
    """获取所有开启提醒的用户ID列表。"""
    prefs = _manager._prefs_cache
    return [uid for uid, data in prefs.items() if data.get("reminder", False)]

def set_reminder(user_id: str, enabled: bool):
    """设置用户提醒开关。"""
    if user_id not in _manager._prefs_cache:
        _manager._prefs_cache[user_id] = {}
    _manager._prefs_cache[user_id]["reminder"] = enabled
    _manager._save_preferences()

def get_reminder_minutes(user_id: str) -> int:
    """获取用户提醒提前分钟数，默认5。"""
    prefs = _manager._prefs_cache.get(user_id, {})
    return prefs.get("reminder_minutes", 5)

def set_reminder_minutes(user_id: str, minutes: int):
    """设置用户提醒提前分钟数。"""
    if user_id not in _manager._prefs_cache:
        _manager._prefs_cache[user_id] = {}
    _manager._prefs_cache[user_id]["reminder_minutes"] = minutes
    _manager._save_preferences()

# ===== 假期订阅功能 =====

def get_holiday_reminder(user_id: str) -> bool:
    """获取用户假期提醒开关状态。"""
    prefs = _manager._prefs_cache.get(user_id, {})
    return prefs.get("holiday_reminder", False)

def set_holiday_reminder(user_id: str, enabled: bool):
    """设置用户假期提醒开关。"""
    if user_id not in _manager._prefs_cache:
        _manager._prefs_cache[user_id] = {}
    _manager._prefs_cache[user_id]["holiday_reminder"] = enabled
    _manager._save_preferences()

# 记录已发送的假期提醒，避免重复 {user_id: {holiday_date_str: True}}
_holiday_reminded: dict = {}

async def check_and_remind_holiday():
    """检查假期，提前5天每天提醒订阅用户。"""
    users = [
        uid for uid, data in _manager._prefs_cache.items()
        if data.get("holiday_reminder", False)
    ]
    if not users:
        return

    from .holidays import ALL_HOLIDAYS, is_holiday
    from datetime import date, timedelta

    today = date.today()

    # 如果是普通周末（不是法定节假日），不发送提醒
    if today.weekday() >= 5 and not is_holiday(today):
        return

    try:
        bot = get_bot()
    except ValueError:
        return

    for user_id in users:
        try:
            if user_id not in _holiday_reminded:
                _holiday_reminded[user_id] = {}

            # 遍历所有节假日，找5天内即将到来的
            for holiday_date, name in ALL_HOLIDAYS.items():
                days_left = (holiday_date - today).days

                # 提前5天内，且今天还没提醒过
                if 0 <= days_left <= 5:
                    date_str = holiday_date.strftime("%Y-%m-%d")
                    reminder_key = f"{date_str}_{name}"

                    if reminder_key in _holiday_reminded[user_id]:
                        continue

                    # 发送提醒
                    if days_left == 0:
                        msg = f"假期提醒\n今天是{name}！\n好好享受假期吧~"
                    else:
                        msg = f"假期提醒\n距离{name}还有{days_left}天\n{holiday_date.strftime('%m月%d日')}开始放假"

                    try:
                        await bot.send_private_msg(
                            user_id=int(user_id),
                            message=Message(msg)
                        )
                        _holiday_reminded[user_id][reminder_key] = True
                    except Exception as e:
                        logger.warning(f"发送假期提醒失败 uid={user_id}: {e}")

        except Exception as e:
            logger.error(f"假期提醒检查失败 uid={user_id}: {e}")

# 每天早上8点检查假期提醒
scheduler.add_job(
    check_and_remind_holiday,
    "cron",
    hour=8,
    minute=0,
    id="class_schedule_holiday_reminder",
    replace_existing=True,
)

# ===== 课前提醒任务 =====

# 记录已提醒的节次，避免重复
_reminded: dict = {}  # {user_id: {date_str: set(periods)}}

def _clear_reminded_cache():
    """每天0点清空提醒缓存。"""
    _reminded.clear()

# 注册每天0点清理
scheduler.add_job(
    _clear_reminded_cache,
    "cron",
    hour=0,
    minute=0,
    id="class_schedule_clear_cache",
    replace_existing=True,
)

async def check_and_remind():
    """检查所有开启提醒的用户，发送课前提醒。"""
    users = get_reminder_users()
    if not users:
        return

    now = datetime.now()
    today = now.date()
    date_str = today.strftime("%Y-%m-%d")
    day_index = today.isoweekday()

    if day_index >= 6:
        return  # 周末不提醒

    # 检查是否是节假日
    from .holidays import is_holiday
    if is_holiday(today):
        return

    try:
        bot = get_bot()
    except ValueError:
        return  # 没有bot实例

    for user_id in users:
        try:
            schedule = _manager.get_schedule(user_id)
            if not schedule:
                continue

            week_info = calculate_week_info(
                schedule["semester_start"], today, schedule.get("total_weeks", 20)
            )

            courses = _manager.get_courses_for_day(user_id, day_index, week_info["current"])
            if not courses:
                continue

            # 初始化当日提醒记录
            if user_id not in _reminded:
                _reminded[user_id] = {}
            if date_str not in _reminded[user_id]:
                _reminded[user_id][date_str] = set()

            reminded_periods = _reminded[user_id][date_str]
            reminder_minutes = get_reminder_minutes(user_id)

            # 遍历每门课，检查是否需要提醒
            for course in courses:
                periods = course.get("periods", [])
                for p in periods:
                    if p in reminded_periods:
                        continue

                    # 获取该节次开始时间
                    from .utils import DEFAULT_SCHEDULE
                    start_time = None
                    for period, start, end in DEFAULT_SCHEDULE:
                        if period == p:
                            start_time = start
                            break

                    if not start_time:
                        continue

                    # 计算提醒时间
                    start_dt = datetime.strptime(start_time, "%H:%M")
                    remind_dt = start_dt - timedelta(minutes=reminder_minutes)

                    # 当前时间在提醒窗口内（前后1分钟）
                    current_minutes = now.hour * 60 + now.minute
                    target_minutes = remind_dt.hour * 60 + remind_dt.minute

                    if abs(current_minutes - target_minutes) <= 1:
                        # 发送提醒
                        name = course.get("name", "未知")
                        teacher = course.get("teacher", "")
                        location = course.get("location", "")

                        if p == 0:
                            period_label = "早读"
                        elif p == 9:
                            period_label = "晚自习"
                        else:
                            period_label = f"第{p}节"

                        msg = f"上课提醒\n{period_label} 还有{reminder_minutes}分钟开始\n课程: {name}"
                        if teacher:
                            msg += f"\n老师: {teacher}"
                        if location:
                            msg += f"\n地点: {location}"

                        try:
                            await bot.send_private_msg(
                                user_id=int(user_id),
                                message=Message(msg)
                            )
                        except Exception as e:
                            logger.warning(f"发送提醒失败 uid={user_id}: {e}")

                        reminded_periods.add(p)

        except Exception as e:
            logger.error(f"提醒检查失败 uid={user_id}: {e}")

# 每分钟检查一次
scheduler.add_job(
    check_and_remind,
    "interval",
    minutes=1,
    id="class_schedule_reminder",
    replace_existing=True,
)
