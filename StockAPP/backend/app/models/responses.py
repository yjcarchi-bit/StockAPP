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


class PositionItem(BaseModel):
    """持仓项"""
    code: str = Field(..., description="证券代码")
    name: str = Field("", description="证券名称")
    shares: int = Field(..., description="持仓数量")
    price: float = Field(..., description="收盘价/结算价")
    market_value: float = Field(..., description="市值/价值")
    profit: float = Field(0, description="盈亏/逐笔浮盈")
    daily_profit: float = Field(0, description="当日盈亏")
    profit_pct: float = Field(0, description="盈亏占比")


class DailyPosition(BaseModel):
    """每日持仓"""
    date: str = Field(..., description="日期")
    positions: List[PositionItem] = Field(default_factory=list, description="持仓列表")
    cash: float = Field(0, description="现金")
    total_value: float = Field(0, description="总资产")
    total_profit: float = Field(0, description="总盈亏")
    total_daily_profit: float = Field(0, description="当日总盈亏")


class BacktestResult(BaseModel):
    """回测结果"""
    result_id: str = Field(..., description="结果ID")
    strategy: str = Field(..., description="策略名称")
    metrics: Metrics = Field(..., description="回测指标")
    equity_curve: List[EquityPoint] = Field(default_factory=list, description="资金曲线")
    trades: List[Trade] = Field(default_factory=list, description="交易记录")
    monthly_returns: List[MonthlyReturn] = Field(default_factory=list, description="月度收益")
    daily_positions: List[DailyPosition] = Field(default_factory=list, description="每日持仓")


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
    name: str = ""
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
    params: List[Dict[str, Any]]


class StrategyListItem(BaseModel):
    """策略列表项"""
    name: str
    display_name: str
    category: str = "simple"
    type: str
    description: str
    params: List[Dict[str, Any]]


class MacroAPIInfo(BaseModel):
    """宏观接口信息"""

    api_name: str = Field(..., description="接口名（用于请求 /api/macro/{api_name}）")
    name_zh: str = Field(..., description="接口中文名称")
    granularity: str = Field(..., description="时间粒度：date | month | quarter")
    default_start: str = Field(..., description="默认起始时间（随粒度变化）")
    default_end: str = Field(..., description="默认结束时间（随粒度变化）")


class MacroDataResponse(BaseModel):
    """宏观接口查询结果"""

    api_name: str = Field(..., description="接口名")
    name_zh: str = Field(..., description="接口中文名称")
    granularity: str = Field(..., description="时间粒度：date | month | quarter")
    params: Dict[str, str] = Field(default_factory=dict, description="实际生效的查询参数")
    range_start: str = Field(..., description="标准化后的起始 key")
    range_end: str = Field(..., description="标准化后的结束 key")
    source: str = Field(..., description="数据来源：tushare 或 mysql_cache")
    fetched_count: int = Field(0, description="本次从 Tushare 拉取条数")
    stored_count: int = Field(0, description="本次写入 MySQL 的条数")
    returned_count: int = Field(0, description="本次接口返回条数")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="数据明细（行字典）")


class FinancialAPIInfo(BaseModel):
    """财务接口信息"""

    api_name: str = Field(..., description="接口名（用于请求 /api/financial/{api_name}）")
    name_zh: str = Field(..., description="接口中文名称")
    mode: str = Field(..., description="参数模式：standard_range/disclosure_range/period_only/dividend")
    default_start: str = Field(..., description="默认起始时间（YYYYMMDD）")
    default_end: str = Field(..., description="默认结束时间（YYYYMMDD）")


class FinancialDataResponse(BaseModel):
    """财务接口查询结果"""

    api_name: str = Field(..., description="接口名")
    name_zh: str = Field(..., description="接口中文名称")
    mode: str = Field(..., description="参数模式")
    ts_code: str = Field(..., description="查询证券代码")
    params: Dict[str, str] = Field(default_factory=dict, description="实际生效的查询参数")
    range_start: str = Field(..., description="标准化后的起始 key")
    range_end: str = Field(..., description="标准化后的结束 key")
    source: str = Field(..., description="数据来源：tushare 或 mysql_cache")
    fetched_count: int = Field(0, description="本次从 Tushare 拉取条数")
    stored_count: int = Field(0, description="本次写入 MySQL 的条数")
    returned_count: int = Field(0, description="本次接口返回条数")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="数据明细（行字典）")


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
