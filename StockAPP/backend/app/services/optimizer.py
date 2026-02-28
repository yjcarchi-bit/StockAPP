"""
参数优化服务
============
复用现有优化器
"""

import sys
import os
import time
from typing import Dict, Any, List
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import ParameterOptimizer, BacktestConfig
from strategies import ETFRotationStrategy


STRATEGY_MAP = {
    "etf_rotation": ETFRotationStrategy,
}


class OptimizerService:
    """参数优化服务"""
    
    @staticmethod
    def _to_native(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        return value
    
    def _normalize_metrics(self, metrics: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
        final_value = float(metrics.get("final_value", initial_capital))
        return {
            "total_return": float(metrics.get("total_return", 0)),
            "annual_return": float(metrics.get("annual_return", 0)),
            "max_drawdown": float(metrics.get("max_drawdown", 0)),
            "sharpe_ratio": float(metrics.get("sharpe_ratio", 0)),
            "sortino_ratio": float(metrics.get("sortino_ratio", 0)),
            "calmar_ratio": float(metrics.get("calmar_ratio", 0)),
            "win_rate": float(metrics.get("win_rate", 0)),
            "profit_factor": float(metrics.get("profit_factor", 0)),
            "total_trades": int(metrics.get("total_trades", 0)),
            "final_value": final_value,
            "benchmark_return": float(metrics.get("benchmark_return", 0)),
        }
    
    def optimize(
        self,
        strategy: str,
        param_grid: Dict[str, List[Any]],
        fixed_params: Dict[str, Any],
        backtest_params: Dict[str, Any],
        etf_codes: List[str],
        metric: str = "sharpe_ratio",
        method: str = "grid",
        n_iter: int = 50
    ) -> Dict[str, Any]:
        """
        参数优化
        
        Args:
            strategy: 策略名称
            param_grid: 参数网格
            fixed_params: 固定参数
            backtest_params: 回测参数
            etf_codes: ETF代码列表
            metric: 优化目标
            method: 优化方法
            n_iter: 随机搜索迭代次数
            
        Returns:
            优化结果
        """
        from .data_source import DataSourceService
        
        if strategy not in STRATEGY_MAP:
            raise ValueError(f"未知策略: {strategy}")
        
        if method not in {"grid", "random"}:
            raise ValueError(f"不支持的优化方法: {method}")
        
        strategy_class = STRATEGY_MAP[strategy]
        
        config = BacktestConfig(
            start_date=backtest_params["start_date"],
            end_date=backtest_params["end_date"],
            initial_capital=backtest_params.get("initial_capital", 100000),
            commission_rate=backtest_params.get("commission_rate", 0.0003),
            stamp_duty=backtest_params.get("stamp_duty", 0.001),
            slippage=backtest_params.get("slippage", 0.0),
        )
        
        data_service = DataSourceService()
        
        optimizer = ParameterOptimizer()
        optimizer.set_strategy_class(strategy_class, strategy)
        optimizer.set_param_grid(param_grid)
        optimizer.set_fixed_params(fixed_params)
        optimizer.set_backtest_config(config)
        optimizer.set_optimization_target(
            metric,
            maximize=metric not in {"max_drawdown", "drawdown"},
        )
        
        data: Dict[str, pd.DataFrame] = {}
        for code in etf_codes:
            history = data_service.get_etf_history(
                code,
                backtest_params["start_date"],
                backtest_params["end_date"]
            )
            if history:
                df = pd.DataFrame(history)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                data[code] = df
        
        if not data:
            raise ValueError("无法获取任何数据")
        
        optimizer._data = data
        optimizer._codes = list(data.keys())
        
        start_ts = time.time()
        if method == "random":
            result = optimizer.random_search(n_iter=n_iter, show_progress=False)
        else:
            result = optimizer.optimize(show_progress=False)
        end_ts = time.time()
        
        best_params = {k: self._to_native(v) for k, v in (result.best_params or {}).items()}
        best_metrics = self._normalize_metrics(result.best_metrics or {}, config.initial_capital)
        
        all_results: List[Dict[str, Any]] = []
        if hasattr(result, "all_results") and isinstance(result.all_results, pd.DataFrame) and not result.all_results.empty:
            for row in result.all_results.to_dict(orient="records"):
                all_results.append({k: self._to_native(v) for k, v in row.items()})
        
        return {
            "best_params": best_params,
            "best_metrics": best_metrics,
            "all_results": all_results,
            "optimization_time": float(result.optimization_time or (end_ts - start_ts)),
            "total_combinations": int(result.total_combinations or len(all_results)),
        }
