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
- 大市值低回撤策略 (Large Cap Low Drawdown)
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
    LargeCapLowDrawdownStrategy,
)

__all__ = [
    "BollingerStrategy",
    "DualMAStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "GridTradingStrategy",
    "ETFRotationStrategy",
    "LargeCapLowDrawdownStrategy",
]
