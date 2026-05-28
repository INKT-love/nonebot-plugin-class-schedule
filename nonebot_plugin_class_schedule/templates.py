"""HTML模板模块 - 用于图片渲染"""

# 基础样式
BASE_STYLE = """
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
body {
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    min-height: 100vh;
}
.container {
    background: white;
    border-radius: 16px;
    padding: 24px;
    max-width: 600px;
    margin: 0 auto;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
.header {
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid #f0f0f0;
}
.header h1 {
    color: #333;
    font-size: 24px;
    margin-bottom: 8px;
}
.header .subtitle {
    color: #666;
    font-size: 14px;
}
.course-item {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 4px solid #667eea;
}
.course-item.current {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-left: 4px solid #fff;
}
.course-item.current .course-name,
.course-item.current .course-info {
    color: white;
}
.course-period {
    font-size: 12px;
    color: #888;
    margin-bottom: 4px;
}
.course-item.current .course-period {
    color: rgba(255,255,255,0.8);
}
.course-name {
    font-size: 18px;
    font-weight: bold;
    color: #333;
    margin-bottom: 8px;
}
.course-info {
    font-size: 14px;
    color: #666;
}
.course-info span {
    margin-right: 16px;
}
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 12px;
}
.status-studying {
    background: #e3f2fd;
    color: #1976d2;
}
.status-break {
    background: #fff3e0;
    color: #f57c00;
}
.status-finished {
    background: #e8f5e9;
    color: #388e3c;
}
.week-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    margin-top: 16px;
}
.week-day {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px 8px;
    text-align: center;
}
.week-day-header {
    font-weight: bold;
    color: #333;
    margin-bottom: 8px;
    font-size: 14px;
}
.week-day-courses {
    font-size: 12px;
    color: #666;
    line-height: 1.6;
}
.empty {
    text-align: center;
    color: #999;
    padding: 40px;
    font-size: 16px;
}
.countdown {
    text-align: center;
    margin-top: 16px;
    padding: 12px;
    background: #fff3e0;
    border-radius: 8px;
    color: #f57c00;
    font-weight: bold;
}
</style>
"""


def render_day_schedule_html(day_name: str, courses: list, schedule: dict) -> str:
    """渲染某天课程表的 HTML"""
    courses_html = ""
    for course in courses:
        period = course.get("period_name", f"第{course.get('period', '?')}节")
        name = course.get("name", "未知课程")
        teacher = course.get("teacher", "")
        location = course.get("location", "")
        
        info_parts = []
        if teacher:
            info_parts.append(f"👤 {teacher}")
        if location:
            info_parts.append(f"📍 {location}")
        
        info_html = f'<div class="course-info">{" | ".join(info_parts)}</div>' if info_parts else ""
        
        courses_html += f"""
        <div class="course-item">
            <div class="course-period">{period}</div>
            <div class="course-name">{name}</div>
            {info_html}
        </div>
        """
    
    if not courses:
        courses_html = '<div class="empty">今天没有课程安排</div>'
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{day_name}课程表</h1>
            <div class="subtitle">共 {len(courses)} 门课程</div>
        </div>
        {courses_html}
    </div>
</body>
</html>
"""


def render_now_course_html(day_name: str, status: str, period_name: str, course: dict = None) -> str:
    """渲染当前课程状态的 HTML"""
    if status == "上课中":
        status_class = "status-studying"
        status_text = "正在上课"
    elif status == "课间":
        status_class = "status-break"
        status_text = "课间休息"
    elif status == "放学后":
        status_class = "status-finished"
        status_text = "今日课程已结束"
    else:
        status_class = "status-break"
        status_text = status
    
    if course:
        name = course.get("name", "未知课程")
        teacher = course.get("teacher", "")
        location = course.get("location", "")
        
        info_parts = []
        if teacher:
            info_parts.append(f"👤 {teacher}")
        if location:
            info_parts.append(f"📍 {location}")
        
        info_html = f'<div class="course-info">{" | ".join(info_parts)}</div>' if info_parts else ""
        
        course_html = f"""
        <div class="course-item current">
            <div class="course-period">{period_name}</div>
            <div class="course-name">{name}</div>
            {info_html}
        </div>
        """
    else:
        course_html = f'<div class="empty">{period_name}</div>'
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{day_name} - 当前状态</h1>
            <div class="subtitle">{status_text}</div>
        </div>
        <div class="status-badge {status_class}">{status_text}</div>
        {course_html}
    </div>
</body>
</html>
"""


