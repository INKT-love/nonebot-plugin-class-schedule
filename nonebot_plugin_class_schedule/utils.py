"""nonebot-plugin-class-schedule - 工具函数"""

import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ===== 作息时间表 =====
# 格式: (节次, 开始时间, 结束时间)
DEFAULT_SCHEDULE = [
    (0, "07:00", "07:30"),   # 早读
    (1, "08:00", "08:45"),   # 第一节
    (2, "08:55", "09:40"),   # 第二节
    (3, "10:00", "10:45"),   # 第三节
    (4, "10:55", "11:40"),   # 第四节
    (5, "14:00", "14:45"),   # 第五节
    (6, "14:55", "15:40"),   # 第六节
    (7, "15:55", "16:40"),   # 第七节
    (8, "16:50", "17:35"),   # 第八节
    (9, "18:20", "21:00"),   # 晚自习
]


def get_current_period(now: datetime = None, schedule: List[Tuple[int, str, str]] = None) -> Dict:
    """
    根据当前时间判断第几节。
    
    返回:
        {
            "status": "class" | "break" | "after_school" | "before_school" | "weekend",
            "period": int,           # 当前节次 (status=class时)
            "next_period": int,      # 下一节次
            "current_course": dict,  # 当前课程 (status=class时)
            "next_course": dict,     # 下一节课程
            "time_to_next": str,     # 距离下一节还有多久
            "time_left": str,        # 当前课程还剩多久 (status=class时)
        }
    """
    if now is None:
        now = datetime.now()
    if schedule is None:
        schedule = DEFAULT_SCHEDULE
    
    # 周末
    if now.weekday() >= 5:  # 周六=5, 周日=6
        return {"status": "weekend", "period": None, "next_period": None}
    
    current_time = now.strftime("%H:%M")
    
    # 找到当前在哪一节
    current_period = None
    next_period = None
    
    for i, (period, start, end) in enumerate(schedule):
        if start <= current_time <= end:
            current_period = period
            next_period = schedule[i + 1][0] if i + 1 < len(schedule) else None
            break
        elif current_time < start:
            next_period = period
            break
    
    # 放学了
    if current_period is None and next_period is None:
        return {"status": "after_school", "period": None, "next_period": None}
    
    # 区分"课前"和"课间"：只有当前时间早于第一节课才是课前
    if current_period is None and next_period is not None:
        first_start = schedule[0][1]
        if current_time < first_start:
            # 还没上课 — 真正课前
            first_start_dt = datetime.strptime(first_start, "%H:%M")
            current_dt = datetime.strptime(current_time, "%H:%M")
            diff = first_start_dt - current_dt
            hours, remainder = divmod(int(diff.total_seconds()), 3600)
            minutes = remainder // 60
            time_str = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
            return {
                "status": "before_school",
                "period": None,
                "next_period": next_period,
                "time_to_next": time_str,
            }
        else:
            # 课间 — 找下一节的开始时间
            for period, start, end in schedule:
                if period == next_period:
                    next_start_dt = datetime.strptime(start, "%H:%M")
                    current_dt = datetime.strptime(current_time, "%H:%M")
                    diff = next_start_dt - current_dt
                    hours, remainder = divmod(int(diff.total_seconds()), 3600)
                    minutes = remainder // 60
                    time_to_next = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
                    return {
                        "status": "break",
                        "period": None,
                        "next_period": next_period,
                        "time_to_next": time_to_next,
                    }

    # 正在上课
    if current_period is not None:
        # 找到当前节的结束时间
        for period, start, end in schedule:
            if period == current_period:
                end_dt = datetime.strptime(end, "%H:%M")
                current_dt = datetime.strptime(current_time, "%H:%M")
                diff = end_dt - current_dt
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes = remainder // 60
                time_left = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
                
                # 计算距离下一节还有多久
                if next_period:
                    for p, s, e in schedule:
                        if p == next_period:
                            next_start_dt = datetime.strptime(s, "%H:%M")
                            diff_to_next = next_start_dt - current_dt
                            h, r = divmod(int(diff_to_next.total_seconds()), 3600)
                            m = r // 60
                            time_to_next = f"{h}小时{m}分钟" if h > 0 else f"{m}分钟"
                            break
                    else:
                        time_to_next = None
                else:
                    time_to_next = None
                
                return {
                    "status": "class",
                    "period": current_period,
                    "next_period": next_period,
                    "time_left": time_left,
                    "time_to_next": time_to_next,
                }
    
    return {"status": "unknown", "period": None, "next_period": None}


