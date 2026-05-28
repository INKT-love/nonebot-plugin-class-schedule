"""课表数据管理模块"""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from nonebot.log import logger


class ScheduleManager:
    """管理用户课表数据和偏好设置"""
    
    def __init__(self):
        self.data_dir = Path(os.environ.get("CLASS_SCHEDULE_DATA_DIR", "./data/class_schedule"))
        self.schedule_dir = self.data_dir / "schedules"
        self.prefs_file = self.data_dir / "preferences.json"
        
        # 确保目录存在
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存
        self._schedule_cache: Dict[str, dict] = {}
        self._prefs_cache: Dict[str, dict] = {}
        
        # 加载偏好
        self._load_preferences()