def render_next_course_html(day_name: str, next_period: tuple, course: dict = None, minutes_left: int = 0) -> str:
    """渲染下一节课的 HTML"""
    if next_period:
        period_name, start_time, end_time = next_period
        time_str = f"{start_time} - {end_time}"
        
        if course:
            name = course.get("name", "未知课程")
            teacher = course.get("teacher", "")
            location = course.get("location", "")
            
            info_parts = []
            if teacher:
                info_parts.append(f"👤 {teacher}")
            if location:
                info_parts.append(f"📍 {location}")
            
            info_html = f'<div class="course-info">{" | ".join(info_parts)}</div>' if info_parts else ""
            
            course_html = f"""
            <div class="course-item">
                <div class="course-period">{period_name} ({time_str})</div>
                <div class="course-name">{name}</div>
                {info_html}
            </div>
            """
        else:
            course_html = f"""
            <div class="course-item">
                <div class="course-period">{period_name} ({time_str})</div>
                <div class="course-name">暂无课程安排</div>
            </div>
            """
        
        countdown_html = f'<div class="countdown">⏰ 距离上课还有 {minutes_left} 分钟</div>' if minutes_left > 0 else ""
    else:
        course_html = '<div class="empty">今天没有更多课程了</div>'
        countdown_html = ""
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{day_name} - 下一节课</h1>
            <div class="subtitle">即将开始</div>
        </div>
        {course_html}
        {countdown_html}
    </div>
</body>
</html>
"""


def render_week_overview_html(week_courses: dict, week: int, parity: str) -> str:
    """渲染本周概览的 HTML"""
    days_html = ""
    for day_idx in range(5):  # 周一到周五
        day_name = ["周一", "周二", "周三", "周四", "周五"][day_idx]
        courses = week_courses.get(day_idx, [])
        
        if courses:
            course_names = "<br>".join([c.get("name", "未知") for c in courses])
        else:
            course_names = "无课"
        
        days_html += f"""
        <div class="week-day">
            <div class="week-day-header">{day_name}</div>
            <div class="week-day-courses">{course_names}</div>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>第{week}周课程概览</h1>
            <div class="subtitle">{parity}</div>
        </div>
        <div class="week-grid">
            {days_html}
        </div>
    </div>
</body>
</html>
"""


def render_my_schedule_html(schedule: dict) -> str:
    """渲染完整课表的 HTML"""
    semester_start = schedule.get("semester_start", "未设置")
    total_weeks = schedule.get("total_weeks", 20)
    courses = schedule.get("courses", [])
    
    # 按星期分组
    by_day = {i: [] for i in range(7)}
    for course in courses:
        day = course.get("day", 0)
        by_day[day].append(course)
    
    days_html = ""
    for day_idx in range(7):
        day_courses = by_day[day_idx]
        if not day_courses:
            continue
        
        day_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day_idx]
        day_courses.sort(key=lambda x: x.get("period", 0))
        
        courses_html = ""
        for c in day_courses:
            period = c.get("period_name", f"第{c.get('period', '?')}节")
            name = c.get("name", "未知")
            teacher = c.get("teacher", "")
            loc = c.get("location", "")
            
            info_parts = [name]
            if teacher:
                info_parts.append(f"({teacher})")
            if loc:
                info_parts.append(f"@{loc}")
            
            courses_html += f"""
            <div class="course-item">
                <div class="course-period">{period}</div>
                <div class="course-name">{' '.join(info_parts)}</div>
            </div>
            """
        
        days_html += f"""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #667eea; margin-bottom: 12px;">{day_name}</h3>
            {courses_html}
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>我的完整课表</h1>
            <div class="subtitle">学期开始: {semester_start} | 总周数: {total_weeks} | 课程数: {len(courses)}</div>
        </div>
        {days_html}
    </div>
</body>
</html>
"""
