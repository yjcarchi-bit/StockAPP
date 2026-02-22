"""
请求模型
========
API 请求参数定义
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import date


class BacktestParams(BaseModel):
    """回测参数"""
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    initial_capital: float = Field(100000, description="初始资金")
    commission_rate: float = Field(0.0003, description="佣金费率")
    stamp_duty: float = Field(0.001, description="印花税率")
    slippage: float = Field(0.0, description="滑点")


class BacktestRequest(BaseModel):
    """回测请求"""
    strategy: str = Field(..., description="策略名称")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    backtest_params: BacktestParams = Field(..., description="回测参数")
    etf_codes: List[str] = Field(..., description="ETF代码列表")


class CompareRequest(BaseModel):
    """策略对比请求"""
    strategies: List[str] = Field(..., description="策略列表", min_length=2, max_length=3)
    strategy_params_list: List[Dict[str, Any]] = Field(default_factory=list, description="各策略参数")
    backtest_params: BacktestParams = Field(..., description="回测参数")
    etf_codes: List[str] = Field(..., description="ETF代码列表")


class OptimizeRequest(BaseModel):
    """参数优化请求"""
    strategy: str = Field(..., description="策略名称")
    param_grid: Dict[str, List[Any]] = Field(..., description="参数网格")
    fixed_params: Dict[str, Any] = Field(default_factory=dict, description="固定参数")
    backtest_params: BacktestParams = Field(..., description="回测参数")
    etf_codes: List[str] = Field(..., description="ETF代码列表")
    optimization_metric: str = Field("sharpe_ratio", description="优化目标")
    method: Literal["grid", "random"] = Field("grid", description="优化方法")
    n_iter: int = Field(50, description="随机搜索迭代次数")


class ETFDataRequest(BaseModel):
    """ETF数据请求"""
    code: str = Field(..., description="ETF代码")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