def format_now_output(period_info: dict, current_course: dict = None, next_course: dict = None) -> str:
    """格式化 /现在什么课 的输出。"""
    status = period_info.get("status")
    
    if status == "weekend":
        return "🎉 今天是周末，没有课哦~"
    
    if status == "after_school":
        return "📚 今日课程已结束，可以休息啦~"
    
    if status == "before_school":
        next_p = period_info.get("next_period")
        time_to = period_info.get("time_to_next", "未知")
        if next_course:
            name = next_course.get("name", "未知")
            location = next_course.get("location", "")
            loc_str = f" @ {location}" if location else ""
            return f"⏰ 还没上课，第一节是{name}{loc_str}\n   还有 {time_to} 开始"
        return f"⏰ 还没上课，还有 {time_to} 开始第一节课"
    
    if status == "class":
        period = period_info.get("period")
        time_left = period_info.get("time_left", "未知")
        
        # 节次标签: 0→早读, 9→晚自习
        if period == 0:
            period_label = "早读"
        elif period == 9:
            period_label = "晚自习"
        else:
            period_label = f"第{period}节"
        
        lines = [f"📖 正在上{period_label}"]
        
        if current_course:
            name = current_course.get("name", "未知")
            location = current_course.get("location", "")
            teacher = current_course.get("teacher", "")
            loc_str = f" @ {location}" if location else ""
            teacher_str = f" ({teacher})" if teacher else ""
            lines.append(f"   {name}{loc_str}{teacher_str}")
        else:
            lines.append("   当前时间段没有课程安排")
        
        lines.append(f"   还剩 {time_left}")
        
        if next_course:
            next_name = next_course.get("name", "未知")
            next_loc = next_course.get("location", "")
            next_loc_str = f" @ {next_loc}" if next_loc else ""
            lines.append(f"\n📋 下节: {next_name}{next_loc_str}")
        
        return "\n".join(lines)
    
    if status == "break":
        next_p = period_info.get("next_period")
        time_to = period_info.get("time_to_next", "未知")
        
        # 节次标签
        if next_p == 0:
            next_label = "早读"
        elif next_p == 9:
            next_label = "晚自习"
        else:
            next_label = f"第{next_p}节"
        
        lines = [f"☕ 课间休息 ({next_label}即将开始)"]
        lines.append(f"   还有 {time_to} 上课")
        
        if next_course:
            name = next_course.get("name", "未知")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            loc_str = f" @ {location}" if location else ""
            teacher_str = f" ({teacher})" if teacher else ""
            lines.append(f"\n📋 下节: {name}{loc_str}{teacher_str}")
        
        return "\n".join(lines)
    
    return "无法确定当前状态"


def format_next_output(period_info: dict, next_course: dict = None, current_course: dict = None) -> str:
    """格式化 /等会什么课 的输出。"""
    status = period_info.get("status")
    
    if status == "weekend":
        return "🎉 今天是周末，没有课哦~"
    
    if status == "after_school":
        return "📚 今日课程已结束，明天见~"
    
    next_p = period_info.get("next_period")
    
    if status == "class":
        # 正在上课，显示下节信息
        time_to = period_info.get("time_to_next", "未知")
        
        lines = []
        
        if current_course:
            curr_name = current_course.get("name", "未知")
            lines.append(f"📖 正在上: {curr_name}")
        
        if next_course:
            name = next_course.get("name", "未知")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            loc_str = f" @ {location}" if location else ""
            teacher_str = f" ({teacher})" if teacher else ""
            # 节次标签
            if next_p == 0:
                next_label = "早读"
            elif next_p == 9:
                next_label = "晚自习"
            else:
                next_label = f"第{next_p}节"
            lines.append(f"📋 下节: {next_label} {name}{loc_str}{teacher_str}")
            lines.append(f"   还有 {time_to}")
        else:
            lines.append("📋 下节没有课程安排")
        
        return "\n".join(lines)
    
    if status in ("break", "before_school"):
        # 课间或课前，显示下一节
        time_to = period_info.get("time_to_next", "未知")
        
        # 节次标签
        if next_p == 0:
            next_label = "早读"
        elif next_p == 9:
            next_label = "晚自习"
        else:
            next_label = f"第{next_p}节"
        
        lines = [f"⏰ {next_label}即将开始"]
        lines.append(f"   还有 {time_to}")
        
        if next_course:
            name = next_course.get("name", "未知")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            loc_str = f" @ {location}" if location else ""
            teacher_str = f" ({teacher})" if teacher else ""
            lines.append(f"\n📋 课程: {name}{loc_str}{teacher_str}")
        else:
            lines.append("\n📋 该时间段没有课程安排")
        
        return "\n".join(lines)
    
    return "无法确定下一节课程"

