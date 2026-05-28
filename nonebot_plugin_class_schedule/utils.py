"""工具函数模块"""

from datetime import date, datetime, timedelta
from typing import Tuple, List, Dict, Optional

# 星期名称映射
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_FULL = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# 默认作息时间表 (示例数据)
DEFAULT_SCHEDULE = {
    "早读": {"start": "07:00", "end": "07:30"},
    "第1节": {"start": "08:00", "end": "08:45"},
    "第2节": {"start": "08:55", "end": "09:40"},
    "第3节": {"start": "09:50", "end": "10:35"},
    "第4节": {"start": "10:45", "end": "11:30"},
    "午休": {"start": "12:00", "end": "14:00"},
    "第5节": {"start": "14:00", "end": "14:45"},
    "第6节": {"start": "14:55", "end": "15:40"},
    "第7节": {"start": "15:50", "end": "16:35"},
    "第8节": {"start": "16:45", "end": "17:30"},
    "晚自习": {"start": "18:30", "end": "21:00"},
}


def calculate_week_info(semester_start: str, current_date: date = None) -> Tuple[int, str]:
    """计算当前周次和单双周
    
    Args:
        semester_start: 学期开始日期 (YYYY-MM-DD)
        current_date: 当前日期，默认为今天
    
    Returns:
        (周次, 单双周) 元组
    """
    if current_date is None:
        current_date = date.today()
    
    start = datetime.strptime(semester_start, "%Y-%m-%d").date()
    days_diff = (current_date - start).days
    
    if days_diff < 0:
        return 0, "开学前"
    
    week = days_diff // 7 + 1
    parity = "单周" if week % 2 == 1 else "双周"
    
    return week, parity


def parse_day_input(day_str: str) -> int:
    """解析星期输入，返回 0-6 (周一到周日)
    
    Args:
        day_str: 星期字符串，如 "周一", "星期一", "1"
    
    Returns:
        星期索引 0-6
    """
    day_map = {
        "周一": 0, "星期一": 0, "1": 0, "一": 0,
        "周二": 1, "星期二": 1, "2": 1, "二": 1,
        "周三": 2, "星期三": 2, "3": 2, "三": 2,
        "周四": 3, "星期四": 3, "4": 3, "四": 3,
        "周五": 4, "星期五": 4, "5": 4, "五": 4,
        "周六": 5, "星期六": 5, "6": 5, "六": 5,
        "周日": 6, "星期日": 6, "星期天": 6, "7": 6, "日": 6,
    }
    return day_map.get(day_str.strip(), -1)


def day_to_chinese(day_index: int) -> str:
    """将星期索引转换为中文"""
    if 0 <= day_index <= 6:
        return WEEKDAY_NAMES[day_index]
    return "未知"


def format_periods(schedule: Dict[str, dict]) -> str:
    """格式化作息时间表为字符串"""
    lines = ["当前作息时间表："]
    for name, times in schedule.items():
        lines.append(f"  {name}: {times['start']} - {times['end']}")
    return "\n".join(lines)


def get_current_period(schedule: Dict[str, dict], current_time: datetime = None) -> Tuple[str, str, Optional[dict]]:
    """获取当前时间段状态
    
    Returns:
        (状态, 当前节次名称, 下一节信息)
    """
    if current_time is None:
        current_time = datetime.now()
    
    current_time_str = current_time.strftime("%H:%M")
    
    periods = []
    for name, times in schedule.items():
        periods.append((name, times["start"], times["end"]))
    
    # 按开始时间排序
    periods.sort(key=lambda x: x[1])
    
    # 检查是否在上课
    for i, (name, start, end) in enumerate(periods):
        if start <= current_time_str <= end:
            # 正在上课
            next_period = periods[i + 1] if i + 1 < len(periods) else None
            return ("上课中", name, next_period)
    
    # 检查是否在课间
    for i, (name, start, end) in enumerate(periods):
        if current_time_str < start:
            if i == 0:
                return ("课前", "未到上课时间", periods[0])
            prev_end = periods[i - 1][2]
            if current_time_str < start:
                return ("课间", f"{periods[i-1][0]}后", periods[i])
    
    # 放学后
    return ("放学后", "今日课程已结束", None)


