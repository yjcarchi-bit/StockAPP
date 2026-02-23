"""
多因子策略模块
==============
综合多个因子进行选股择时的复合策略

包含:
- ETF轮动策略 (ETF Rotation)
- 大市值低回撤策略 (Large Cap Low Drawdown)
"""

from .etf_rotation import ETFRotationStrategy
from .large_cap_low_drawdown import LargeCapLowDrawdownStrategy

__all__ = [
    "ETFRotationStrategy",
    "LargeCapLowDrawdownStrategy",
]
