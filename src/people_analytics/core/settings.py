from __future__ import annotations

import os
import socket
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "dev"
    database_url: str = "sqlite:///./var/people_analytics.db"
    video_root: str = "./var/people_analytics/videos"
    config_dir: str = "./config"
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"
    job_poll_interval: int = 5
    job_lock_timeout: int = 300
    worker_id: str = ""

    def resolved_worker_id(self) -> str:
        if self.worker_id:
            return self.worker_id
        return f"{socket.gethostname()}-{os.getpid()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.worker_id = settings.resolved_worker_id()
    settings.video_root = str(Path(settings.video_root))
    settings.config_dir = str(Path(settings.config_dir))
    return settings
