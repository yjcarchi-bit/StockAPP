"""
回测服务
========
复用现有回测引擎
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import BacktestEngine, BacktestConfig
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
    "three_horse_small_cap": "399101",  # 原版小市值核心指数
    "three_horse_white_horse": "000300",  # 沪深300
    "three_horse_carriage": ["399101", "000300"],  # 小市值 + 白马
}

STRATEGY_REQUIRED_INDEX_CODES = {
    "three_horse_small_cap": ["399101"],
    "three_horse_white_horse": ["000300"],
    "three_horse_carriage": ["399101", "000300"],
}

STRATEGY_AUTO_STOCK_LIMIT = {
    # 股票策略在未显式指定股票列表时，默认自动加载成分股数量上限。
    # 0 表示不截断（按完整成分股集合加载）。
    "three_horse_small_cap": 300,
    "three_horse_white_horse": 200,
    "three_horse_carriage": 0,
}

STRATEGY_WARMUP_DAYS = {
    # 按交易窗口需求预留历史数据，避免回测起始阶段因历史不足无法发出信号。
    # 注意: 这里是“交易日级别预估”，实际会按自然日放大后回拉。
    "etf_rotation": 260,
    "three_horse_etf_rotation": 300,
    "three_horse_etf_rebound": 20,
    "three_horse_dual_etf": 320,
    "three_horse_small_cap": 260,
    "three_horse_white_horse": 320,
    "three_horse_carriage": 360,
}

THREE_HORSE_COST_PRESET = {
    # 贴近原版 set_backtest:
    # stock: commission=0.85/10000, close_tax=0.0005, slippage=0.002
    # fund : commission=0.5/10000,  close_tax=0.0,    slippage=0.001
    "stock_commission_rate": 0.85 / 10000,
    "stock_stamp_duty": 0.0005,
    "stock_min_commission": 5.0,
    "fund_commission_rate": 0.5 / 10000,
    "fund_stamp_duty": 0.0,
    "fund_min_commission": 5.0,
    "stock_slippage": 0.002,
    "fund_slippage": 0.001,
}


class BacktestService:
    """回测服务"""
    
    def __init__(self):
        self.data_cache = {}

    @staticmethod
    def _expand_start_date(start_date: str, warmup_days: int) -> str:
        if warmup_days <= 0:
            return start_date
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            # 交易日近似转换为自然日，避免停牌/节假日导致窗口不足。
            expanded = dt - timedelta(days=warmup_days * 2)
            return expanded.strftime("%Y-%m-%d")
        except Exception:
            return start_date
    
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
        strategy_instance = strategy_class()
        effective_strategy_params: Dict[str, Any] = dict(strategy_params or {})

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
        
        engine = BacktestEngine(config)
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
                auto_stock_limit = int((effective_strategy_params or {}).get("auto_stock_limit", default_limit))
            except (TypeError, ValueError):
                auto_stock_limit = default_limit
            auto_stock_limit = max(0, auto_stock_limit)
            use_historical_constituents = bool((effective_strategy_params or {}).get("use_historical_constituents", True))
            constituent_freq = str((effective_strategy_params or {}).get("constituent_freq", "M")).upper() or "M"
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
                enforce_sub_universe = bool(effective_strategy_params.get("enforce_sub_universe", False))
                if enforce_sub_universe:
                    small_codes = index_stock_map.get("399101", [])
                    white_codes = index_stock_map.get("000300", [])
                    if auto_stock_limit > 0:
                        small_codes = small_codes[:auto_stock_limit]
                        white_codes = white_codes[:auto_stock_limit]
                    if small_codes and "small_universe_codes" not in effective_strategy_params:
                        effective_strategy_params["small_universe_codes"] = small_codes
                    if white_codes and "white_universe_codes" not in effective_strategy_params:
                        effective_strategy_params["white_universe_codes"] = white_codes
            elif strategy in {"three_horse_small_cap", "three_horse_white_horse"}:
                if stock_codes and "universe_codes" not in effective_strategy_params:
                    effective_strategy_params["universe_codes"] = stock_codes[:]

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

        loaded_codes = 0

        for code in stock_codes:
            data = data_service.get_stock_history(
                code,
                fetch_start_date,
                backtest_params["end_date"]
            )
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                engine.add_data(code, df)
                loaded_codes += 1

        for code in STRATEGY_REQUIRED_INDEX_CODES.get(strategy, []):
            data = data_service.get_index_history(
                code,
                fetch_start_date,
                backtest_params["end_date"]
            )
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                engine.add_data(code, df)
                loaded_codes += 1

        for code in etf_codes_to_load:
            data = data_service.get_etf_history(
                code,
                fetch_start_date,
                backtest_params["end_date"]
            )
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                engine.add_data(code, df)
                loaded_codes += 1
        
        if loaded_codes == 0:
            raise ValueError("未获取到可用于回测的历史数据")

        strategy_instance.set_params(effective_strategy_params)
        
        engine.add_strategy(strategy_instance)
        
        result = engine.run(show_progress=False)
        
        return self._format_result(result, strategy)
    
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
    
    def _extract_daily_values(self, result: Any) -> pd.DataFrame:
        daily_values = result.daily_values.copy()
        if daily_values.empty:
            return pd.DataFrame(columns=["date", "total_value", "cash", "positions"])
        
        if "date" not in daily_values.columns:
            daily_values = daily_values.reset_index()
            if "index" in daily_values.columns:
                daily_values = daily_values.rename(columns={"index": "date"})
        
        daily_values["date"] = pd.to_datetime(daily_values["date"])
        daily_values = daily_values.sort_values("date").reset_index(drop=True)
        return daily_values
    
    def _build_monthly_returns(self, daily_values: pd.DataFrame) -> List[Dict[str, Any]]:
        if daily_values.empty:
            return []
        
        monthly_returns: List[Dict[str, Any]] = []
        grouped = daily_values.groupby([daily_values["date"].dt.year, daily_values["date"].dt.month], sort=True)
        
        for (year, month), group in grouped:
            start_val = float(group["total_value"].iloc[0])
            end_val = float(group["total_value"].iloc[-1])
            if start_val == 0:
                return_rate = 0.0
            else:
                return_rate = (end_val / start_val - 1) * 100
            
            monthly_returns.append(
                {
                    "year": int(year),
                    "month": int(month),
                    "return_rate": round(float(return_rate), 4),
                }
            )
        
        return monthly_returns
    
    def _build_trades(self, result: Any) -> List[Dict[str, Any]]:
        trade_records = result.trade_records.copy()
        if trade_records.empty:
            return []
        
        if "timestamp" in trade_records.columns:
            trade_records["timestamp"] = pd.to_datetime(trade_records["timestamp"])
            trade_records = trade_records.sort_values("timestamp")
        
        trades: List[Dict[str, Any]] = []
        for _, row in trade_records.iterrows():
            timestamp_raw = row.get("timestamp")
            timestamp = (
                timestamp_raw.strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(timestamp_raw, "strftime")
                else str(timestamp_raw)
            )
            price = float(row.get("price", 0))
            amount = int(row.get("amount", 0))
            value = row.get("value", price * amount)
            side = str(row.get("side", "")).lower()
            if side not in {"buy", "sell"}:
                side = "buy"
            
            trades.append(
                {
                    "timestamp": timestamp,
                    "code": str(row.get("code", "")),
                    "side": side,
                    "price": price,
                    "amount": amount,
                    "value": float(value),
                }
            )
        
        return trades
    
    def _build_daily_positions(self, daily_values: pd.DataFrame, initial_capital: float) -> List[Dict[str, Any]]:
        if daily_values.empty:
            return []
        
        daily_positions: List[Dict[str, Any]] = []
        prev_market_values: Dict[str, float] = {}
        prev_total_value: Optional[float] = None
        
        for _, row in daily_values.iterrows():
            row_positions = row.get("positions", {})
            if not isinstance(row_positions, dict):
                row_positions = {}
            
            current_market_values: Dict[str, float] = {}
            position_items = []
            
            for code, pos in row_positions.items():
                if not isinstance(pos, dict):
                    continue
                
                shares = int(pos.get("amount", pos.get("shares", 0)) or 0)
                price = float(pos.get("current_price", pos.get("price", 0)) or 0)
                market_value = float(pos.get("market_value", shares * price) or 0)
                profit = float(pos.get("profit", 0) or 0)
                profit_pct = float(pos.get("profit_pct", 0) or 0)
                
                prev_mv = prev_market_values.get(code)
                daily_profit = market_value - prev_mv if prev_mv is not None else profit
                current_market_values[code] = market_value
                
                position_items.append(
                    {
                        "code": str(code),
                        "name": str(pos.get("name", "")),
                        "shares": shares,
                        "price": price,
                        "market_value": market_value,
                        "profit": profit,
                        "daily_profit": float(daily_profit),
                        "profit_pct": profit_pct,
                    }
                )
            
            cash = float(row.get("cash", 0) or 0)
            total_value = float(row.get("total_value", cash + sum(item["market_value"] for item in position_items)) or 0)
            total_profit = total_value - initial_capital
            total_daily_profit = total_value - prev_total_value if prev_total_value is not None else total_profit
            
            daily_positions.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "positions": position_items,
                    "cash": cash,
                    "total_value": total_value,
                    "total_profit": float(total_profit),
                    "total_daily_profit": float(total_daily_profit),
                }
            )
            
            prev_market_values = current_market_values
            prev_total_value = total_value
        
        return daily_positions
    
    def _format_result(self, result, strategy: str) -> Dict[str, Any]:
        """格式化回测结果"""
        initial_capital = float(result.config.initial_capital)
        metrics = self._normalize_metrics(result.metrics or {}, initial_capital)
        
        daily_values = self._extract_daily_values(result)
        equity_curve = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "value": float(row.get("total_value", 0)),
            }
            for _, row in daily_values.iterrows()
        ]
        
        trades = self._build_trades(result)
        monthly_returns = self._build_monthly_returns(daily_values)
        daily_positions = self._build_daily_positions(daily_values, initial_capital)
        
        return {
            "strategy": strategy,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": trades,
            "monthly_returns": monthly_returns,
            "daily_positions": daily_positions,
        }
