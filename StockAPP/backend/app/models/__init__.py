"""
数据模型
========
"""

from .requests import (
    BacktestParams,
    BacktestRequest,
    CompareRequest,
    OptimizeRequest,
    ETFDataRequest,
)
from .responses import (
    Metrics,
    EquityPoint,
    Trade,
    MonthlyReturn,
    BacktestResult,
    CompareResult,
    OptimizationResult,
    ETFInfo,
    ETFData,
    StockInfo,
    StrategyInfo,
    StrategyListItem,
    APIResponse,
    ErrorResponse,
)

__all__ = [
    "BacktestParams",
    "BacktestRequest",
    "CompareRequest",
    "OptimizeRequest",
    "ETFDataRequest",
    "Metrics",
    "EquityPoint",
    "Trade",
    "MonthlyReturn",
    "BacktestResult",
    "CompareResult",
    "OptimizationResult",
    "ETFInfo",
    "ETFData",
    "StockInfo",
    "StrategyInfo",
    "StrategyListItem",
    "APIResponse",
    "ErrorResponse",
]
