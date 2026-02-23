"""
多因子策略模块
==============
综合多个因子进行选股择时的复合策略

包含:
- ETF轮动策略 (ETF Rotation)
- 多ETF轮动策略 (Multi ETF Rotation)
- 偷鸡摸狗策略 (Steal Dog)
- 搅屎棍策略 (FMS)
- 大市值低回撤策略 (Large Cap Low Drawdown)
- 多策略组合策略 (Multi Strategy Portfolio)
"""

from .etf_rotation import ETFRotationStrategy
from .multi_etf_rotation import MultiETFRotationStrategy
from .steal_dog_strategy import StealDogStrategy
from .fms_strategy import FMSStrategy
from .large_cap_low_drawdown import LargeCapLowDrawdownStrategy
from .multi_strategy_portfolio import MultiStrategyPortfolio

__all__ = [
    "ETFRotationStrategy",
    "MultiETFRotationStrategy",
    "StealDogStrategy",
    "FMSStrategy",
    "LargeCapLowDrawdownStrategy",
    "MultiStrategyPortfolio",
]
