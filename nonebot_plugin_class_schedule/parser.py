"""nonebot-plugin-class-schedule - 课表解析器

支持多种格式的课表文本导入：
- 格式1: 每行一门课
  周一：
  早读 物理（钱晓晶）
  第1节 生物(张建坤)
  第2节 数学 @A201
  第3节 英语（王老师）
  晚自习 数学
  
- 格式2: 紧凑格式（用空格分隔）
  周一：早读 物理 第1节 生物 第2节 数学

支持识别：课程名、老师、地点
"""

import re
from datetime import date
from typing import List, Dict, Optional, Tuple

# 星期映射
DAY_PATTERNS = {
    1: ["周一", "星期一", "周一：", "星期一：", "周一 ", "星期一 "],
    2: ["周二", "星期二", "周二：", "星期二：", "周二 ", "星期二 "],
    3: ["周三", "星期三", "周三：", "星期三：", "周三 ", "星期三 "],
    4: ["周四", "星期四", "周四：", "星期四：", "周四 ", "星期四 "],
    5: ["周五", "星期五", "周五：", "星期五：", "周五 ", "星期五 "],
    6: ["周六", "星期六", "周六：", "星期六：", "周六 ", "星期六 "],
    7: ["周日", "星期日", "周日：", "星期日：", "周日 ", "星期日 "],
}

# 节次映射
PERIOD_PATTERNS = {
    0: ["早读", "早读", "早读"],
    1: ["第1节", "第1节课", "1节", "第一节", "第1节"],
    2: ["第2节", "第2节课", "2节", "第二节", "第2节"],
    3: ["第3节", "第3节课", "3节", "第三节", "第3节"],
    4: ["第4节", "第4节课", "4节", "第四节", "第4节"],
    5: ["第5节", "第5节课", "5节", "第五节", "第5节"],
    6: ["第6节", "第6节课", "6节", "第六节", "第6节"],
    7: ["第7节", "第7节课", "7节", "第七节", "第7节"],
    8: ["第8节", "第8节课", "8节", "第八节", "第8节"],
    9: ["晚自习", "晚自习", "晚上"],
}


def parse_period(text: str) -> Optional[int]:
    """识别节次，返回节次数（0=早读, 1-8=第1-8节, 9=晚自习），None表示未识别。"""
    text = text.strip()
    for period, patterns in PERIOD_PATTERNS.items():
        for p in patterns:
            if p in text:
                return period
    return None


def parse_day(text: str) -> Optional[int]:
    """识别星期几，返回1-7，None表示未识别。"""
    text = text.strip().rstrip("：:").strip()
    for day, patterns in DAY_PATTERNS.items():
        for p in patterns:
            if text == p or text.startswith(p):
                return day
    return None


def parse_course_line(line: str) -> Optional[Dict]:
    """解析一行课程信息。"""
    line = line.strip()
    if not line:
        return None
    
    # 跳过星期标题和空行
    if parse_day(line) is not None:
        return None
    if not line or line.startswith("#"):
        return None
    
    # 识别节次
    period = parse_period(line)
    if period is None:
        return None
    
    # 提取课程名、老师、地点
    course_info = line
    
    # 移除节次前缀
    for patterns in PERIOD_PATTERNS.values():
        for p in patterns:
            if p in course_info:
                course_info = course_info.replace(p, "").strip()
                break
    
    # 解析 (老师) 或（老师）
    teacher = ""
    m = re.search(r"[（(]([^）)]+)[）)]", course_info)
    if m:
        teacher = m.group(1).strip()
        course_info = re.sub(r"[（(][^）)]+[）)]", "", course_info).strip()
    
    # 解析 @地点 或 #地点
    location = ""
    m = re.search(r"[@#]([^@\s#]+)", course_info)
    if m:
        location = m.group(1).strip()
        course_info = re.sub(r"[@#][^@\s#]+", "", course_info).strip()
    
    course_name = course_info.strip()
    
    if not course_name:
        return None
    
    return {
        "name": course_name,
        "periods": [period],
        "teacher": teacher,
        "location": location,
    }


def parse_schedule_text(text: str) -> Tuple[List[Dict], List[str]]:
    """解析课表文本，返回 (课程列表, 错误列表)。"""
    lines = text.split("\n")
    courses = []
    errors = []
    current_day = None
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # 识别星期
        day = parse_day(line)
        if day is not None:
            current_day = day
            # 检查是否是纯星期标题（如"周一："）
            remaining = line
            for p in DAY_PATTERNS[day]:
                remaining = remaining.replace(p, "")
            remaining = remaining.strip("：:")
            if not remaining:
                continue
            # 如果有内容，继续解析
            line = remaining
        
        # 如果没有指定星期，跳过
        if current_day is None:
            continue
        
        # 解析课程
        course = parse_course_line(line)
        if course:
            course["day"] = current_day
            courses.append(course)
        elif parse_period(line) is not None:
            # 识别到节次但无法解析
            errors.append(f"第{i}行无法解析: {line}")
    
    return courses, errors


def validate_schedule(courses: List[Dict]) -> List[str]:
    """验证课表，返回警告列表。"""
    warnings = []
    
    # 检查是否有课程
    if not courses:
        warnings.append("没有识别到任何课程")
        return warnings
    
    # 检查每天是否有课
    days_with_courses = set(c.get("day") for c in courses)
    for day in range(1, 6):
        if day not in days_with_courses:
            warnings.append(f"周一到周五中，{['一','二','三','四','五'][day-1]}没有课程")
    
    # 检查重复课程
    for day in range(1, 8):
        day_courses = [c for c in courses if c.get("day") == day]
        period_counts = {}
        for c in day_courses:
            for p in c.get("periods", []):
                period_counts[p] = period_counts.get(p, 0) + 1
        
        for p, count in period_counts.items():
            if count > 1:
                p_name = ["早读","第1节","第2节","第3节","第4节","第5节","第6节","第7节","第8节","晚自习"][p]
                warnings.append(f"周{['一','二','三','四','五','六','日'][day-1]} {p_name} 有{count}门课（请确认是否正确）")
    
    return warnings


def format_schedule_for_review(courses: List[Dict]) -> str:
    """格式化课表用于预览。"""
    if not courses:
        return "未识别到课程"
    
    # 按星期分组
    days = {i: [] for i in range(1, 8)}
    for c in courses:
        day = c.get("day", 1)
        days[day].append(c)
    
    lines = ["课表预览：", ""]
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    for day in range(1, 8):
        if not days[day]:
            continue
        lines.append(f"【{day_names[day]}】")
        
        # 按节次排序
        sorted_courses = sorted(days[day], key=lambda c: min(c.get("periods", [99])))
        
        for c in sorted_courses:
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
        
        lines.append("")
    
    return "\n".join(lines)


# ===== 导入格式示例 =====

IMPORT_FORMAT = """
课表导入格式示例：

周一：
早读 英语（李老师）
第1节 数学 @A201
第2节 物理(王老师) @B302
第3节 化学
晚自习 语文

周二：
第1节 英语
第2节 数学
...

支持格式：
• 早读/第1-8节/晚自习 + 课程名
• 课程后可跟 (老师) 或 @地点
• 星期支持：周一/星期一/周一：
• 节次支持：第1节/第一节/1节

直接发送课表内容即可导入~
"""


IMPORT_COMMAND_GUIDE = """
请按以下格式发送课表：

周一：
早读 英语（李老师）
第1节 数学 @A201
第2节 物理(王老师)
...

支持格式：
• 早读/第1-8节/晚自习 + 课程名
• (老师) 表示老师
• @地点 表示上课地点

发送 /取消导入 退出导入模式
"""
