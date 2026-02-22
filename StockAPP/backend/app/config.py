"""
配置管理
==========
"""

from typing import List


class Settings:
    """应用配置"""
    
    app_name: str = "StockAPP API"
    app_version: str = "2.0.0"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    debug: bool = False


settings = Settings()
