"""
策略模块
========
内置策略实现

目录结构:
- simple/: 简单策略（单因子）
- multi_factor/: 多因子策略（复合策略）

简单策略:
- 布林带策略 (Bollinger)
- 双均线策略 (Dual MA)
- RSI策略
- MACD策略
- 网格交易策略 (Grid Trading)

多因子策略:
- ETF轮动策略 (ETF Rotation)
- 多ETF轮动策略 (Multi ETF Rotation)
- 偷鸡摸狗策略 (Steal Dog)
- 搅屎棍策略 (FMS)
- 大市值低回撤策略 (Large Cap Low Drawdown)
- 多策略组合策略 (Multi Strategy Portfolio)
"""

from .simple import (
    BollingerStrategy,
    DualMAStrategy,
    RSIStrategy,
    MACDStrategy,
    GridTradingStrategy,
)

from .multi_factor import (
    ETFRotationStrategy,
    MultiETFRotationStrategy,
    StealDogStrategy,
    FMSStrategy,
    LargeCapLowDrawdownStrategy,
    MultiStrategyPortfolio,
)

__all__ = [
    "BollingerStrategy",
    "DualMAStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "GridTradingStrategy",
    "ETFRotationStrategy",
    "MultiETFRotationStrategy",
    "StealDogStrategy",
    "FMSStrategy",
    "LargeCapLowDrawdownStrategy",
    "MultiStrategyPortfolio",
]
