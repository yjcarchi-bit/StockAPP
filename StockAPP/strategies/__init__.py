"""
策略模块
========
所有交易策略的统一入口

包含:
- ETF轮动策略 (ETF Rotation)
"""

from .multi_factor.etf_rotation import ETFRotationStrategy

__all__ = [
    "ETFRotationStrategy",
]
