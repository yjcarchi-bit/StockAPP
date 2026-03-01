"""
多因子策略模块
==============
综合多个因子进行选股择时的复合策略

包含:
- ETF轮动策略 (ETF Rotation)
- 三驾马车ETF轮动 (Three Horse ETF Rotation)
- 三驾马车ETF反弹 (Three Horse ETF Rebound)
- 三驾马车双ETF组合 (Three Horse Dual ETF)
- 三驾马车小市值 (Three Horse Small Cap)
- 三驾马车白马攻防 (Three Horse White Horse)
- 三驾马车总策略 (Three Horse Carriage)
"""

from .etf_rotation import ETFRotationStrategy
from .three_horse_etf_rotation import ThreeHorseETFRotationStrategy
from .three_horse_etf_rebound import ThreeHorseETFReboundStrategy
from .three_horse_dual_etf import ThreeHorseDualETFStrategy
from .three_horse_small_cap import ThreeHorseSmallCapStrategy
from .three_horse_white_horse import ThreeHorseWhiteHorseStrategy
from .three_horse_carriage import ThreeHorseCarriageStrategy

__all__ = [
    "ETFRotationStrategy",
    "ThreeHorseETFRotationStrategy",
    "ThreeHorseETFReboundStrategy",
    "ThreeHorseDualETFStrategy",
    "ThreeHorseSmallCapStrategy",
    "ThreeHorseWhiteHorseStrategy",
    "ThreeHorseCarriageStrategy",
]
