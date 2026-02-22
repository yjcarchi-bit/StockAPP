"""
全局设置模块
============
应用程序的全局配置管理

特性:
- 单例模式
- 配置持久化
- 环境变量支持
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class Settings:
    """
    全局设置
    
    Attributes:
        initial_capital: 初始资金
        commission_rate: 佣金费率
        stamp_duty: 印花税率
        min_commission: 最低佣金
        lot_size: 每手股数
        benchmark: 默认基准指数
        cache_expire_hours: 缓存过期时间（小时）
        theme: UI主题
        language: 语言
    """
    
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003
    stamp_duty: float = 0.001
    min_commission: float = 5.0
    lot_size: int = 100
    benchmark: str = "000300"
    cache_expire_hours: int = 24
    theme: str = "light"
    language: str = "zh_CN"
    
    _instance: Optional["Settings"] = field(default=None, repr=False)
    _config_file: str = field(default="", repr=False)
    
    def __post_init__(self):
        if not self._config_file:
            config_dir = Path.home() / ".stockapp"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_file = str(config_dir / "config.json")
    
    def save(self) -> None:
        """保存配置到文件"""
        config = asdict(self)
        config.pop("_instance", None)
        config.pop("_config_file", None)
        
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def load(self) -> None:
        """从文件加载配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                for key, value in config.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception:
                pass
    
    def reset(self) -> None:
        """重置为默认配置"""
        self.initial_capital = 100000.0
        self.commission_rate = 0.0003
        self.stamp_duty = 0.001
        self.min_commission = 5.0
        self.lot_size = 100
        self.benchmark = "000300"
        self.cache_expire_hours = 24
        self.theme = "light"
        self.language = "zh_CN"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "stamp_duty": self.stamp_duty,
            "min_commission": self.min_commission,
            "lot_size": self.lot_size,
            "benchmark": self.benchmark,
            "cache_expire_hours": self.cache_expire_hours,
            "theme": self.theme,
            "language": self.language,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """从字典创建"""
        return cls(**data)


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置实例（单例）"""
    global _settings_instance
    
    if _settings_instance is None:
        _settings_instance = Settings()
        _settings_instance.load()
    
    return _settings_instance
