"""
回测服务
========
复用现有回测引擎
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import BacktestEngine, BacktestConfig
from strategies import ETFRotationStrategy


STRATEGY_MAP = {
    "etf_rotation": ETFRotationStrategy,
}


class BacktestService:
    """回测服务"""
    
    def __init__(self):
        self.data_cache = {}
    
    def run(
        self,
        strategy: str,
        strategy_params: Dict[str, Any],
        backtest_params: Dict[str, Any],
        etf_codes: List[str]
    ) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy: 策略名称
            strategy_params: 策略参数
            backtest_params: 回测参数
            etf_codes: ETF代码列表
            
        Returns:
            回测结果字典
        """
        from .data_source import DataSourceService
        
        if strategy not in STRATEGY_MAP:
            raise ValueError(f"未知策略: {strategy}")
        
        strategy_class = STRATEGY_MAP[strategy]
        strategy_instance = strategy_class(**strategy_params)
        
        config = BacktestConfig(
            start_date=backtest_params["start_date"],
            end_date=backtest_params["end_date"],
            initial_capital=backtest_params.get("initial_capital", 100000),
            commission_rate=backtest_params.get("commission_rate", 0.0003),
            stamp_duty=backtest_params.get("stamp_duty", 0.001),
        )
        
        data_service = DataSourceService()
        
        engine = BacktestEngine(config)
        
        for code in etf_codes:
            data = data_service.get_etf_history(
                code,
                backtest_params["start_date"],
                backtest_params["end_date"]
            )
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
                engine.add_data(code, df)
        
        engine.add_strategy(strategy_instance)
        
        result = engine.run(show_progress=False)
        
        return self._format_result(result, strategy)
    
    def _format_result(self, result, strategy: str) -> Dict[str, Any]:
        """格式化回测结果"""
        equity_curve = []
