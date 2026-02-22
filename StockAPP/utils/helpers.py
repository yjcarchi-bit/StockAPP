"""
辅助函数模块
============
常用的辅助工具函数
"""

from datetime import datetime, timedelta
from typing import Union, Optional
import pandas as pd


def format_number(value: float, decimal: int = 2) -> str:
    """
    格式化数字
    
    Args:
        value: 数值
        decimal: 小数位数
        
    Returns:
        格式化后的字符串
    """
    if abs(value) >= 1e8:
        return f"{value/1e8:.{decimal}f}亿"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.{decimal}f}万"
    else:
        return f"{value:,.{decimal}f}"


def format_percent(value: float, decimal: int = 2) -> str:
    """
    格式化百分比
    
    Args:
        value: 数值（已经是百分比形式，如15.5表示15.5%）
        decimal: 小数位数
        
    Returns:
        格式化后的字符串
    """
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimal}f}%"


def format_date(date: Union[str, datetime], fmt: str = "%Y-%m-%d") -> str:
    """
    格式化日期
    
    Args:
        date: 日期
        fmt: 格式
        
    Returns:
        格式化后的字符串
    """
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return date
    
    return date.strftime(fmt)


def calculate_trading_days(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime]
) -> int:
    """
    计算交易日数量（粗略估计）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        交易日数量
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    days = (end_date - start_date).days
    
    trading_days = int(days * 5 / 7)
    
    return max(trading_days, 1)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """
    安全除法
    
    Args:
        a: 被除数
        b: 除数
        default: 除数为0时的默认值
        
    Returns:
        计算结果
    """
    if b == 0:
        return default
    return a / b


def get_risk_level(value: float, thresholds: dict) -> str:
    """
    根据阈值获取风险等级
    
    Args:
        value: 数值
        thresholds: 阈值字典，如 {"low": -5, "medium": -10, "high": -20}
        
    Returns:
        风险等级
    """
    if value >= thresholds.get("low", -5):
        return "低"
    elif value >= thresholds.get("medium", -10):
        return "中"
    elif value >= thresholds.get("high", -20):
        return "高"
    else:
        return "极高"


def get_performance_level(value: float, thresholds: dict) -> str:
    """
    根据阈值获取表现等级
    
    Args:
        value: 数值
        thresholds: 阈值字典
        
    Returns:
        表现等级
    """
    if value >= thresholds.get("excellent", 20):
        return "优秀"
    elif value >= thresholds.get("good", 10):
        return "良好"
    elif value >= thresholds.get("average", 0):
        return "一般"
    else:
        return "较差"


def generate_date_range(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    freq: str = "D"
) -> list:
    """
    生成日期范围
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        freq: 频率 (D=日, W=周, M=月, B=工作日)
        
    Returns:
        日期列表
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    return dates.tolist()
