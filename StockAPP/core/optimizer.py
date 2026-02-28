"""
策略参数优化模块
================
支持网格搜索、随机搜索等参数优化方法

特性:
- 网格搜索参数优化
- 多目标优化支持
- 优化结果可视化
- 并行计算支持
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Type, Callable, Tuple
from itertools import product
import pandas as pd
import numpy as np
import time

from .backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from .strategy_base import StrategyBase
from .data_source import DataSource


@dataclass
class OptimizationResult:
    """
    优化结果
    
    Attributes:
        best_params: 最优参数
        best_metrics: 最优指标
        all_results: 所有结果
        optimization_time: 优化耗时
    """
    
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_metrics: Dict[str, float] = field(default_factory=dict)
    all_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    optimization_time: float = 0.0
    total_combinations: int = 0
    
    def get_top_n(self, n: int = 10, metric: str = "total_return") -> pd.DataFrame:
        """获取排名前N的结果"""
        if self.all_results.empty:
            return pd.DataFrame()
        
        df = self.all_results.sort_values(metric, ascending=False)
        return df.head(n)
    
    def get_summary(self) -> str:
        """获取优化摘要"""
        summary = f"""
参数优化结果
{'='*50}
总组合数: {self.total_combinations}
优化耗时: {self.optimization_time:.2f} 秒

最优参数:
"""
        for key, value in self.best_params.items():
            summary += f"  {key}: {value}\n"
        
        summary += f"""
