"""
策略模块
========
所有交易策略的统一入口

包含:
- ETF轮动策略 (ETF Rotation)
- 三驾马车ETF轮动策略 (Three Horse ETF Rotation)
- 三驾马车ETF反弹策略 (Three Horse ETF Rebound)
- 三驾马车双ETF组合策略 (Three Horse Dual ETF)
- 三驾马车小市值策略 (Three Horse Small Cap)
- 三驾马车白马攻防策略 (Three Horse White Horse)
- 三驾马车总策略 (Three Horse Carriage)
"""

from .multi_factor.etf_rotation import ETFRotationStrategy
from .multi_factor.three_horse_etf_rotation import ThreeHorseETFRotationStrategy
from .multi_factor.three_horse_etf_rebound import ThreeHorseETFReboundStrategy
from .multi_factor.three_horse_dual_etf import ThreeHorseDualETFStrategy
from .multi_factor.three_horse_small_cap import ThreeHorseSmallCapStrategy
from .multi_factor.three_horse_white_horse import ThreeHorseWhiteHorseStrategy
from .multi_factor.three_horse_carriage import ThreeHorseCarriageStrategy

__all__ = [
    "ETFRotationStrategy",
    "ThreeHorseETFRotationStrategy",
    "ThreeHorseETFReboundStrategy",
    "ThreeHorseDualETFStrategy",
    "ThreeHorseSmallCapStrategy",
    "ThreeHorseWhiteHorseStrategy",
    "ThreeHorseCarriageStrategy",
]
