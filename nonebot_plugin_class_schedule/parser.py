"""课表解析模块"""

import re
from typing import List, Dict, Tuple

# 导入课表命令指南
IMPORT_COMMAND_GUIDE = """\
请发送课表内容，格式如下:

周一：
早读 英语（李老师）
第1节 数学 @A201
第2节 物理(王老师)
第3节 化学
晚自习 语文

周二：
第1节 英语
第2节 数学
...

支持格式：
- 星期：周一/星期一/周一：
- 节次：早读/第1节/第一节/1节/晚自习
- 老师：(老师名) 或（老师名）
- 地点：@地点 或 #地点

发送 /取消导入 取消操作"""

IMPORT_FORMAT = """\
示例格式：
周一：
早读 物理（钱老师）
第1节 生物(张老师)
第2节 化学 @B305

周二：
...
"""

# 星期映射
DAY_MAP = {
    "周一": 0, "星期一": 0, "1": 0, "一": 0,
    "周二": 1, "星期二": 1, "2": 1, "二": 1,
    "周三": 2, "星期三": 2, "3": 2, "三": 2,
    "周四": 3, "星期四": 3, "4": 3, "四": 3,
    "周五": 4, "星期五": 4, "5": 4, "五": 4,
    "周六": 5, "星期六": 5, "6": 5, "六": 5,
    "周日": 6, "星期日": 6, "星期天": 6, "7": 6, "日": 6,
}

# 节次映射
PERIOD_MAP = {
    "早读": 0, "早自习": 0,
    "第1节": 1, "第一节": 1, "1节": 1,
    "第2节": 2, "第二节": 2, "2节": 2,
    "第3节": 3, "第三节": 3, "3节": 3,
    "第4节": 4, "第四节": 4, "4节": 4,
    "第5节": 5, "第五节": 5, "5节": 5,
    "第6节": 6, "第六节": 6, "6节": 6,
    "第7节": 7, "第七节": 7, "7节": 7,
    "第8节": 8, "第八节": 8, "8节": 8,
    "第9节": 9, "第九节": 9, "9节": 9,
    "晚自习": 10, "晚修": 10,
}


def parse_schedule_text(text: str) -> Tuple[List[dict], List[str]]:
    """解析课表文本
    
    Returns:
        (课程列表, 错误信息列表)
    """
    courses = []
    errors = []
    
    lines = text.strip().split("\n")
    current_day = None
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # 检查是否是星期行
        day_match = re.match(r"^(周[一二三四五六日]|星期[一二三四五六日])[：:]?$", line)
        if day_match:
            day_str = day_match.group(1)
            current_day = DAY_MAP.get(day_str)
            continue
        
        # 解析课程行
        if current_day is not None:
            course = parse_course_line(line)
            if course:
                course["day"] = current_day
                courses.append(course)
            else:
                errors.append(f"第{line_num}行无法解析: {line}")
    
    return courses, errors


def parse_course_line(line: str) -> dict:
    """解析单行课程信息"""
    # 匹配模式: 节次 课程名 (老师) @地点
    # 或: 节次 课程名
    
    # 提取节次
    period_pattern = r"^(早读|早自习|第?\d+节|晚自习|晚修)[：:\s]*"
    period_match = re.match(period_pattern, line)
    
    if not period_match:
        return None
    
    period_str = period_match.group(1)
    period_num = PERIOD_MAP.get(period_str, 0)
    
    # 剩余部分
    remaining = line[period_match.end():].strip()
    if not remaining:
        return None
    
    # 提取老师 (中文括号或英文括号)
    teacher = ""
    teacher_match = re.search(r"[（(]([^）)]+)[）)]", remaining)
    if teacher_match:
        teacher = teacher_match.group(1)
        remaining = remaining[:teacher_match.start()] + remaining[teacher_match.end():]
    
    # 提取地点 (@或#开头)
    location = ""
    location_match = re.search(r"[@#](\S+)", remaining)
    if location_match:
        location = location_match.group(1)
        remaining = remaining[:location_match.start()] + remaining[location_match.end():]
    
    # 课程名是剩余部分
    name = remaining.strip()
    
    return {
        "period": period_num,
        "period_name": period_str,
        "name": name,
        "teacher": teacher,
        "location": location,
        "weeks": [],  # 空列表表示所有周
    }


def validate_schedule(courses: List[dict]) -> List[str]:
    """验证课表，返回警告信息"""
    warnings = []
    
    if not courses:
        warnings.append("没有识别到任何课程")
        return warnings
    
    # 检查重复课程
    seen = set()
    for course in courses:
        key = (course.get("day"), course.get("period"))
        if key in seen:
            day_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][key[0]]
            warnings.append(f"{day_name}第{key[1]}节有重复课程")
        seen.add(key)
    
    # 检查是否有课程名
    for course in courses:
        if not course.get("name"):
            warnings.append(f"第{course.get('day')+1}天第{course.get('period')}节缺少课程名")
    
    return warnings


def format_schedule_for_review(courses: List[dict]) -> str:
    """格式化课表供用户确认"""
    lines = ["【课表预览】", ""]
    
    # 按星期分组
    by_day = {i: [] for i in range(7)}
    for course in courses:
        day = course.get("day", 0)
        by_day[day].append(course)
    
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    for day_idx in range(7):
        day_courses = by_day[day_idx]
        if day_courses:
            lines.append(f"\n{day_names[day_idx]}:")
            day_courses.sort(key=lambda x: x.get("period", 0))
            for c in day_courses:
                period = c.get("period_name", f"第{c.get('period', '?')}节")
                name = c.get("name", "未知")
                teacher = c.get("teacher", "")
                loc = c.get("location", "")
                
                parts = [f"  {period}: {name}"]
                if teacher:
                    parts.append(f"({teacher})")
                if loc:
                    parts.append(f"@{loc}")
                lines.append(" ".join(parts))
    
    return "\n".join(lines)
