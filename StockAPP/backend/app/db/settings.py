"""Database settings for MySQL-backed market storage."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_project_env()


@dataclass
class DBSettings:
    storage_backend: str = os.getenv("DATA_STORAGE_BACKEND", "mysql").strip().lower()
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_db: str = os.getenv("MYSQL_DATABASE", "stockapp")
    mysql_user: str = os.getenv("MYSQL_USER", "stockapp")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "stockapp")
    mysql_charset: str = os.getenv("MYSQL_CHARSET", "utf8mb4")
    mysql_pool_size: int = int(os.getenv("MYSQL_POOL_SIZE", "10"))
    mysql_max_overflow: int = int(os.getenv("MYSQL_MAX_OVERFLOW", "20"))
    mysql_pool_recycle: int = int(os.getenv("MYSQL_POOL_RECYCLE", "1800"))

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@"
            f"{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset={self.mysql_charset}"
        )


settings = DBSettings()


def is_mysql_enabled() -> bool:
    return settings.storage_backend in {"dual", "mysql"}
