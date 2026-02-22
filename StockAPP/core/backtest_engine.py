"""
回测引擎模块
============
事件驱动的回测引擎，支持多种策略

特性:
- 事件驱动回测
- 完整的交易费用计算
- 回测结果分析
- 基准对比
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Type
import pandas as pd
import numpy as np

from .data_source import DataSource
from .strategy_base import StrategyBase, BarData
from .portfolio import Portfolio
from .indicators import Indicators


@dataclass
class BacktestConfig:
    """
    回测配置
    
    Attributes:
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        commission_rate: 佣金费率
        stamp_duty: 印花税率
        min_commission: 最低佣金
        lot_size: 每手股数
        benchmark: 基准指数代码
        slippage: 滑点
    """
    
    start_date: Union[str, datetime]
    end_date: Union[str, datetime]
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003
    stamp_duty: float = 0.001
    min_commission: float = 5.0
    lot_size: int = 100
    benchmark: str = "000300"
    slippage: float = 0.0
    
    def __post_init__(self):
        if isinstance(self.start_date, str):
            self.start_date = datetime.strptime(self.start_date, "%Y-%m-%d")
        if isinstance(self.end_date, str):
            self.end_date = datetime.strptime(self.end_date, "%Y-%m-%d")


@dataclass
class BacktestResult:
    """
    回测结果
    
    Attributes:
        config: 回测配置
        daily_values: 每日净值数据
        trade_records: 交易记录
        metrics: 回测指标
    """
    
    config: BacktestConfig
    daily_values: pd.DataFrame = field(default_factory=pd.DataFrame)
    trade_records: pd.DataFrame = field(default_factory=pd.DataFrame)
    benchmark_values: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return self.metrics.get("total_return", 0.0)
    
    @property
    def annual_return(self) -> float:
        """年化收益率"""
        return self.metrics.get("annual_return", 0.0)
    
    @property
    def max_drawdown(self) -> float:
        """最大回撤"""
        return self.metrics.get("max_drawdown", 0.0)
    
    @property
    def sharpe_ratio(self) -> float:
        """夏普比率"""
        return self.metrics.get("sharpe_ratio", 0.0)
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """计算回测指标"""
        if self.daily_values.empty:
            return {}
        
        df = self.daily_values.copy()
        
        if "date" in df.columns:
            df = df.set_index("date") if not isinstance(df.index, pd.DatetimeIndex) else df
        
        values = df["total_value"]
        
        total_return = (values.iloc[-1] / values.iloc[0] - 1) * 100
        
        days = (df.index[-1] - df.index[0]).days
        years = max(days / 365, 1/252)
        annual_return = ((values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1) * 100
        
        daily_returns = values.pct_change().dropna()
        annual_volatility = daily_returns.std() * np.sqrt(252) * 100
        
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate * 100) / annual_volatility if annual_volatility > 0 else 0
        
        cummax = values.expanding().max()
        drawdown = (values - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        max_dd_duration = 0
        current_dd_duration = 0
        for dd in drawdown:
            if dd < 0:
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
            else:
                current_dd_duration = 0
        
        trades = self.trade_records
        if not trades.empty:
            buy_trades = trades[trades["side"] == "buy"]
            sell_trades = trades[trades["side"] == "sell"]
            
            total_trades = len(sell_trades)
            
            if total_trades > 0:
                win_trades = 0
                total_profit = 0
                total_loss = 0
                
                for _, trade in sell_trades.iterrows():
                    code = trade["code"]
                    sell_price = trade["price"]
                    sell_amount = trade["amount"]
                    
                    code_buys = buy_trades[buy_trades["code"] == code]
                    if not code_buys.empty:
                        avg_buy_price = (code_buys["price"] * code_buys["amount"]).sum() / code_buys["amount"].sum()
                        profit = (sell_price - avg_buy_price) * sell_amount
                        
                        if profit > 0:
                            win_trades += 1
                            total_profit += profit
                        else:
                            total_loss += abs(profit)
                
                win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
                profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            else:
                win_rate = 0
                profit_factor = 0
        else:
            total_trades = 0
            win_rate = 0
            profit_factor = 0
        
        benchmark_return = 0.0
        if not self.benchmark_values.empty:
            bench = self.benchmark_values
            if "close" in bench.columns:
                benchmark_return = (bench["close"].iloc[-1] / bench["close"].iloc[0] - 1) * 100
        
        excess_return = total_return - benchmark_return
        
        sortino_ratio = 0.0
        if len(daily_returns) > 0:
            downside_returns = daily_returns[daily_returns < 0]
            downside_std = downside_returns.std() * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0
            sortino_ratio = (annual_return - risk_free_rate * 100) / downside_std if downside_std > 0 else 0
        
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        self.metrics = {
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "annual_volatility": round(annual_volatility, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "calmar_ratio": round(calmar_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_dd_duration": max_dd_duration,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "benchmark_return": round(benchmark_return, 2),
            "excess_return": round(excess_return, 2),
            "initial_capital": self.config.initial_capital,
            "final_value": round(values.iloc[-1], 2),
        }
        
        return self.metrics
    
    def get_summary(self) -> str:
        """获取结果摘要"""
        if not self.metrics:
            self.calculate_metrics()
        
        m = self.metrics
        
        summary = f"""
