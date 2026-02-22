"""
响应模型
========
API 响应数据定义
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class Metrics(BaseModel):
    """回测指标"""
    total_return: float = Field(..., description="总收益率")
    annual_return: float = Field(..., description="年化收益率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    sortino_ratio: float = Field(0, description="索提诺比率")
    calmar_ratio: float = Field(0, description="卡玛比率")
    win_rate: float = Field(..., description="胜率")
    profit_factor: float = Field(0, description="盈亏比")
    total_trades: int = Field(0, description="交易次数")
    final_value: float = Field(..., description="最终资产")
    benchmark_return: float = Field(0, description="基准收益率")


class EquityPoint(BaseModel):
    """资金曲线点"""
    date: str
    value: float


class Trade(BaseModel):
    """交易记录"""
    timestamp: str
    code: str
    side: str
    price: float
    amount: int
    value: float


class MonthlyReturn(BaseModel):
    """月度收益"""
    year: int
    month: int
    return_rate: float


class BacktestResult(BaseModel):
    """回测结果"""
    result_id: str = Field(..., description="结果ID")
    strategy: str = Field(..., description="策略名称")
    metrics: Metrics = Field(..., description="回测指标")
    equity_curve: List[EquityPoint] = Field(default_factory=list, description="资金曲线")
    trades: List[Trade] = Field(default_factory=list, description="交易记录")
    monthly_returns: List[MonthlyReturn] = Field(default_factory=list, description="月度收益")


class CompareResult(BaseModel):
    """策略对比结果"""
    results: List[BacktestResult] = Field(..., description="各策略结果")
    best_return_strategy: str = Field(..., description="最高收益策略")
    best_sharpe_strategy: str = Field(..., description="最高夏普策略")
    min_drawdown_strategy: str = Field(..., description="最小回撤策略")


class OptimizationResult(BaseModel):
    """参数优化结果"""
    best_params: Dict[str, Any] = Field(..., description="最优参数")
    best_metrics: Metrics = Field(..., description="最优指标")
    all_results: List[Dict[str, Any]] = Field(default_factory=list, description="所有结果")
    optimization_time: float = Field(0, description="优化耗时")
    total_combinations: int = Field(0, description="总组合数")


class ETFInfo(BaseModel):
    """ETF信息"""
    code: str
    name: str
    type: str


class StockInfo(BaseModel):
    """股票信息"""
    code: str
    name: str
    market: str = ""
    industry: str = ""


class ETFData(BaseModel):
    """ETF数据"""
    code: str
    data: List[Dict[str, Any]]


class StrategyInfo(BaseModel):
    """策略信息"""
    name: str
    display_name: str
    category: str = "simple"
    type: str
    icon: str
    description: str
    logic: List[str]
    suitable: str
    risk: str
    params: Dict[str, Any]


class StrategyListItem(BaseModel):
    """策略列表项"""
    name: str
    display_name: str
    category: str = "simple"
    type: str
    description: str
    params: List[Dict[str, Any]]


class APIResponse(BaseModel):
    """通用API响应"""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None