最优指标:
  总收益率:   {self.best_metrics.get('total_return', 0):.2f}%
  年化收益率: {self.best_metrics.get('annual_return', 0):.2f}%
  最大回撤:   {self.best_metrics.get('max_drawdown', 0):.2f}%
  夏普比率:   {self.best_metrics.get('sharpe_ratio', 0):.2f}
{'='*50}
"""
        return summary


class ParameterOptimizer:
    """
    参数优化器
    
    支持网格搜索、随机搜索等方法寻找最优策略参数
    
    Example:
        >>> optimizer = ParameterOptimizer()
        >>> optimizer.set_strategy_class(DualMAStrategy)
        >>> optimizer.set_param_grid({
        ...     "fast_period": [5, 10, 15],
        ...     "slow_period": [20, 30, 60]
        ... })
        >>> optimizer.set_data(codes, start_date, end_date)
        >>> result = optimizer.optimize()
    """
    
    def __init__(self, data_source: Optional[DataSource] = None):
        """
        初始化优化器
        
        Args:
            data_source: 数据源
        """
        self.data_source = data_source or DataSource()
        
        self._strategy_class: Optional[Type[StrategyBase]] = None
        self._strategy_name: str = ""
        self._param_grid: Dict[str, List[Any]] = {}
        self._fixed_params: Dict[str, Any] = {}
        self._backtest_config: Optional[BacktestConfig] = None
        self._codes: List[str] = []
        self._data: Dict[str, pd.DataFrame] = {}
        self._optimization_metric: str = "sharpe_ratio"
        self._maximize: bool = True
        self._progress_callback: Optional[Callable] = None
    
    def set_strategy_class(
        self,
        strategy_class: Type[StrategyBase],
        name: str = ""
    ) -> None:
        """
        设置策略类
        
        Args:
            strategy_class: 策略类
            name: 策略名称
        """
        self._strategy_class = strategy_class
        self._strategy_name = name or strategy_class.__name__
    
    def set_param_grid(self, param_grid: Dict[str, List[Any]]) -> None:
        """
        设置参数网格
        
        Args:
            param_grid: 参数网格，如 {"fast_period": [5, 10], "slow_period": [20, 30]}
        """
        self._param_grid = param_grid
    
    def set_fixed_params(self, params: Dict[str, Any]) -> None:
        """
        设置固定参数
        
        Args:
            params: 固定参数，这些参数在优化过程中保持不变
        """
        self._fixed_params = params
    
    def set_backtest_config(self, config: BacktestConfig) -> None:
        """设置回测配置"""
        self._backtest_config = config
    
    def set_data(
        self,
        codes: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        data_type: str = "etf"
    ) -> None:
        """
        设置回测数据
        
        Args:
            codes: 证券代码列表
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
        """
        self._codes = codes
        self._data_type = data_type
        
        for code in codes:
            df = self.data_source.get_history(code, start_date, end_date, data_type)
            if df is not None:
                self._data[code] = df
    
    def set_optimization_target(
        self,
        metric: str = "sharpe_ratio",
        maximize: bool = True
    ) -> None:
        """
        设置优化目标
        
        Args:
            metric: 优化指标，如 "sharpe_ratio", "total_return", "max_drawdown"
            maximize: 是否最大化（False表示最小化）
        """
        self._optimization_metric = metric
        self._maximize = maximize
    
    def set_progress_callback(self, callback: Callable) -> None:
        """设置进度回调函数"""
        self._progress_callback = callback
    
    def _generate_param_combinations(self) -> List[Dict[str, Any]]:
        """生成所有参数组合"""
        if not self._param_grid:
            return [self._fixed_params.copy()]
        
        keys = list(self._param_grid.keys())
        values = list(self._param_grid.values())
        
        combinations = []
        for combo in product(*values):
            params = dict(zip(keys, combo))
            params.update(self._fixed_params.copy())
            combinations.append(params)
        
        return combinations
    
    def _create_strategy(self, params: Dict[str, Any]) -> StrategyBase:
        """创建策略实例"""
        if self._strategy_class is None:
            raise ValueError("请先设置策略类")
        
        strategy = self._strategy_class()
        strategy.set_params(params)
        return strategy
    
    def _run_single_backtest(
        self,
        params: Dict[str, Any],
        show_progress: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        运行单次回测
        
        Args:
            params: 策略参数
            show_progress: 是否显示进度
            
        Returns:
            (参数字典, 指标字典)
        """
        engine = BacktestEngine(self._backtest_config, self.data_source)
        
        for code, data in self._data.items():
            engine.add_data(code, data)
        
        strategy = self._create_strategy(params)
        engine.add_strategy(strategy)
        
        result = engine.run(show_progress=show_progress)
        
        return params, result.metrics
    
    def optimize(
        self,
        show_progress: bool = True,
        top_n: int = 10
    ) -> OptimizationResult:
        """
        执行参数优化
        
        Args:
            show_progress: 是否显示进度
            top_n: 返回前N个最优结果
            
        Returns:
            优化结果
        """
        if self._strategy_class is None:
            raise ValueError("请先设置策略类")
        
        if self._backtest_config is None:
            raise ValueError("请先设置回测配置")
        
        if not self._data:
            raise ValueError("请先设置回测数据")
        
        start_time = time.time()
        
        combinations = self._generate_param_combinations()
        total = len(combinations)
        
        if show_progress:
            print(f"开始参数优化，共 {total} 个参数组合")
        
        all_results = []
        best_score = float('-inf') if self._maximize else float('inf')
        best_params = {}
        best_metrics = {}
        
        for i, params in enumerate(combinations):
            try:
                _, metrics = self._run_single_backtest(params, show_progress=False)
                
                score = metrics.get(self._optimization_metric, 0)
                
                result_row = {**params, **metrics}
                all_results.append(result_row)
                
                if self._maximize:
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_metrics = metrics.copy()
                else:
                    if score < best_score:
                        best_score = score
                        best_params = params.copy()
                        best_metrics = metrics.copy()
                
                if show_progress:
                    progress = (i + 1) / total * 100
                    print(f"优化进度: {progress:.1f}% ({i+1}/{total}) - 当前最优 {self._optimization_metric}: {best_score:.2f}")
                
                if self._progress_callback:
                    self._progress_callback(i + 1, total, params, metrics)
            
            except Exception as e:
                if show_progress:
                    print(f"参数组合 {params} 回测失败: {str(e)}")
                continue
        
        end_time = time.time()
        
        results_df = pd.DataFrame(all_results)
        
        result = OptimizationResult(
            best_params=best_params,
            best_metrics=best_metrics,
            all_results=results_df,
            optimization_time=end_time - start_time,
            total_combinations=total
        )
        
        if show_progress:
            print(result.get_summary())
        
        return result
    
    def random_search(
        self,
        n_iter: int = 50,
        show_progress: bool = True
    ) -> OptimizationResult:
        """
        随机搜索优化
        
        Args:
            n_iter: 随机采样次数
            show_progress: 是否显示进度
            
        Returns:
            优化结果
        """
        import random
        
        if self._strategy_class is None:
            raise ValueError("请先设置策略类")
        
        if self._backtest_config is None:
            raise ValueError("请先设置回测配置")
        
        if not self._data:
            raise ValueError("请先设置回测数据")
        
        start_time = time.time()
        
        if show_progress:
            print(f"开始随机搜索，共 {n_iter} 次采样")
        
        all_results = []
        best_score = float('-inf') if self._maximize else float('inf')
        best_params = {}
        best_metrics = {}
        
        for i in range(n_iter):
            try:
                params = {}
                for key, values in self._param_grid.items():
                    params[key] = random.choice(values)
                params.update(self._fixed_params.copy())
                
                _, metrics = self._run_single_backtest(params, show_progress=False)
                
                score = metrics.get(self._optimization_metric, 0)
                
                result_row = {**params, **metrics}
                all_results.append(result_row)
                
                if self._maximize:
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_metrics = metrics.copy()
                else:
                    if score < best_score:
                        best_score = score
                        best_params = params.copy()
                        best_metrics = metrics.copy()
                
                if show_progress:
                    progress = (i + 1) / n_iter * 100
                    print(f"搜索进度: {progress:.1f}% ({i+1}/{n_iter}) - 当前最优 {self._optimization_metric}: {best_score:.2f}")
            
            except Exception as e:
                if show_progress:
                    print(f"采样 {i+1} 失败: {str(e)}")
                continue
        
        end_time = time.time()
        
        results_df = pd.DataFrame(all_results)
        
        result = OptimizationResult(
            best_params=best_params,
            best_metrics=best_metrics,
            all_results=results_df,
            optimization_time=end_time - start_time,
            total_combinations=n_iter
        )
        
        if show_progress:
            print(result.get_summary())
        
        return result


