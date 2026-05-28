"""nonebot-plugin-class-schedule - 作息表解析器

支持格式：
早读 07:00-07:30
第1节 08:00-08:45
第2节 08:55-09:40
午休 12:00-14:00
晚自习 18:20-21:00

或：
早读 07:00 07:30
第1节 08:00 08:45
"""

import re
from typing import List, Dict, Tuple, Optional

# 节次名称映射
PERIOD_NAMES = {
    0: ["早读", "早自习", "早读时间"],
    1: ["第1节", "第一节", "1节"],
    2: ["第2节", "第二节", "2节"],
    3: ["第3节", "第三节", "3节"],
    4: ["第4节", "第四节", "4节"],
    5: ["第5节", "第五节", "5节"],
    6: ["第6节", "第六节", "6节"],
    7: ["第7节", "第七节", "7节"],
    8: ["第8节", "第八节", "8节"],
    9: ["晚自习", "晚自习时间", "晚上"],
    10: ["午休", "中午", "午间"],
    11: ["午间", "午饭", "中午休息"],
    12: ["下午", "下午时间"],
    13: ["课外", "课外活动"],
}


def parse_period_name(text: str) -> Optional[int]:
    """识别节次名称，返回节次数。"""
    text = text.strip()
    for period, names in PERIOD_NAMES.items():
        for name in names:
            if name in text or text.startswith(name):
                return period
    return None


def parse_time_range(text: str) -> Optional[Tuple[str, str]]:
    """解析时间范围。"""
    text = text.strip()
    
    # 格式1: 08:00-08:45
    m = re.match(r"(\d{1,2}):(\d{2})\s*[-~至]\s*(\d{1,2}):(\d{2})", text)
    if m:
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        end = f"{int(m.group(3)):02d}:{m.group(4)}"
        return (start, end)
    
    # 格式2: 08:00 08:45 (两个空格分开)
    m = re.match(r"(\d{1,2}):(\d{2})\s+(\d{1,2}):(\d{2})", text)
    if m:
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        end = f"{int(m.group(3)):02d}:{m.group(4)}"
        return (start, end)
    
    # 格式3: 08:00 (只有开始时间)
    m = re.match(r"(\d{1,2}):(\d{2})", text)
    if m:
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        return (start, None)
    
    return None


def parse_schedule_text(text: str) -> Tuple[List[Tuple[int, str, str]], List[str]]:
    """解析作息表文本，返回 [(节次, 开始时间, 结束时间), ...], 错误列表。"""
    lines = text.split("\n")
    schedule = []
    errors = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # 跳过明显的说明文字
        if "格式" in line or "示例" in line or "请按" in line:
            continue
        
        # 尝试解析节次
        period = None
        remaining = line
        
        for p, names in PERIOD_NAMES.items():
            for name in names:
                if line.startswith(name):
                    period = p
                    remaining = line[len(name):].strip()
                    break
            if period is not None:
                break
        
        if period is None:
            # 尝试在中间找节次名
            for p, names in PERIOD_NAMES.items():
                for name in names:
                    if name in line:
                        period = p
                        idx = line.index(name)
                        remaining = line[:idx].strip() + " " + line[idx + len(name):].strip()
                        break
                if period is not None:
                    break
        
        if period is None:
            # 尝试用数字识别
            m = re.match(r"第?(.)节", line)
            if m:
                num = m.group(1)
                period_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8}
                if num in period_map:
                    period = period_map[num]
                    remaining = line[m.end():].strip()
        
        if period is None:
            continue
        
        # 解析时间
        times = parse_time_range(remaining)
        if times is None:
            errors.append(f"第{i}行无法识别时间: {line}")
            continue
        
        start_time, end_time = times
        if end_time is None:
            errors.append(f"第{i}行缺少结束时间: {line}")
            continue
        
        schedule.append((period, start_time, end_time))
    
    # 按开始时间排序
    schedule.sort(key=lambda x: x[1])
    return schedule, errors


def validate_schedule(schedule: List[Tuple[int, str, str]]) -> List[str]:
    """验证作息表，返回警告列表。"""
    warnings = []
    
    if not schedule:
        warnings.append("作息表为空")
        return warnings
    
    # 检查早读
    has_morning = any(p == 0 for p, _, _ in schedule)
    if not has_morning:
        warnings.append("未识别到早读时间")
    
    # 检查晚自习
    has_evening = any(p == 9 for p, _, _ in schedule)
    if not has_evening:
        warnings.append("未识别到晚自习时间")
    
    # 检查时间重叠
    for i, (p1, s1, e1) in enumerate(schedule):
        for p2, s2, e2 in schedule[i+1:]:
            if s1 < e2 and s2 < e1:
                p1_name = get_period_display_name(p1)
                p2_name = get_period_display_name(p2)
                warnings.append(f"{p1_name}({s1}-{e1}) 和 {p2_name}({s2}-{e2}) 时间重叠")
    
    return warnings


def get_period_display_name(period: int) -> str:
    """获取节次显示名称。"""
    names = {
        0: "早读", 1: "第1节", 2: "第2节", 3: "第3节", 4: "第4节",
        5: "第5节", 6: "第6节", 7: "第7节", 8: "第8节",
        9: "晚自习", 10: "午休", 11: "午间", 12: "下午", 13: "课外"
    }
    return names.get(period, f"第{period}节")


def format_schedule_for_review(schedule: List[Tuple[int, str, str]]) -> str:
    """格式化作息表用于预览。"""
    if not schedule:
        return "未识别到作息表"
    
    lines = ["作息表预览：", ""]
    for period, start, end in schedule:
        name = get_period_display_name(period)
        lines.append(f"  {name}  {start}-{end}")
    
    return "\n".join(lines)


def schedule_to_dict(schedule: List[Tuple[int, str, str]]) -> List[Dict]:
    """转换为标准格式。"""
    return [
        {"period": p, "start": s, "end": e}
        for p, s, e in schedule
    ]


# ===== 导入格式示例 =====

SCHEDULE_IMPORT_GUIDE = """
请按以下格式发送作息表：

早读 07:00-07:30
第1节 08:00-08:45
第2节 08:55-09:40
第3节 10:00-10:45
第4节 10:55-11:40
午休 12:00-14:00
第5节 14:00-14:45
第6节 14:55-15:40
第7节 15:55-16:40
第8节 16:50-17:35
晚自习 18:20-21:00

支持格式：
• 节次名 + 时间范围
• 时间: 08:00-08:45 或 08:00 08:45
• 节次: 早读/第1节/第一节/1节/晚自习

发送 /取消导入作息 退出导入模式
"""
