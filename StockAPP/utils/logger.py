"""
日志模块
========
统一的日志管理

特性:
- 控制台输出
- 文件输出
- 日志级别控制
"""

import os
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path


class Logger:
    """
    简单日志类
    
    Example:
        >>> logger = get_logger("myapp")
        >>> logger.info("这是一条信息")
        >>> logger.error("这是一条错误")
    """
    
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    
    def __init__(
        self,
        name: str = "StockAPP",
        level: str = "INFO",
        log_file: Optional[str] = None
    ):
        self.name = name
        self.level = self.LEVELS.get(level.upper(), 20)
        self.log_file = log_file
        
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
    
    def _log(self, level: str, message: str) -> None:
        """内部日志方法"""
        level_num = self.LEVELS.get(level, 20)
        
        if level_num < self.level:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] [{self.name}] {message}"
        
        print(log_line)
        
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_line + "\n")
            except Exception:
                pass
    
    def debug(self, message: str) -> None:
        """调试信息"""
        self._log("DEBUG", message)
    
    def info(self, message: str) -> None:
        """一般信息"""
        self._log("INFO", message)
    
    def warning(self, message: str) -> None:
        """警告信息"""
        self._log("WARNING", message)
    
    def error(self, message: str) -> None:
        """错误信息"""
        self._log("ERROR", message)
    
    def critical(self, message: str) -> None:
        """严重错误"""
        self._log("CRITICAL", message)


_loggers = {}


def get_logger(name: str = "StockAPP") -> Logger:
    """
    获取日志实例
    
    Args:
        name: 日志名称
        
    Returns:
        Logger实例
    """
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name]


def setup_logger(
    name: str = "StockAPP",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> Logger:
    """
    设置日志
    
    Args:
        name: 日志名称
        level: 日志级别
        log_file: 日志文件路径
        
    Returns:
        Logger实例
    """
    logger = Logger(name, level, log_file)
    _loggers[name] = logger
    return logger