def format_now_output(day_name: str, status: str, period_name: str, course: dict = None) -> str:
    """格式化当前课程输出"""
    lines = [f"【{day_name} - 当前状态】"]
    lines.append("")
    
    if status == "上课中":
        if course:
            lines.append(f"正在上课: {course.get('name', '未知课程')}")
            if course.get('teacher'):
                lines.append(f"任课老师: {course['teacher']}")
            if course.get('location'):
                lines.append(f"上课地点: {course['location']}")
        else:
            lines.append(f"正在上: {period_name}")
            lines.append("(该时段暂无课程安排)")
    elif status == "课间":
        lines.append(f"当前: {period_name}")
        if course:
            lines.append(f"下一节: {course.get('name', '未知')}")
        else:
            lines.append("下一节暂无课程安排")
    elif status == "放学后":
        lines.append("今日课程已结束")
    else:
        lines.append(f"当前状态: {status}")
    
    return "\n".join(lines)


def format_next_output(day_name: str, next_period: tuple, course: dict = None, minutes_left: int = 0) -> str:
    """格式化下一节课输出"""
    lines = [f"【{day_name} - 下一节课】"]
    lines.append("")
    
    if next_period:
        period_name, start_time, end_time = next_period
        lines.append(f"时间: {period_name} ({start_time} - {end_time})")
        
        if course:
            lines.append(f"课程: {course.get('name', '未知课程')}")
            if course.get('teacher'):
                lines.append(f"老师: {course['teacher']}")
            if course.get('location'):
                lines.append(f"地点: {course['location']}")
        else:
            lines.append("课程: 暂无安排")
        
        if minutes_left > 0:
            lines.append("")
            lines.append(f"距离上课还有 {minutes_left} 分钟")
    else:
        lines.append("今天没有更多课程了")
    
    return "\n".join(lines)


def format_day_output(day_name: str, courses: List[dict], schedule: Dict[str, dict]) -> str:
    """格式化某天课程输出"""
    lines = [f"【{day_name}课程表】"]
    lines.append("")
    
    if not courses:
        lines.append("今天没有课程安排")
        return "\n".join(lines)
    
    for course in courses:
        period = course.get("period_name", f"第{course.get('period', '?')}节")
        name = course.get("name", "未知课程")
        teacher = course.get("teacher", "")
        location = course.get("location", "")
        
        info_parts = [name]
        if teacher:
            info_parts.append(f"({teacher})")
        if location:
            info_parts.append(f"@{location}")
        
        lines.append(f"{period}: {' '.join(info_parts)}")
    
    return "\n".join(lines)


def format_weekly_overview(week_courses: Dict[int, List[dict]], week: int, parity: str) -> str:
    """格式化本周概览"""
    lines = [f"【第{week}周课程概览 - {parity}】"]
    lines.append("")
    
    for day_idx in range(5):  # 周一到周五
        day_name = WEEKDAY_NAMES[day_idx]
        courses = week_courses.get(day_idx, [])
        
        if courses:
            course_names = [c.get("name", "未知") for c in courses]
            lines.append(f"{day_name}: {' | '.join(course_names)}")
        else:
            lines.append(f"{day_name}: 无课")
    
    return "\n".join(lines)


def format_my_schedule(schedule: dict) -> str:
    """格式化完整课表输出"""
    lines = ["【我的完整课表】"]
    lines.append("")
    
    semester_start = schedule.get("semester_start", "未设置")
    total_weeks = schedule.get("total_weeks", 20)
    courses = schedule.get("courses", [])
    
    lines.append(f"学期开始: {semester_start}")
    lines.append(f"总周数: {total_weeks}")
    lines.append(f"课程数量: {len(courses)}")
    lines.append("")
    
    # 按星期分组
    by_day = {i: [] for i in range(7)}
    for course in courses:
        day = course.get("day", 0)
        by_day[day].append(course)
    
    for day_idx in range(7):
        day_courses = by_day[day_idx]
        if day_courses:
            lines.append(f"\n{WEEKDAY_NAMES[day_idx]}:")
            day_courses.sort(key=lambda x: x.get("period", 0))
            for c in day_courses:
                period = c.get("period_name", f"第{c.get('period', '?')}节")
                name = c.get("name", "未知")
                teacher = c.get("teacher", "")
                loc = c.get("location", "")
                info = f"  {period}: {name}"
                if teacher:
                    info += f" ({teacher})"
                if loc:
                    info += f" @{loc}"
                lines.append(info)
    
    return "\n".join(lines)


def parse_time_string(time_str: str) -> Optional[tuple]:
    """解析时间字符串，返回 (小时, 分钟)"""
    try:
        parts = time_str.strip().split(":")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
    except:
        pass
    return None
