"""课表数据管理模块."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from nonebot.log import logger

try:
    from nonebot import get_driver
except Exception:
    get_driver = None

try:
    from nonebot import require

    require("nonebot_plugin_localstore")
    import nonebot_plugin_localstore as localstore
except Exception:
    localstore = None


def _resolve_data_dir() -> Path:
    """Resolve the data directory without storing user data inside the package."""
    if get_driver is not None:
        try:
            config = get_driver().config
            configured = getattr(config, "class_schedule_data_dir", None)
            if configured:
                return Path(str(configured)).expanduser()
        except Exception:
            pass

    if localstore is not None:
        try:
            return localstore.get_data_dir("nonebot_plugin_class_schedule")
        except Exception:
            pass

    return Path.cwd() / "data" / "class_schedule"


class ScheduleManager:
    """管理用户课表数据和偏好设置"""
    
    def __init__(self):
        self.data_dir = _resolve_data_dir()
        self.schedule_dir = self.data_dir / "schedules"
        self.prefs_file = self.data_dir / "preferences.json"
        
        # 确保目录存在
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存
        self._schedule_cache: Dict[str, dict] = {}
        self._prefs_cache: Dict[str, dict] = {}
        
        # 加载偏好设置
        self._load_preferences()
    
    def _load_preferences(self):
        """加载用户偏好设置"""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, "r", encoding="utf-8") as f:
                    self._prefs_cache = json.load(f)
            except Exception as e:
                logger.error(f"加载偏好设置失败: {e}")
                self._prefs_cache = {}
        else:
            self._prefs_cache = {}
    
    def _save_preferences(self):
        """保存用户偏好设置"""
        try:
            with open(self.prefs_file, "w", encoding="utf-8") as f:
                json.dump(self._prefs_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存偏好设置失败: {e}")
    
    def _get_schedule_file(self, user_id: str) -> Path:
        """获取用户课表文件路径"""
        return self.schedule_dir / f"{user_id}.json"
    
    def get_schedule(self, user_id: str) -> Optional[dict]:
        """获取用户课表"""
        # 先检查缓存
        if user_id in self._schedule_cache:
            return self._schedule_cache[user_id]
        
        # 从文件加载
        schedule_file = self._get_schedule_file(user_id)
        if schedule_file.exists():
            try:
                with open(schedule_file, "r", encoding="utf-8") as f:
                    schedule = json.load(f)
                    self._schedule_cache[user_id] = schedule
                    return schedule
            except Exception as e:
                logger.error(f"加载课表失败 {user_id}: {e}")
                return None
        return None
    
    def save_schedule(self, user_id: str, schedule: dict):
        """保存用户课表"""
        schedule_file = self._get_schedule_file(user_id)
        try:
            with open(schedule_file, "w", encoding="utf-8") as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
            self._schedule_cache[user_id] = schedule
            logger.info(f"课表已保存: {user_id}")
        except Exception as e:
            logger.error(f"保存课表失败 {user_id}: {e}")
            raise
    
    def get_courses_for_day(self, user_id: str, day_index: int, week: int) -> List[dict]:
        """获取某天某周的课程列表"""
        schedule = self.get_schedule(user_id)
        if not schedule:
            return []
        
        courses = schedule.get("courses", [])
        day_courses = []
        
        for course in courses:
            # 检查课程是否在该天
            if course.get("day") == day_index:
                # 检查周次限制
                weeks = course.get("weeks", [])
                if not weeks or week in weeks:
                    day_courses.append(course)
        
        # 按节次排序
        day_courses.sort(key=lambda x: x.get("period", 0))
        return day_courses
    
    def get_user_style(self, user_id: str) -> str:
        """获取用户输出风格 (text/image)"""
        prefs = self._prefs_cache.get(user_id, {})
        return prefs.get("output_style", "text")
    
    def set_user_style(self, user_id: str, style: str):
        """设置用户输出风格"""
        if user_id not in self._prefs_cache:
            self._prefs_cache[user_id] = {}
        self._prefs_cache[user_id]["output_style"] = style
        self._save_preferences()
    
    def get_reminder_settings(self, user_id: str) -> dict:
        """获取用户提醒设置"""
        prefs = self._prefs_cache.get(user_id, {})
        return prefs.get("reminder", {"enabled": False, "minutes_before": 5})
    
    def set_reminder_settings(self, user_id: str, enabled: bool = None, minutes_before: int = None):
        """设置用户提醒设置"""
        if user_id not in self._prefs_cache:
            self._prefs_cache[user_id] = {}
        
        if "reminder" not in self._prefs_cache[user_id]:
            self._prefs_cache[user_id]["reminder"] = {"enabled": False, "minutes_before": 5}
        
        if enabled is not None:
            self._prefs_cache[user_id]["reminder"]["enabled"] = enabled
        if minutes_before is not None:
            self._prefs_cache[user_id]["reminder"]["minutes_before"] = minutes_before
        
        self._save_preferences()
    
    def get_holiday_reminder(self, user_id: str) -> bool:
        """获取用户假期提醒设置"""
        prefs = self._prefs_cache.get(user_id, {})
        return prefs.get("holiday_reminder", False)
    
    def set_holiday_reminder(self, user_id: str, enabled: bool):
        """设置用户假期提醒"""
        if user_id not in self._prefs_cache:
            self._prefs_cache[user_id] = {}
        self._prefs_cache[user_id]["holiday_reminder"] = enabled
        self._save_preferences()
    
    def get_custom_schedule(self, user_id: str) -> Optional[dict]:
        """获取用户自定义作息表"""
        prefs = self._prefs_cache.get(user_id, {})
        return prefs.get("custom_schedule")
    
    def search_courses(self, user_id: str, keyword: str) -> List[dict]:
        """搜索课程"""
        schedule = self.get_schedule(user_id)
        if not schedule:
            return []
        
        courses = schedule.get("courses", [])
        results = []
        keyword_lower = keyword.lower()
        
        for course in courses:
            name = course.get("name", "").lower()
            teacher = course.get("teacher", "").lower()
            if keyword_lower in name or keyword_lower in teacher:
                results.append(course)
        
        return results