回测结果摘要
{'='*50}
回测区间: {self.config.start_date.strftime('%Y-%m-%d')} ~ {self.config.end_date.strftime('%Y-%m-%d')}
初始资金: {m['initial_capital']:,.2f}
最终资产: {m['final_value']:,.2f}

收益指标:
  总收益率:   {m['total_return']:.2f}%
  年化收益率: {m['annual_return']:.2f}%
  基准收益率: {m['benchmark_return']:.2f}%
  超额收益:   {m['excess_return']:.2f}%

风险指标:
  年化波动率: {m['annual_volatility']:.2f}%
  最大回撤:   {m['max_drawdown']:.2f}%

风险调整收益:
  夏普比率:   {m['sharpe_ratio']:.2f}
  索提诺比率: {m['sortino_ratio']:.2f}
  卡玛比率:   {m['calmar_ratio']:.2f}

交易统计:
  交易次数:   {m['total_trades']}
  胜率:       {m['win_rate']:.2f}%
  盈亏比:     {m['profit_factor']:.2f}
{'='*50}
"""
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "config": {
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "initial_capital": self.config.initial_capital,
                "benchmark": self.config.benchmark,
            },
            "metrics": self.metrics,
            "daily_values": self.daily_values.to_dict() if not self.daily_values.empty else {},
            "trade_records": self.trade_records.to_dict() if not self.trade_records.empty else {},
        }


class BacktestEngine:
    """
    回测引擎
    
    事件驱动的回测引擎，支持多种策略
    
    Example:
        >>> config = BacktestConfig(
        ...     start_date="2022-01-01",
        ...     end_date="2024-01-01",
        ...     initial_capital=100000
        ... )
        >>> engine = BacktestEngine(config)
        >>> engine.add_data("510300", etf_data)
        >>> engine.add_strategy(MyStrategy())
        >>> result = engine.run()
    """
    
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        data_source: Optional[DataSource] = None
    ):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
            data_source: 数据源
        """
        self.config = config
        self.data_source = data_source or DataSource()
        
        self._data: Dict[str, pd.DataFrame] = {}
        self._strategies: List[StrategyBase] = []
        self._portfolio: Optional[Portfolio] = None
        self._benchmark_data: Optional[pd.DataFrame] = None
    
    def set_config(self, config: BacktestConfig) -> None:
        """设置回测配置"""
        self.config = config
    
    def add_data(self, code: str, data: pd.DataFrame) -> None:
        """
        添加数据
        
        Args:
            code: 证券代码
            data: 历史数据DataFrame
        """
        if "date" in data.columns and not pd.api.types.is_datetime64_any_dtype(data["date"]):
            data["date"] = pd.to_datetime(data["date"])
        
        data = data.sort_values("date").reset_index(drop=True)
        self._data[code] = data
    
    def add_strategy(self, strategy: StrategyBase) -> None:
        """
        添加策略
        
        Args:
            strategy: 策略实例
        """
        self._strategies.append(strategy)
    
    def load_data(
        self,
        codes: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        data_type: str = "etf",
        show_progress: bool = True
    ) -> None:
        """
        加载数据
        
        Args:
            codes: 证券代码列表
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
            show_progress: 是否显示进度
        """
        for i, code in enumerate(codes):
            if show_progress:
                print(f"加载数据 [{i+1}/{len(codes)}]: {code}")
            
            df = self.data_source.get_history(code, start_date, end_date, data_type)
            if df is not None:
                self.add_data(code, df)
    
    def load_benchmark(self) -> None:
        """加载基准数据"""
        if self.config is None or not self.config.benchmark:
            return
        
        benchmark_code = self.config.benchmark
        
        if benchmark_code in self._data:
            self._benchmark_data = self._data[benchmark_code]
            return
        
        df = self.data_source.get_index_history(
            benchmark_code,
            self.config.start_date,
            self.config.end_date
        )
        
        if df is not None:
            self._benchmark_data = df
    
    def _get_trade_dates(self) -> List[datetime]:
        """获取交易日列表"""
        if not self._data:
            return []
        
        all_dates = set()
        for df in self._data.values():
            if "date" in df.columns:
                dates = df["date"].tolist()
                all_dates.update(dates)
        
        start = self.config.start_date
        end = self.config.end_date
        
        trade_dates = sorted([d for d in all_dates if start <= d <= end])
        
        return trade_dates
    
    def _get_bar(self, code: str, date: datetime) -> Optional[BarData]:
        """获取指定日期的K线数据"""
        df = self._data.get(code)
        
        if df is None or df.empty:
            return None
        
        if "date" in df.columns:
            mask = df["date"] == date
            if not mask.any():
                return None
            
            row = df[mask].iloc[0]
            return BarData.from_series(code, row)
        
        return None
    
    def run(self, show_progress: bool = True) -> BacktestResult:
        """
        运行回测
        
        Args:
            show_progress: 是否显示进度
            
        Returns:
            回测结果
        """
        if self.config is None:
            raise ValueError("请先设置回测配置")
        
        if not self._strategies:
            raise ValueError("请先添加策略")
        
        if not self._data:
            raise ValueError("请先添加数据")
        
        self.load_benchmark()
        
        self._portfolio = Portfolio(
            initial_capital=self.config.initial_capital,
            commission_rate=self.config.commission_rate,
            stamp_duty=self.config.stamp_duty,
            min_commission=self.config.min_commission,
            lot_size=self.config.lot_size,
        )
        
        strategy = self._strategies[0]
        strategy.set_portfolio(self._portfolio)
        strategy.set_data(self._data)
        strategy.initialize()
        strategy.on_start()
        
        trade_dates = self._get_trade_dates()
        total_days = len(trade_dates)
        
        if show_progress:
            print(f"开始回测，共 {total_days} 个交易日")
        
        for i, trade_date in enumerate(trade_dates):
            if show_progress and i % 50 == 0:
                progress = (i + 1) / total_days * 100
                print(f"回测进度: {progress:.1f}% ({i+1}/{total_days})")
            
            strategy.set_current_date(trade_date)
            
            prices = {}
            for code in self._data.keys():
                bar = self._get_bar(code, trade_date)
                if bar is not None:
                    prices[code] = bar.close
                    strategy.on_bar(bar)
            
            self._portfolio.record_daily_value(trade_date, prices)
        
        strategy.on_end()
        
        result = BacktestResult(config=self.config)
        result.daily_values = self._portfolio.get_daily_values_df()
        result.trade_records = self._portfolio.get_trade_records()
        
        if self._benchmark_data is not None:
            bench_df = self._benchmark_data.copy()
            if "date" in bench_df.columns:
                bench_df = bench_df[
                    (bench_df["date"] >= self.config.start_date) &
                    (bench_df["date"] <= self.config.end_date)
                ]
            result.benchmark_values = bench_df
        
        result.calculate_metrics()
        
        if show_progress:
            print(result.get_summary())
        
        return result
    
    def reset(self) -> None:
        """重置引擎状态"""
        self._data.clear()
        self._strategies.clear()
        self._portfolio = None
        self._benchmark_data = None