# 星期映射
WEEKDAY_NAMES = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_FULL = ["", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def calculate_week_info(
    semester_start_str: str, today: date, total_weeks: int
) -> Dict:
    """
    计算当前周数信息。

    返回:
        {
            "current": int,    # 当前第几周 (1-based)
            "total": int,      # 总周数
            "is_odd": bool,    # 是否单周
            "is_before": bool, # 是否在学期开始前
            "is_after": bool,  # 是否在学期结束后
        }
    """
    try:
        semester_start = date.fromisoformat(semester_start_str)
    except (ValueError, TypeError):
        # 无效日期，返回默认值
        return {
            "current": 1, "total": total_weeks,
            "is_odd": True, "is_before": False, "is_after": False,
        }

    if today < semester_start:
        return {
            "current": 1, "total": total_weeks,
            "is_odd": True, "is_before": True, "is_after": False,
        }

    delta = (today - semester_start).days
    week = delta // 7 + 1

    if week > total_weeks:
        return {
            "current": total_weeks, "total": total_weeks,
            "is_odd": total_weeks % 2 == 1, "is_before": False, "is_after": True,
        }

    return {
        "current": week, "total": total_weeks,
        "is_odd": week % 2 == 1, "is_before": False, "is_after": False,
    }


def parse_day_input(text: str) -> Optional[int]:
    """
    解析用户输入的星期。

    支持格式:
      "周一", "星期二", "星期3", "周4", "1", "今天", "明天"

    返回 day_index (1=周一 ~ 7=周日) 或 None（解析失败）。
    "今天"/"明天" 返回特殊标记，由调用方处理。
    """
    text = text.strip()

    if not text:
        return None

    # 今天 / 明天
    if text in ("今天", "今日"):
        return 0  # 0 = 今天
    if text in ("明天", "明日"):
        return -1  # -1 = 明天

    # "周一" ~ "周日"
    match = re.match(r"周([一二三四五六日])$", text)
    if match:
        mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
        return mapping.get(match.group(1))

    # "星期一" ~ "星期日" / "星期1" ~ "星期7"
    match = re.match(r"星期([一二三四五六日1-7])$", text)
    if match:
        group = match.group(1)
        mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
        if group in mapping:
            return mapping[group]
        return int(group)

    # "周1" ~ "周7"
    match = re.match(r"周([1-7])$", text)
    if match:
        return int(match.group(1))

    # 纯数字 1-7
    if text.isdigit():
        n = int(text)
        if 1 <= n <= 7:
            return n

    return None


def day_to_chinese(day: int) -> str:
    """将 day_index (1-7) 转为中文，如 1→'周一'"""
    if 1 <= day <= 7:
        return WEEKDAY_NAMES[day]
    return f"第{day}天"


def format_periods(periods: List[int]) -> str:
    """
    将节次列表格式化为可读字符串。

    0→早读, 9→晚自习, 1-8→第1-8节
    例: [1, 2] → "第1-2节"
        [0] → "早读"
        [9] → "晚自习"
    """
    if not periods:
        return ""

    # 映射节次标签
    def _label(p):
        if p == 0:
            return "早读"
        if p == 9:
            return "晚自习"
        return f"第{p}节"

    sorted_p = sorted(periods)
    # 如果只有一个节次，直接返回标签
    if len(sorted_p) == 1:
        return _label(sorted_p[0])

    # 多个节次，按范围合并
    ranges = []
    start = sorted_p[0]
    end = sorted_p[0]

    for p in sorted_p[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append((start, end))
            start = p
            end = p
    ranges.append((start, end))

    # 如果所有节次连续且同类型（都是普通节次1-8），用范围表示
    if len(ranges) == 1 and 1 <= sorted_p[0] <= 8 and 1 <= sorted_p[-1] <= 8:
        s, e = ranges[0]
        if s == e:
            return f"第{s}节"
        return f"第{s}-{e}节"

    # 否则逐个用标签表示
    parts = [_label(p) for p in sorted_p]
    return "、".join(parts)


def format_single_course(course: dict) -> str:
    """格式化单门课程为一行文本。"""
    name = course.get("name", "未命名")
    location = course.get("location", "")
    teacher = course.get("teacher", "")

    line = f"  {name}"
    extras = []
    if location:
        extras.append(location)
    if teacher:
        extras.append(teacher)
    if extras:
        line += "  |  " + " / ".join(extras)

    return line


def format_day_output(
    target_date: date,
    day_index: int,
    week_info: dict,
    courses: list,
    title: str = None,
) -> str:
    """格式化某一天的课程输出。"""
    current_week = week_info["current"]
    total_weeks = week_info["total"]
    is_odd = week_info["is_odd"]

    if title is None:
        day_name = WEEKDAY_NAMES[day_index] if 1 <= day_index <= 7 else "当天"
        title = f"{day_name}课表"

    date_str = target_date.strftime("%Y-%m-%d")
    week_type = "单周" if is_odd else "双周"

    lines = [
        f"=== {title} ===",
        f"日期: {date_str}  |  第{current_week}周 ({week_type})  |  共{total_weeks}周",
    ]

    if week_info.get("is_before"):
        lines.append("\n【提示】学期尚未开始")
        return "\n".join(lines)
    if week_info.get("is_after"):
        lines.append("\n【提示】学期已结束")
        return "\n".join(lines)

    if not courses:
        lines.append("\n今天没有课~")
        return "\n".join(lines)

    # 按节次排序
    courses_sorted = sorted(courses, key=lambda c: min(c.get("periods", [99])))

    lines.append("")
    for c in courses_sorted:
        periods_str = format_periods(c.get("periods", []))
        course_line = format_single_course(c)
        lines.append(f"{periods_str}  {course_line}")

    return "\n".join(lines)


def format_weekly_overview(
    week_info: dict,
    days_data: Dict[int, list],
    target_date: date = None,
) -> str:
    """格式化整周课表概览。"""
    current_week = week_info["current"]
    is_odd = week_info["is_odd"]
    week_type = "单周" if is_odd else "双周"
    total_weeks = week_info["total"]

    # 计算本周一的日期
    if target_date is None:
        target_date = date.today()
    monday = target_date - timedelta(days=target_date.isoweekday() - 1)

    lines = [
        "===== 本周课表概览 =====",
        f"第{current_week}周 ({week_type})  |  共{total_weeks}周",
        f"({monday.strftime('%m/%d')} - {(monday + timedelta(days=4)).strftime('%m/%d')})",
        "",
    ]

    if week_info.get("is_before"):
        lines.append("学期尚未开始。")
        return "\n".join(lines)
    if week_info.get("is_after"):
        lines.append("学期已结束。")
        return "\n".join(lines)

    has_any = False
    for day in range(1, 6):  # 周一 ~ 周五
        day_name = WEEKDAY_NAMES[day]
        courses = days_data.get(day, [])

        # 按节次排序
        courses_sorted = sorted(courses, key=lambda c: min(c.get("periods", [99])))

        if not courses_sorted:
            lines.append(f"{day_name}  无课")
        else:
            has_any = True
            lines.append(f"{day_name}:")
            for c in courses_sorted:
                periods_str = format_periods(c.get("periods", []))
                name = c.get("name", "未命名")
                location = c.get("location", "")
                extra = f" | {location}" if location else ""
                lines.append(f"  {periods_str}  {name}{extra}")
        lines.append("")

    if not has_any:
        lines.append("本周没有安排课程~")

    return "\n".join(lines)


def format_my_schedule(schedule: dict) -> str:
    """格式化完整课表。"""
    courses = schedule.get("courses", [])
    semester_start = schedule.get("semester_start", "未知")
    total_weeks = schedule.get("total_weeks", 20)

    lines = [
        "===== 我的课表 =====",
        f"学期开始: {semester_start}  |  共{total_weeks}周",
        "",
    ]

    if not courses:
        lines.append("暂无课程安排。")
        return "\n".join(lines)

    # 按星期分组
    day_groups: Dict[int, list] = {}
    for c in courses:
        day = c.get("day", 0)
        if day not in day_groups:
            day_groups[day] = []
        day_groups[day].append(c)

    for day in range(1, 8):
        if day not in day_groups:
            continue
        day_courses = day_groups[day]
        day_courses_sorted = sorted(day_courses, key=lambda c: min(c.get("periods", [99])))

        lines.append(f"【{WEEKDAY_NAMES[day]}】")
        for c in day_courses_sorted:
            periods_str = format_periods(c.get("periods", []))
            name = c.get("name", "未命名")
            location = c.get("location", "")
            teacher = c.get("teacher", "")
            weeks = c.get("weeks", [])

            # 格式化周次
            if not weeks:
                weeks_str = "全学期"
            elif len(weeks) <= 4:
                weeks_str = f"第{','.join(map(str, weeks))}周"
            else:
                weeks_str = f"第{weeks[0]}-{weeks[-1]}周"

            extras = []
            if location:
                extras.append(location)
            if teacher:
                extras.append(teacher)
            extra_str = " | " + " / ".join(extras) if extras else ""

            lines.append(f"  {periods_str}  {name}{extra_str}")
            lines.append(f"            {weeks_str}")
        lines.append("")

    return "\n".join(lines)
