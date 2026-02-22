"""
核心模块
========
包含数据源、回测引擎、策略基类、指标计算等核心组件
"""

from .data_source import DataSource
from .backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from .strategy_base import StrategyBase, BarData
from .indicators import Indicators
from .portfolio import Portfolio, Position
from .order import Order, OrderType, OrderStatus
from .optimizer import ParameterOptimizer, OptimizationResult, get_strategy_param_grid

__all__ = [
    "DataSource",
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "StrategyBase",
    "BarData",
    "Indicators",
    "Portfolio",
    "Position",
    "Order",
    "OrderType",
    "OrderStatus",
    "ParameterOptimizer",
    "OptimizationResult",
    "get_strategy_param_grid",
]
