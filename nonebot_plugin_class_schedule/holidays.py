"""节假日数据模块"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

# 2026-2027年法定节假日数据 (示例数据)
HOLIDAYS_2026 = {
    # 元旦
    "2026-01-01": "元旦",
    "2026-01-02": "元旦",
    "2026-01-03": "元旦",
    
    # 春节
    "2026-02-17": "春节",
    "2026-02-18": "春节",
    "2026-02-19": "春节",
    "2026-02-20": "春节",
    "2026-02-21": "春节",
    "2026-02-22": "春节",
    "2026-02-23": "春节",
    
    # 清明节
    "2026-04-04": "清明节",
    "2026-04-05": "清明节",
    "2026-04-06": "清明节",
    
    # 劳动节
    "2026-05-01": "劳动节",
    "2026-05-02": "劳动节",
    "2026-05-03": "劳动节",
    "2026-05-04": "劳动节",
    "2026-05-05": "劳动节",
    
    # 端午节
    "2026-06-19": "端午节",
    "2026-06-20": "端午节",
    "2026-06-21": "端午节",
    
    # 中秋节
    "2026-09-25": "中秋节",
    "2026-09-26": "中秋节",
    "2026-09-27": "中秋节",
    
    # 国庆节
    "2026-10-01": "国庆节",
    "2026-10-02": "国庆节",
    "2026-10-03": "国庆节",
    "2026-10-04": "国庆节",
    "2026-10-05": "国庆节",
    "2026-10-06": "国庆节",
    "2026-10-07": "国庆节",
    "2026-10-08": "国庆节",
}

# 调休工作日 (周末需要上班)
WORKDAYS_2026 = {
    "2026-02-14": "春节调休",
    "2026-02-15": "春节调休",
    "2026-04-11": "清明调休",
    "2026-04-12": "清明调休",
    "2026-04-25": "劳动节调休",
    "2026-05-09": "劳动节调休",
    "2026-06-13": "端午调休",
    "2026-06-14": "端午调休",
    "2026-09-19": "中秋调休",
    "2026-09-20": "中秋调休",
    "2026-09-26": "国庆调休",
    "2026-10-10": "国庆调休",
}


def is_holiday(target_date: date = None) -> bool:
    """检查指定日期是否为节假日
    
    Args:
        target_date: 目标日期，默认为今天
    
    Returns:
        是否为节假日
    """
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime("%Y-%m-%d")
    
    # 检查是否在节假日列表
    if date_str in HOLIDAYS_2026:
        return True
    
    # 检查是否为调休工作日
    if date_str in WORKDAYS_2026:
        return False
    
    # 检查是否为周末
    weekday = target_date.weekday()
    if weekday >= 5:  # 周六或周日
        return True
    
    return False


def get_holiday_name(target_date: date = None) -> Optional[str]:
    """获取指定日期的节假日名称
    
    Args:
        target_date: 目标日期，默认为今天
    
    Returns:
        节假日名称，如果不是节假日则返回 None
    """
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime("%Y-%m-%d")
    
    # 检查是否在节假日列表
    if date_str in HOLIDAYS_2026:
        return HOLIDAYS_2026[date_str]
    
    # 检查是否为周末
    weekday = target_date.weekday()
    if weekday >= 5:
        return "周末"
    
    return None


def get_workday_reason(target_date: date = None) -> Optional[str]:
    """获取调休工作日的说明
    
    Args:
        target_date: 目标日期，默认为今天
    
    Returns:
        调休说明，如果不是调休工作日则返回 None
    """
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime("%Y-%m-%d")
    return WORKDAYS_2026.get(date_str)


def get_next_holiday(target_date: date = None) -> Optional[Tuple[date, str, int]]:
    """获取下一个节假日
    
    Args:
        target_date: 目标日期，默认为今天
    
    Returns:
        (节假日日期, 节假日名称, 距离天数) 元组，如果没有则返回 None
    """
    if target_date is None:
        target_date = date.today()
    
    # 遍历节假日列表，找到最近的未来节假日
    for date_str, name in sorted(HOLIDAYS_2026.items()):
        holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if holiday_date > target_date:
            days_left = (holiday_date - target_date).days
            return (holiday_date, name, days_left)
    
    return None


def get_holiday_status(target_date: date = None) -> str:
    """获取指定日期的节假日状态描述
    
    Args:
        target_date: 目标日期，默认为今天
    
    Returns:
        状态描述字符串
    """
    if target_date is None:
        target_date = date.today()
    
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # 检查是否在节假日列表
    if date_str in HOLIDAYS_2026:
        holiday_name = HOLIDAYS_2026[date_str]
        return f"今天是{holiday_name}假期 ({weekday_names[weekday]})"
    
    # 检查是否为调休工作日
    if date_str in WORKDAYS_2026:
        reason = WORKDAYS_2026[date_str]
        return f"今天是调休工作日 ({reason})"
    
    # 检查是否为周末
    if weekday >= 5:
        return f"今天是周末 ({weekday_names[weekday]})"
    
    # 工作日
    next_holiday = get_next_holiday(target_date)
    if next_holiday:
        holiday_date, name, days_left = next_holiday
        return f"今天是工作日 ({weekday_names[weekday]})\n距离{name}还有 {days_left} 天"
    
    return f"今天是工作日 ({weekday_names[weekday]})"
