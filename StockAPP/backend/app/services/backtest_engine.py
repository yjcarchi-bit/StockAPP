"""
回测服务
========
复用现有回测引擎
"""

import sys
import os
import pandas as pd
from typing import Dict, Any, List, Optional

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
        strategy_instance = strategy_class()
        strategy_instance.set_params(strategy_params or {})
        
        config = BacktestConfig(
            start_date=backtest_params["start_date"],
            end_date=backtest_params["end_date"],
            initial_capital=backtest_params.get("initial_capital", 100000),
            commission_rate=backtest_params.get("commission_rate", 0.0003),
            stamp_duty=backtest_params.get("stamp_duty", 0.001),
            slippage=backtest_params.get("slippage", 0.0),
        )
        
        data_service = DataSourceService()
        
        engine = BacktestEngine(config)
        loaded_codes = 0
        
        for code in etf_codes:
            data = data_service.get_etf_history(
                code,
                backtest_params["start_date"],
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
