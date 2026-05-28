"""nonebot-plugin-class-schedule - 图片渲染模板"""

from datetime import date, datetime
from typing import Dict, List, Optional

# ===== 通用样式 =====

BASE_STYLE = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  min-height: 100vh;
  padding: 40px 28px;
  color: #e8eaf6;
  font-size: 18px;
}
.container { max-width: 800px; margin: 0 auto; }
.header {
  text-align: center;
  margin-bottom: 32px;
  padding: 28px;
  background: linear-gradient(135deg, rgba(103, 58, 183, 0.15), rgba(63, 81, 181, 0.1));
  border-radius: 20px;
  border: 1px solid rgba(156, 39, 176, 0.2);
}
.header h1 {
  font-size: 42px;
  font-weight: 700;
  background: linear-gradient(135deg, #ce93d8, #9fa8da, #80deea);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 10px;
}
.header .subtitle { color: #90a4ae; font-size: 18px; }
.info-bar {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.info-tag {
  background: rgba(103, 58, 183, 0.2);
  padding: 8px 18px;
  border-radius: 24px;
  font-size: 16px;
  color: #ce93d8;
}
.card {
  background: linear-gradient(145deg, rgba(30, 40, 60, 0.8), rgba(20, 30, 50, 0.6));
  border-radius: 16px;
  padding: 22px 26px;
  margin-bottom: 16px;
  border: 1px solid rgba(103, 58, 183, 0.15);
  display: flex;
  align-items: center;
  gap: 20px;
}
.period-badge {
  background: linear-gradient(135deg, #7c4dff, #536dfe);
  padding: 14px 18px;
  border-radius: 14px;
  font-weight: 600;
  font-size: 18px;
  min-width: 90px;
  text-align: center;
  white-space: nowrap;
}
.period-badge.early { background: linear-gradient(135deg, #ff7043, #ff5722); }
.period-badge.night { background: linear-gradient(135deg, #5c6bc0, #3f51b5); }
.course-info { flex: 1; }
.course-name { font-size: 22px; font-weight: 600; color: #e8eaf6; margin-bottom: 6px; }
.course-meta { font-size: 16px; color: #90a4ae; }
.course-meta span { margin-right: 16px; }
.status-card {
  background: linear-gradient(145deg, rgba(30, 40, 60, 0.9), rgba(20, 30, 50, 0.7));
  border-radius: 24px;
  padding: 40px;
  text-align: center;
  border: 1px solid rgba(103, 58, 183, 0.2);
  margin-bottom: 24px;
}
.status-icon { width: 72px; height: 72px; margin: 0 auto 16px; }
.status-text { font-size: 32px; font-weight: 700; color: #ce93d8; margin-bottom: 12px; }
.status-detail { font-size: 20px; color: #90a4ae; }
.countdown { font-size: 36px; font-weight: 700; color: #80deea; margin-top: 16px; }
.week-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.day-column { background: rgba(20, 30, 50, 0.5); border-radius: 16px; padding: 16px; }
.day-name { text-align: center; font-weight: 600; color: #ce93d8; margin-bottom: 12px; font-size: 18px; }
.mini-course {
  background: rgba(103, 58, 183, 0.15);
  padding: 10px 12px;
  border-radius: 10px;
  margin-bottom: 8px;
  font-size: 14px;
}
.mini-course .name { color: #e8eaf6; font-weight: 500; }
.mini-course .period { color: #90a4ae; font-size: 12px; }
.footer {
  text-align: center;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid rgba(103, 58, 183, 0.15);
  color: #546e7a;
  font-size: 16px;
}
"""


def render_day_schedule_html(
    target_date: date,
    day_index: int,
    week_info: dict,
    courses: list,
    title: str = None,
) -> str:
    """渲染某天课表的 HTML。"""
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    week_type = "单周" if week_info.get("is_odd") else "双周"
    
    if title is None:
        title = f"{day_names[day_index]}课表"

    courses_html = ""
    for c in sorted(courses, key=lambda x: min(x.get("periods", [99]))):
        periods = c.get("periods", [])
        p = periods[0] if periods else 0
        
        # 节次标签
        if p == 0:
            period_label = "早读"
            badge_class = "early"
        elif p == 9:
            period_label = "晚自习"
            badge_class = "night"
        else:
            period_label = f"第{p}节"
            badge_class = ""
        
        name = c.get("name", "未命名")
        location = c.get("location", "")
        teacher = c.get("teacher", "")
        
        meta_parts = []
        if location:
            meta_parts.append(f"地点: {location}")
        if teacher:
            meta_parts.append(f"老师: {teacher}")
        
        courses_html += f"""
        <div class="card">
          <div class="period-badge {badge_class}">{period_label}</div>
          <div class="course-info">
            <div class="course-name">{name}</div>
            <div class="course-meta">{' '.join(meta_parts)}</div>
          </div>
        </div>"""

    if not courses:
        courses_html = """
        <div class="status-card">
          <div class="status-icon">🎉</div>
          <div class="status-text">今天没有课</div>
          <div class="status-detail">可以好好休息啦~</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="subtitle">{target_date.strftime('%Y年%m月%d日')}</div>
    <div class="info-bar">
      <span class="info-tag">第{week_info['current']}周</span>
      <span class="info-tag">{week_type}</span>
    </div>
  </div>
  {courses_html}
  <div class="footer">发送 /课程表帮助 查看更多命令</div>
</div>
</body>
</html>"""


def render_now_course_html(
    period_info: dict,
    current_course: dict = None,
    next_course: dict = None,
) -> str:
    """渲染 /现在什么课 的 HTML。"""
    status = period_info.get("status")
    
    if status == "weekend":
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>今天是周末</h1>
    <div class="subtitle">好好休息吧~</div>
  </div>
</div>
</body>
</html>"""

    if status == "after_school":
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>今日课程已结束</h1>
    <div class="subtitle">辛苦啦，明天见~</div>
  </div>
</div>
</body>
</html>"""
    
    if status == "before_school":
        next_p = period_info.get("next_period")
        time_to = period_info.get("time_to_next", "未知")
        
        if next_p == 0:
            next_label = "早读"
        elif next_p == 9:
            next_label = "晚自习"
        else:
            next_label = f"第{next_p}节"
        
        next_html = ""
        if next_course:
            next_p = period_info.get("next_period")
            if next_p == 0:
                next_period_label = "早读"
                badge_class = "early"
            elif next_p == 9:
                next_period_label = "晚自习"
                badge_class = "night"
            else:
                next_period_label = f"第{next_p}节"
                badge_class = ""
            name = next_course.get("name", "")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            next_html = f"""
            <div class="card">
              <div class="period-badge {badge_class}">{next_period_label}</div>
              <div class="course-info">
                <div class="course-name">{name}</div>
                <div class="course-meta">{f"地点: {location}" if location else ""} {f"老师: {teacher}" if teacher else ""}</div>
                <div class="course-meta" style="color: #80deea;">还有 {time_to} 开始</div>
              </div>
            </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>还没上课</h1>
    <div class="subtitle">还有 {time_to}</div>
  </div>
  {next_html}
</div>
</body>
</html>"""
    
    if status == "break":
        next_p = period_info.get("next_period")
        time_to = period_info.get("time_to_next", "未知")
        
        if next_p == 0:
            next_period_label = "早读"
            badge_class = "early"
        elif next_p == 9:
            next_period_label = "晚自习"
            badge_class = "night"
        else:
            next_period_label = f"第{next_p}节"
            badge_class = ""
        
        next_html = ""
        if next_course:
            name = next_course.get("name", "")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            next_html = f"""
            <div class="card">
              <div class="period-badge {badge_class}">{next_period_label}</div>
              <div class="course-info">
                <div class="course-name">{name}</div>
                <div class="course-meta">{f"地点: {location}" if location else ""} {f"老师: {teacher}" if teacher else ""}</div>
                <div class="course-meta" style="color: #80deea;">还有 {time_to}</div>
              </div>
            </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>课间休息</h1>
    <div class="subtitle">下一节还有 {time_to}</div>
  </div>
  {next_html}
</div>
</body>
</html>"""
    
    if status == "class":
        period = period_info.get("period")
        time_left = period_info.get("time_left", "未知")
        
        if period == 0:
            period_label = "早读"
            badge_class = "early"
        elif period == 9:
            period_label = "晚自习"
            badge_class = "night"
        else:
            period_label = f"第{period}节"
            badge_class = ""
        
        # 当前课程卡片（只在有课程时显示）
        current_html = ""
        if current_course:
            name = current_course.get("name", "")
            location = current_course.get("location", "")
            teacher = current_course.get("teacher", "")
            current_html = f"""
            <div class="card">
              <div class="period-badge {badge_class}">{period_label}</div>
              <div class="course-info">
                <div class="course-name">{name}</div>
                <div class="course-meta">{f"地点: {location}" if location else ""} {f"老师: {teacher}" if teacher else ""}</div>
              </div>
            </div>"""
        
        # 下一节课信息（只在有下节课时显示）
        next_html = ""
        if next_course:
            next_p = period_info.get("next_period")
            time_to = period_info.get("time_to_next", "")
            if next_p == 0:
                next_period_label = "早读"
                badge_c = "early"
            elif next_p == 9:
                next_period_label = "晚自习"
                badge_c = "night"
            else:
                next_period_label = f"第{next_p}节"
                badge_c = ""
            name = next_course.get("name", "")
            location = next_course.get("location", "")
            teacher = next_course.get("teacher", "")
            next_html = f"""
            <div class="card">
              <div class="period-badge {badge_c}">{next_period_label}</div>
              <div class="course-info">
                <div class="course-name">{name}</div>
                <div class="course-meta">{f"地点: {location}" if location else ""} {f"老师: {teacher}" if teacher else ""}</div>
                <div class="course-meta" style="color: #80deea;">{time_to} 后开始</div>
              </div>
            </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>当前课程</h1>
    <div class="subtitle">还剩 {time_left}</div>
  </div>
  {current_html}
  {next_html}
</div>
</body>
</html>"""
    
    return ""


def render_next_course_html(
    period_info: dict,
    next_course: dict = None,
    current_course: dict = None,
) -> str:
    """渲染 /等会什么课 的 HTML。专注显示下一节课。"""
    status = period_info.get("status")
    next_p = period_info.get("next_period")
    time_to = period_info.get("time_to_next", "未知")

    if next_p == 0:
        next_period_label = "早读"
        badge_class = "early"
    elif next_p == 9:
        next_period_label = "晚自习"
        badge_class = "night"
    else:
        next_period_label = f"第{next_p}节"
        badge_class = ""

    # 标题根据状态变化
    if status == "weekend":
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>今天是周末</h1>
    <div class="subtitle">好好休息吧~</div>
  </div>
</div>
</body>
</html>"""

    if status == "after_school":
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>今日课程已结束</h1>
    <div class="subtitle">辛苦啦，明天见~</div>
  </div>
</div>
</body>
</html>"""

    # 正在上课
    current_html = ""
    if status == "class" and current_course:
        curr_name = current_course.get("name", "")
        current_html = f'<div class="status-detail" style="margin-bottom: 16px;">正在上: {curr_name}</div>'

    # 下一节课卡片
    next_html = ""
    if next_course:
        name = next_course.get("name", "")
        location = next_course.get("location", "")
        teacher = next_course.get("teacher", "")
        next_html = f"""
        <div class="card">
          <div class="period-badge {badge_class}">{next_period_label}</div>
          <div class="course-info">
            <div class="course-name">{name}</div>
            <div class="course-meta">{f"地点: {location}" if location else ""} {f"老师: {teacher}" if teacher else ""}</div>
            <div class="course-meta" style="color: #80deea; font-size: 20px; font-weight: 600; margin-top: 8px;">
              还有 {time_to} 上课
            </div>
          </div>
        </div>"""
    else:
        next_html = f"""
        <div class="card">
          <div class="period-badge {badge_class}">{next_period_label}</div>
          <div class="course-info">
            <div class="course-name">暂无安排</div>
            <div class="course-meta" style="color: #80deea;">还有 {time_to} 开始</div>
          </div>
        </div>"""

    # 标题
    if status == "class":
        title = "下一节课"
        subtitle = f"还有 {time_to}"
    elif status == "break":
        title = "下一节课"
        subtitle = f"还有 {time_to}"
    else:  # before_school
        title = "下一节课"
        subtitle = f"还有 {time_to}"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
  </div>
  {current_html}
  {next_html}
</div>
</body>
</html>"""


def render_week_overview_html(
    week_info: dict,
    days_data: Dict[int, list],
    target_date: date = None,
) -> str:
    """渲染本周课表概览的 HTML。"""
    week_type = "单周" if week_info.get("is_odd") else "双周"
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    columns_html = ""
    for day in range(1, 6):
        courses = days_data.get(day, [])
        courses_sorted = sorted(courses, key=lambda c: min(c.get("periods", [99])))
        
        courses_html = ""
        for c in courses_sorted[:6]:  # 最多显示6门
            periods = c.get("periods", [])
            p = periods[0] if periods else 0
            if p == 0:
                p_label = "早"
            elif p == 9:
                p_label = "晚"
            else:
                p_label = str(p)
            name = c.get("name", "")[:6]  # 截断
            courses_html += f"""
            <div class="mini-course">
              <div class="name">{name}</div>
              <div class="period">第{p_label}节</div>
            </div>"""
        
        if not courses_sorted:
            courses_html = '<div class="mini-course"><div class="name">无课</div></div>'
        
        columns_html += f"""
        <div class="day-column">
          <div class="day-name">{day_names[day]}</div>
          {courses_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>本周课表</h1>
    <div class="info-bar">
      <span class="info-tag">第{week_info['current']}周</span>
      <span class="info-tag">{week_type}</span>
    </div>
  </div>
  <div class="week-grid">
    {columns_html}
  </div>
  <div class="footer">发送 /我的课表 查看完整课表</div>
</div>
</body>
</html>"""


def render_my_schedule_html(schedule: dict) -> str:
    """渲染完整课表的 HTML。"""
    courses = schedule.get("courses", [])
    semester_start = schedule.get("semester_start", "未知")
    total_weeks = schedule.get("total_weeks", 20)
    
    # 按天分组
    day_groups: Dict[int, list] = {}
    for c in courses:
        day = c.get("day", 0)
        if day not in day_groups:
            day_groups[day] = []
        day_groups[day].append(c)
    
    day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    all_days_html = ""
    for day in range(1, 8):
        if day not in day_groups:
            continue
        
        day_courses = sorted(day_groups[day], key=lambda c: min(c.get("periods", [99])))
        
        courses_html = ""
        for c in day_courses:
            periods = c.get("periods", [])
            p = periods[0] if periods else 0
            
            if p == 0:
                period_label = "早读"
                badge_class = "early"
            elif p == 9:
                period_label = "晚自习"
                badge_class = "night"
            else:
                period_label = f"第{p}节"
                badge_class = ""
            
            name = c.get("name", "")
            location = c.get("location", "")
            teacher = c.get("teacher", "")
            
            meta = []
            if location:
                meta.append(f"地点: {location}")
            if teacher:
                meta.append(f"老师: {teacher}")
            
            courses_html += f"""
            <div class="card">
              <div class="period-badge {badge_class}">{period_label}</div>
              <div class="course-info">
                <div class="course-name">{name}</div>
                <div class="course-meta">{' '.join(meta)}</div>
              </div>
            </div>"""
        
        all_days_html += f"""
        <div class="header" style="margin-top: 16px; padding: 16px;">
          <h1 style="font-size: 20px;">{day_names[day]}</h1>
        </div>
        {courses_html}"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>我的课表</h1>
    <div class="subtitle">学期: {semester_start} 起 · 共{total_weeks}周</div>
  </div>
  {all_days_html}
  <div class="footer">发送 /课程表帮助 查看更多命令</div>
</div>
</body>
</html>"""
