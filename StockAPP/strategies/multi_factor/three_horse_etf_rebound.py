"""
三驾马车 ETF 反弹策略（本地化版）
================================
将聚宽三驾马车 v10.2 中「策略2 ETF反弹」迁移到本地回测框架。

核心逻辑:
1. 从候选ETF池中识别“低开反弹”信号
2. 触发卖出条件后在最小持仓天数后卖出
3. 到达最大持仓天数强制卖出
4. 按优先级仅持有1只ETF

说明:
- 聚宽版是分时调度，本地版在日频 `on_trading_day` 执行。
- 信号计算基于日K近似，不使用分钟级数据。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase


THREE_HORSE_REBOUND_ETF_POOL = [
    "159536",  # 中证2000
    "159629",  # 中证1000
    "159922",  # 中证500
    "159919",  # 沪深300
    "159783",  # 双创50
]


class ThreeHorseETFReboundStrategy(StrategyBase):
    """
    三驾马车中的 ETF 反弹子策略。
    """

    display_name = "三驾马车ETF反弹"
    description = (
        "从聚宽三驾马车迁移的ETF反弹子策略。"
        "检测低开后当日反弹信号，结合最小/最大持仓周期控制持仓。"
    )
    logic = [
        "1. 计算低开反弹信号（开盘相对近3日高点偏弱 + 当日收涨）",
        "2. 仅保留优先级最高的触发ETF",
        "3. 持仓ETF若当日走弱且达到最小持仓天数则卖出",
        "4. 持仓到达最大天数强制卖出",
        "5. 使用可用现金买入目标ETF（单标的）",
    ]
    suitable = "适合希望复现三驾马车ETF反弹逻辑、偏短周期轮动的场景"
    risk = "震荡期可能出现频繁换仓；日频近似与聚宽分时执行可能有偏差"
    params_info = {
        "min_holding_days": {
            "default": 2,
            "min": 1,
            "max": 10,
            "step": 1,
            "description": "最小持仓天数",
            "type": "slider",
        },
        "max_holding_days": {
            "default": 5,
            "min": 2,
            "max": 20,
            "step": 1,
            "description": "最大持仓天数",
            "type": "slider",
        },
        "open_to_prev_high_threshold": {
            "default": 0.98,
            "min": 0.90,
            "max": 1.00,
            "step": 0.01,
            "description": "当日开盘/近3日最高价阈值（低于触发）",
            "type": "slider",
        },
        "intraday_rebound_threshold": {
            "default": 1.01,
            "min": 1.00,
            "max": 1.08,
            "step": 0.01,
            "description": "当日收盘/开盘阈值（高于触发）",
            "type": "slider",
        },
        "enable_start_date_guard": {
            "default": True,
            "description": "是否启用开始交易日期限制",
            "type": "switch",
        },
        "use_input_universe": {
            "default": True,
            "description": "优先使用回测传入ETF列表（否则按内置池）",
            "type": "switch",
        },
    }

    def __init__(self):
        super().__init__()
        self._min_holding_days = 2
        self._max_holding_days = 5
        self._open_to_prev_high_threshold = 0.98
        self._intraday_rebound_threshold = 1.01
        self._enable_start_date_guard = True
        self._start_trade_date = "2023-10-01"
        self._use_input_universe = True

        self._holding_days: Dict[str, int] = {}
        self._latest_candidates: List[str] = []
        self._latest_selected: Optional[str] = None

    def initialize(self) -> None:
        self._min_holding_days = int(self.get_param("min_holding_days", 2))
        self._max_holding_days = int(self.get_param("max_holding_days", 5))
        self._open_to_prev_high_threshold = float(self.get_param("open_to_prev_high_threshold", 0.98))
        self._intraday_rebound_threshold = float(self.get_param("intraday_rebound_threshold", 1.01))
        self._enable_start_date_guard = bool(self.get_param("enable_start_date_guard", True))
        self._start_trade_date = "2023-10-01"
        self._use_input_universe = bool(self.get_param("use_input_universe", True))

        self._holding_days = {}
        self._latest_candidates = []
        self._latest_selected = None

        self.log("初始化完成（三驾马车ETF反弹本地版）")

    def _candidate_pool(self) -> List[str]:
        if self._use_input_universe:
            return [code for code in THREE_HORSE_REBOUND_ETF_POOL if code in self._data]
        return [code for code in THREE_HORSE_REBOUND_ETF_POOL if code in self._data]

    def _on_or_after_start_date(self, date: datetime) -> bool:
        if not self._enable_start_date_guard:
            return True
        try:
            threshold = datetime.strptime(self._start_trade_date, "%Y-%m-%d").date()
        except Exception:
            return True
        return date.date() >= threshold

    def _update_holding_days(self) -> None:
        current_codes = [code for code in list(self._portfolio.positions.keys()) if self.has_position(code)]
        current_set = set(current_codes)

        for code in list(self._holding_days.keys()):
            if code not in current_set:
                del self._holding_days[code]

        for code in current_codes:
            self._holding_days[code] = self._holding_days.get(code, 0) + 1

    def _order_target_value(self, code: str, target_value: float) -> None:
        price = self.get_price(code)
        if price <= 0:
            return

        current_amount = self.get_position(code).amount if self.has_position(code) else 0
        current_value = current_amount * price
        diff = target_value - current_value

        if abs(diff) < 100:
            return

        if diff > 0:
            buy_cash = min(diff, self.cash)
            amount = int(buy_cash / price / 100) * 100
            if amount > 0:
                self.buy(code, price=price, amount=amount, name=code)
                self._holding_days.setdefault(code, 0)
            return

        sell_value = -diff
        sell_amount = int(sell_value / price / 100) * 100
        if sell_amount <= 0:
            if current_amount > 0:
                self.sell_all(code, price=price)
            return
        self.sell(code, price=price, amount=sell_amount)

    def _scan_signals(self) -> tuple[List[str], List[str]]:
        buy_candidates: List[str] = []
        sell_flags: List[str] = []

        for code in self._candidate_pool():
            df = self.get_history(code, 5, fields=["open", "high", "close"])
            if df.empty or len(df) < 4:
                continue

            open_arr = df["open"].astype(float).values
            high_arr = df["high"].astype(float).values
            close_arr = df["close"].astype(float).values

            today_open = float(open_arr[-1])
            today_close = float(close_arr[-1])
            y_close = float(close_arr[-2]) if len(close_arr) >= 2 else today_close

            prev_high_max = float(np.max(high_arr[-4:-1])) if len(high_arr) >= 4 else 0.0
            if today_open <= 0 or prev_high_max <= 0:
                continue

            if (
                today_open / prev_high_max < self._open_to_prev_high_threshold
                and today_close / today_open > self._intraday_rebound_threshold
            ):
                buy_candidates.append(code)

            if today_close < y_close:
                sell_flags.append(code)

        prioritized = [c for c in THREE_HORSE_REBOUND_ETF_POOL if c in buy_candidates]
        if prioritized:
            prioritized = [prioritized[0]]

        return prioritized, sell_flags

    def _rebalance(self, selected_list: List[str], sell_flags: List[str]) -> None:
        selected = selected_list[0] if selected_list else None
        self._latest_selected = selected

        current_codes = [code for code in list(self._portfolio.positions.keys()) if self.has_position(code)]
        current_rebound = [c for c in current_codes if c in self._candidate_pool()]
        current_code = current_rebound[0] if current_rebound else None

        force_sell: List[str] = []
        if selected and current_code and current_code != selected:
            # 新信号优先级更高时，主动换仓
            current_idx = THREE_HORSE_REBOUND_ETF_POOL.index(current_code) if current_code in THREE_HORSE_REBOUND_ETF_POOL else 999
            selected_idx = THREE_HORSE_REBOUND_ETF_POOL.index(selected) if selected in THREE_HORSE_REBOUND_ETF_POOL else 999
            if selected_idx < current_idx:
                force_sell.append(current_code)

        for code in list(current_rebound):
            hold_days = self._holding_days.get(code, 0)
            should_sell = (
                (code in sell_flags and hold_days >= self._min_holding_days)
                or hold_days >= self._max_holding_days
                or code in force_sell
            )
            if should_sell:
                self._order_target_value(code, 0.0)

        if not selected:
            return

        if self.has_position(selected):
            return

        self._order_target_value(selected, self.cash)

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        if not self._on_or_after_start_date(date):
            return

        self._update_holding_days()
        buy_candidates, sell_flags = self._scan_signals()
        self._latest_candidates = buy_candidates
        self._rebalance(buy_candidates, sell_flags)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def on_end(self) -> None:
        selected = self._latest_selected or "无"
        self.log(f"回测结束：最后入选ETF {selected}")
