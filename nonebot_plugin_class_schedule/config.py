"""Plugin configuration."""

from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    """Configuration for nonebot-plugin-class-schedule."""

    class_schedule_data_dir: str | Path | None = None

