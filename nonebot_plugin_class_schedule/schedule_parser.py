"""作息表解析模块"""

import re
from typing import List, Dict, Tuple, Optional

# 导入指南
SCHEDULE_IMPORT_GUIDE = """\
请发送作息表内容，格式如下:

早读 07:00-07:30
第1节 08:00-08:45
第2节 08:55-09:40
午休 12:00-14:00
第5节 14:00-14:45
晚自习 18:20-21:00

支持格式：
- 节次名称 + 时间段 (HH:MM-HH:MM)
- 使用 - 或 ~ 连接开始和结束时间

发送 /取消导入作息 取消操作"""

# 节次排序权重
PERIOD_ORDER = {
    "早读": 0, "早自习": 0,
    "第1节": 1, "第一节": 1,
    "第2节": 2, "第二节": 2,
    "第3节": 3, "第三节": 3,
    "第4节": 4, "第四节": 4,
    "午休": 5,
    "第5节": 6, "第五节": 6,
    "第6节": 7, "第六节": 7,
    "第7节": 8, "第七节": 8,
    "第8节": 9, "第八节": 9,
    "第9节": 10, "第九节": 10,
    "晚自习": 20, "晚修": 20,
}


def parse_schedule_text(text: str) -> Tuple[List[dict], List[str]]:
    """解析作息表文本
    
    Returns:
        (时间段列表, 错误信息列表)
    """
    schedule = []
    errors = []
    
    lines = text.strip().split("\n")
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        period = parse_period_line(line)
        if period:
            schedule.append(period)
        else:
            errors.append(f"第{line_num}行无法解析: {line}")
    
    # 按节次排序
    schedule.sort(key=lambda x: PERIOD_ORDER.get(x["name"], 99))
    
    return schedule, errors


def parse_period_line(line: str) -> Optional[dict]:
    """解析单行时间段
    
    格式: 节次名 开始时间-结束时间
    例如: 第1节 08:00-08:45
    """
    # 匹配时间格式 HH:MM-HH:MM 或 HH:MM~HH:MM
    time_pattern = r"(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})"
    time_match = re.search(time_pattern, line)
    
    if not time_match:
        return None
    
    start_time = time_match.group(1)
    end_time = time_match.group(2)
    
    # 节次名是时间前面的部分
    name_part = line[:time_match.start()].strip()
    if not name_part:
        return None
    
    return {
        "name": name_part,
        "start": start_time,
        "end": end_time,
    }


def validate_schedule(schedule: List[dict]) -> List[str]:
    """验证作息表，返回警告信息"""
    warnings = []
    
    if not schedule:
        warnings.append("没有识别到任何时间段")
        return warnings
    
    # 检查时间格式
    for period in schedule:
        start = period.get("start", "")
        end = period.get("end", "")
        
        if not re.match(r"^\d{1,2}:\d{2}$", start):
            warnings.append(f"{period['name']} 开始时间格式错误: {start}")
        if not re.match(r"^\d{1,2}:\d{2}$", end):
            warnings.append(f"{period['name']} 结束时间格式错误: {end}")
    
    # 检查时间重叠
    for i in range(len(schedule) - 1):
        current_end = schedule[i]["end"]
        next_start = schedule[i + 1]["start"]
        
        # 简单字符串比较 (假设都是同一天)
        if current_end > next_start:
            warnings.append(f"{schedule[i]['name']} 和 {schedule[i+1]['name']} 时间有重叠")
    
    return warnings


def format_schedule_for_review(schedule: List[dict]) -> str:
    """格式化作息表供用户确认"""
    lines = ["【作息表预览】", ""]
    
    for period in schedule:
        name = period.get("name", "未知")
        start = period.get("start", "?")
        end = period.get("end", "?")
        lines.append(f"  {name}: {start} - {end}")
    
    return "\n".join(lines)


def schedule_to_dict(schedule: List[dict]) -> Dict[str, dict]:
    """将作息表列表转换为字典格式"""
    result = {}
    for period in schedule:
        name = period.get("name", "")
        if name:
            result[name] = {
                "start": period.get("start", ""),
                "end": period.get("end", ""),
            }
    return result
