"""
参数优化服务
============
复用现有优化器
"""

import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import ParameterOptimizer, BacktestConfig
from strategies import (
    ETFRotationStrategy,
    ThreeHorseETFRotationStrategy,
    ThreeHorseETFReboundStrategy,
    ThreeHorseDualETFStrategy,
    ThreeHorseSmallCapStrategy,
    ThreeHorseWhiteHorseStrategy,
    ThreeHorseCarriageStrategy,
)


STRATEGY_MAP = {
    "etf_rotation": ETFRotationStrategy,
    "three_horse_etf_rotation": ThreeHorseETFRotationStrategy,
    "three_horse_etf_rebound": ThreeHorseETFReboundStrategy,
    "three_horse_dual_etf": ThreeHorseDualETFStrategy,
    "three_horse_small_cap": ThreeHorseSmallCapStrategy,
    "three_horse_white_horse": ThreeHorseWhiteHorseStrategy,
    "three_horse_carriage": ThreeHorseCarriageStrategy,
}

STRATEGY_DATA_MODE = {
    "three_horse_small_cap": "stock",
    "three_horse_white_horse": "stock",
    "three_horse_carriage": "stock",
}

STRATEGY_REQUIRED_ETF_CODES = {
    "three_horse_etf_rotation": [
        "510180", "513030", "513100", "513520", "510410", "518880", "501018", "159985", "511090",
        "159915", "588120", "512480", "159851", "513020", "159637", "513630", "510050",
    ],
    "three_horse_etf_rebound": [
        "159536", "159629", "159922", "159919", "159783",
    ],
    "three_horse_dual_etf": [
        "159536", "159629", "159922", "159919", "159783",
        "510180", "513030", "513100", "513520", "510410", "518880", "501018", "159985", "511090",
        "159915", "588120", "512480", "159851", "513020", "159637", "513630", "510050",
    ],
    "three_horse_small_cap": [
        "512800",
    ],
    "three_horse_white_horse": [
        "511010",
    ],
    "three_horse_carriage": [
        "512800", "511010",
        "159536", "159629", "159922", "159919", "159783",
        "510180", "513030", "513100", "513520", "510410", "518880", "501018", "159985", "511090",
        "159915", "588120", "512480", "159851", "513020", "159637", "513630", "510050",
    ],
}

STRATEGY_REQUIRED_STOCK_INDEX = {
    "three_horse_small_cap": "399101",
    "three_horse_white_horse": "000300",
    "three_horse_carriage": ["399101", "000300"],
}

STRATEGY_REQUIRED_INDEX_CODES = {
    "three_horse_small_cap": ["399101"],
    "three_horse_white_horse": ["000300"],
    "three_horse_carriage": ["399101", "000300"],
}

STRATEGY_AUTO_STOCK_LIMIT = {
    "three_horse_small_cap": 300,
    "three_horse_white_horse": 200,
    "three_horse_carriage": 0,
}

STRATEGY_WARMUP_DAYS = {
    "etf_rotation": 260,
    "three_horse_etf_rotation": 300,
    "three_horse_etf_rebound": 20,
    "three_horse_dual_etf": 320,
    "three_horse_small_cap": 260,
    "three_horse_white_horse": 320,
    "three_horse_carriage": 360,
}

THREE_HORSE_COST_PRESET = {
    "stock_commission_rate": 0.85 / 10000,
    "stock_stamp_duty": 0.0005,
    "stock_min_commission": 5.0,
    "fund_commission_rate": 0.5 / 10000,
    "fund_stamp_duty": 0.0,
    "fund_min_commission": 5.0,
    "stock_slippage": 0.002,
    "fund_slippage": 0.001,
}


