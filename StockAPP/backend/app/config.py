"""
配置管理
==========
"""

import os
from typing import List


class Settings:
    """应用配置"""
    
    app_name: str = "StockAPP API"
    app_version: str = "2.0.0"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1:5173",
        "http://127.0.0.1",
    ]
    
    debug: bool = False
    tushare_timeout: int = int(os.getenv("TUSHARE_TIMEOUT", "30"))


settings = Settings()
