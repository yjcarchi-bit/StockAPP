"""
策略模块
========
内置策略实现

包含:
- ETF轮动策略
- 双均线策略
- RSI策略
- MACD策略
- 布林带策略
- 网格交易策略
- 搅屎棍策略 (FMS)
- 偷鸡摸狗策略
- 多ETF轮动策略
- 多策略组合策略
- 自定义策略模板
"""

from .etf_rotation import ETFRotationStrategy
from .dual_ma import DualMAStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .bollinger_strategy import BollingerStrategy
from .grid_strategy import GridTradingStrategy
from .fms_strategy import FMSStrategy
from .steal_dog_strategy import StealDogStrategy
from .multi_etf_rotation import MultiETFRotationStrategy
from .multi_strategy_portfolio import MultiStrategyPortfolio

__all__ = [
    "ETFRotationStrategy",
    "DualMAStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerStrategy",
    "GridTradingStrategy",
    "FMSStrategy",
    "StealDogStrategy",
    "MultiETFRotationStrategy",
    "MultiStrategyPortfolio",
]
