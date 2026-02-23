"""
简单策略模块
============
基于单一因子信号的交易策略

包含:
- 布林带策略 (Bollinger)
- 双均线策略 (Dual MA)
- RSI策略
- MACD策略
- 网格交易策略 (Grid Trading)
"""

from .bollinger_strategy import BollingerStrategy
from .dual_ma import DualMAStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .grid_strategy import GridTradingStrategy

__all__ = [
    "BollingerStrategy",
    "DualMAStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "GridTradingStrategy",
]
