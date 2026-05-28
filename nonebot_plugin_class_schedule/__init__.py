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