class OptimizerService:
    """参数优化服务"""
    
    @staticmethod
    def _to_native(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        return value

    @staticmethod
    def _expand_start_date(start_date: str, warmup_days: int) -> str:
        if warmup_days <= 0:
            return start_date
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            expanded = dt - timedelta(days=warmup_days * 2)
            return expanded.strftime("%Y-%m-%d")
        except Exception:
            return start_date
    
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
        effective_fixed_params: Dict[str, Any] = dict(fixed_params or {})
        is_three_horse = strategy.startswith("three_horse")
        preset = THREE_HORSE_COST_PRESET if is_three_horse else {}
        
        config = BacktestConfig(
            start_date=backtest_params["start_date"],
            end_date=backtest_params["end_date"],
            initial_capital=backtest_params.get("initial_capital", 100000),
            commission_rate=backtest_params.get(
                "commission_rate",
                preset.get("stock_commission_rate", 0.0003),
            ),
            stamp_duty=backtest_params.get(
                "stamp_duty",
                preset.get("stock_stamp_duty", 0.001),
            ),
            min_commission=backtest_params.get(
                "min_commission",
                preset.get("stock_min_commission", 5.0),
            ),
            slippage=backtest_params.get("slippage", 0.0),
            stock_commission_rate=backtest_params.get(
                "stock_commission_rate",
                preset.get("stock_commission_rate"),
            ),
            stock_stamp_duty=backtest_params.get(
                "stock_stamp_duty",
                preset.get("stock_stamp_duty"),
            ),
            stock_min_commission=backtest_params.get(
                "stock_min_commission",
                preset.get("stock_min_commission"),
            ),
            fund_commission_rate=backtest_params.get(
                "fund_commission_rate",
                preset.get("fund_commission_rate"),
            ),
            fund_stamp_duty=backtest_params.get(
                "fund_stamp_duty",
                preset.get("fund_stamp_duty"),
            ),
            fund_min_commission=backtest_params.get(
                "fund_min_commission",
                preset.get("fund_min_commission"),
            ),
            stock_slippage=backtest_params.get(
                "stock_slippage",
                preset.get("stock_slippage"),
            ),
            fund_slippage=backtest_params.get(
                "fund_slippage",
                preset.get("fund_slippage"),
            ),
        )
        
        data_service = DataSourceService()
        warmup_days = int(STRATEGY_WARMUP_DAYS.get(strategy, 0))
        fetch_start_date = self._expand_start_date(backtest_params["start_date"], warmup_days)
        
        optimizer = ParameterOptimizer()
        optimizer.set_strategy_class(strategy_class, strategy)
        optimizer.set_param_grid(param_grid)
        optimizer.set_fixed_params(effective_fixed_params)
        optimizer.set_backtest_config(config)
        optimizer.set_optimization_target(
            metric,
            maximize=metric not in {"max_drawdown", "drawdown"},
        )
        
        data: Dict[str, pd.DataFrame] = {}
        requested_codes = list(etf_codes or [])
        mode = STRATEGY_DATA_MODE.get(strategy, "etf")

        def _is_stock_code(code: str) -> bool:
            code = str(code).strip()
            return len(code) == 6 and code[0] in {"0", "3", "6"}

        stock_codes: List[str] = []
        index_stock_map: Dict[str, List[str]] = {}
        auto_stock_limit = 0
        if mode == "stock":
            default_limit = int(STRATEGY_AUTO_STOCK_LIMIT.get(strategy, 0) or 0)
            try:
                auto_stock_limit = int((effective_fixed_params or {}).get("auto_stock_limit", default_limit))
            except (TypeError, ValueError):
                auto_stock_limit = default_limit
            auto_stock_limit = max(0, auto_stock_limit)
            use_historical_constituents = bool((effective_fixed_params or {}).get("use_historical_constituents", True))
            constituent_freq = str((effective_fixed_params or {}).get("constituent_freq", "M")).upper() or "M"
            if constituent_freq not in {"M", "Q"}:
                constituent_freq = "M"

            stock_codes = [c for c in requested_codes if _is_stock_code(c)]
            stock_codes = list(dict.fromkeys(stock_codes))
            if not stock_codes:
                index_codes_raw = STRATEGY_REQUIRED_STOCK_INDEX.get(strategy)
                if index_codes_raw:
                    index_codes = index_codes_raw if isinstance(index_codes_raw, list) else [index_codes_raw]
                    merged: List[str] = []
                    for index_code in index_codes:
                        if use_historical_constituents:
                            constituents = data_service.get_index_constituents_history(
                                str(index_code),
                                fetch_start_date,
                                backtest_params["end_date"],
                                freq=constituent_freq,
                            )
                        else:
                            constituents = data_service.get_index_constituents(
                                str(index_code),
                                date=backtest_params["end_date"],
                            )
                        index_codes_list: List[str] = []
                        for item in constituents:
                            code = item.get("code", "")
                            if not _is_stock_code(code):
                                continue
                            if code not in index_codes_list:
                                index_codes_list.append(code)
                            if code not in merged:
                                merged.append(code)
                        index_stock_map[str(index_code)] = index_codes_list
                    if auto_stock_limit > 0:
                        merged = merged[:auto_stock_limit]
                    stock_codes = merged

            if strategy == "three_horse_carriage":
                enforce_sub_universe = bool(effective_fixed_params.get("enforce_sub_universe", False))
                if enforce_sub_universe:
                    small_codes = index_stock_map.get("399101", [])
                    white_codes = index_stock_map.get("000300", [])
                    if auto_stock_limit > 0:
                        small_codes = small_codes[:auto_stock_limit]
                        white_codes = white_codes[:auto_stock_limit]
                    if small_codes and "small_universe_codes" not in effective_fixed_params:
                        effective_fixed_params["small_universe_codes"] = small_codes
                    if white_codes and "white_universe_codes" not in effective_fixed_params:
                        effective_fixed_params["white_universe_codes"] = white_codes
            elif strategy in {"three_horse_small_cap", "three_horse_white_horse"}:
                if stock_codes and "universe_codes" not in effective_fixed_params:
                    effective_fixed_params["universe_codes"] = stock_codes[:]

        optimizer.set_fixed_params(effective_fixed_params)

        etf_codes_to_load: List[str] = []
        etf_codes_to_load.extend([c for c in STRATEGY_REQUIRED_ETF_CODES.get(strategy, []) if c not in etf_codes_to_load])
        if mode == "stock":
            user_etf_codes = [c for c in requested_codes if not _is_stock_code(c)]
            for c in user_etf_codes:
                if c not in etf_codes_to_load:
                    etf_codes_to_load.append(c)
        else:
            for c in requested_codes:
                if c not in etf_codes_to_load:
                    etf_codes_to_load.append(c)

        for code in stock_codes:
            history = data_service.get_stock_history(
                code,
                fetch_start_date,
                backtest_params["end_date"]
            )
            if history:
                df = pd.DataFrame(history)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                data[code] = df

        for code in STRATEGY_REQUIRED_INDEX_CODES.get(strategy, []):
            history = data_service.get_index_history(
                code,
                fetch_start_date,
                backtest_params["end_date"]
            )
            if history:
                df = pd.DataFrame(history)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                data[code] = df

        for code in etf_codes_to_load:
            history = data_service.get_etf_history(
                code,
                fetch_start_date,
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