def get_strategy_param_grid(strategy_name: str) -> Dict[str, List[Any]]:
    """
    获取策略的默认参数网格
    
    Args:
        strategy_name: 策略名称
        
    Returns:
        参数网格字典
    """
    grids = {
        "双均线策略": {
            "fast_period": [5, 10, 15, 20],
            "slow_period": [20, 30, 40, 60],
            "ma_type": ["SMA", "EMA"]
        },
        "RSI策略": {
            "rsi_period": [6, 9, 14, 21],
            "oversold": [20, 25, 30],
            "overbought": [70, 75, 80]
        },
        "ETF轮动策略": {
            "lookback_days": [5, 10, 20, 30],
            "stop_loss": [0.05, 0.08, 0.10, 0.15],
            "atr_period": [10, 14, 20]
        },
        "MACD策略": {
            "fast_period": [8, 10, 12, 15],
            "slow_period": [20, 26, 30, 35],
            "signal_period": [7, 9, 12],
            "use_histogram": [True, False]
        },
        "布林带策略": {
            "period": [10, 15, 20, 25],
            "std_dev": [1.5, 2.0, 2.5, 3.0],
            "use_middle_exit": [True, False]
        },
        "网格交易策略": {
            "grid_num": [5, 8, 10, 15],
            "grid_range_pct": [0.1, 0.15, 0.2, 0.25],
            "position_per_grid": [0.05, 0.1, 0.15]
        }
    }
    
    return grids.get(strategy_name, {})
