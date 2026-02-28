"""
参数优化服务
============
复用现有优化器
"""

import sys
import os
from typing import Dict, Any, List
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import ParameterOptimizer, BacktestConfig
from strategies import ETFRotationStrategy


STRATEGY_MAP = {
    "etf_rotation": ETFRotationStrategy,
}


class OptimizerService:
    """参数优化服务"""
    
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
        
        strategy_class = STRATEGY_MAP[strategy]
        
        config = BacktestConfig(
            start_date=backtest_params["start_date"],
            end_date=backtest_params["end_date"],
            initial_capital=backtest_params.get("initial_capital", 100000),
        )
        
        data_service = DataSourceService()
        
        optimizer = ParameterOptimizer()
        optimizer.set_strategy_class(strategy_class, strategy)
        optimizer.set_param_grid(param_grid)
        optimizer.set_fixed_params(fixed_params)
        optimizer.set_backtest_config(config)
        optimizer.set_optimization_target(metric, maximize=True)
        
        data = {}
        for code in etf_codes:
            history = data_service.get_etf_history(
                code,
                backtest_params["start_date"],
                backtest_params["end_date"]
            )
            if history:
                import pandas as pd
                df = pd.DataFrame(history)
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
                data[code] = df
        
        if not data:
            raise ValueError("无法获取任何数据")
