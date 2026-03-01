"""
三驾马车双ETF组合策略（本地化版）
================================
将三驾马车中的两个 ETF 子策略在本地统一为一个可回测策略：
- 策略2：ETF反弹
- 策略3：ETF轮动

组合规则:
1. 分别生成“反弹ETF”与“轮动ETF”目标
2. 按资金配比映射为目标仓位
3. 在单账户下统一调仓（若两个子策略选中同一ETF，仓位叠加）
4. 支持 2023-09-28 前后资金配比拨正（模拟原策略 capital_balance_2）
"""

from __future__ import annotations

import math
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase


THREE_HORSE_ETF_REBOUND_POOL = [
    "159536",
    "159629",
    "159922",
    "159919",
    "159783",
]

THREE_HORSE_ETF_ROTATION_POOL = [
    "510180",
    "513030",
    "513100",
    "513520",
    "510410",
    "518880",
    "501018",
    "159985",
    "511090",
    "159915",
    "588120",
    "512480",
    "159851",
    "513020",
    "159637",
    "513630",
    "510050",
]


class ThreeHorseDualETFStrategy(StrategyBase):
    """
    三驾马车双ETF组合（策略2 + 策略3）。
    """

    display_name = "三驾马车双ETF组合"
    description = (
        "将三驾马车中的ETF反弹与ETF轮动合并为本地单策略。"
        "在一个账户中按配比分配两个子策略仓位，并支持原策略的拨正规则。"
    )
    logic = [
        "1. ETF反弹子策略选出最多1个标的",
        "2. ETF轮动子策略选出最多1个标的",
        "3. 按配比映射目标仓位（可启用拨正规则）",
        "4. 统一调仓到目标值，未入选ETF减仓到0",
        "5. 若两个子策略命中同一ETF则仓位叠加",
    ]
    suitable = "适合希望在本地较完整复现三驾马车ETF部分资金分配逻辑的场景"
    risk = "子策略同向失效时组合回撤会放大；日频近似与聚宽分时行为会有偏差"
    params_info = {
        "rotation_ratio": {
            "default": 0.35,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "ETF轮动子策略资金占比",
            "type": "slider",
        },
        "rebound_ratio": {
            "default": 0.10,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "ETF反弹子策略资金占比",
            "type": "slider",
        },
        "enable_capital_balance_rule": {
            "default": True,
            "description": "启用2023-09-28前后拨正规则（反弹仓位临时并入轮动）",
            "type": "switch",
        },
        "rotation_lookback_days": {
            "default": 25,
            "min": 15,
            "max": 60,
            "step": 5,
            "description": "轮动动量回看天数",
            "type": "slider",
        },
        "rotation_min_score": {
            "default": 0.3,
            "min": 0.0,
            "max": 2.0,
            "step": 0.1,
            "description": "轮动最小动量得分",
            "type": "slider",
        },
        "rotation_max_score": {
            "default": 5.0,
            "min": 1.0,
            "max": 10.0,
            "step": 0.5,
            "description": "轮动最大动量得分",
            "type": "slider",
        },
        "rotation_enable_day_stop_filter": {
            "default": True,
            "description": "轮动启用当日跌幅过滤",
            "type": "switch",
        },
        "rotation_day_stoploss_limit": {
            "default": -0.03,
            "min": -0.10,
            "max": -0.01,
            "step": 0.01,
            "description": "轮动当日跌幅阈值（close/open-1）",
            "type": "slider",
        },
        "rebound_min_holding_days": {
            "default": 2,
            "min": 1,
            "max": 10,
            "step": 1,
            "description": "反弹最小持仓天数",
            "type": "slider",
        },
        "rebound_max_holding_days": {
            "default": 5,
            "min": 2,
            "max": 20,
            "step": 1,
            "description": "反弹最大持仓天数",
            "type": "slider",
        },
    }

    def __init__(self):
        super().__init__()

        self._rotation_ratio = 0.35
        self._rebound_ratio = 0.10
        self._enable_capital_balance_rule = True
        self._capital_balance_date = date(2023, 9, 28)
        self._rebound_start_trade_date = date(2023, 10, 1)

        # rotation params
        self._rotation_lookback_days = 25
        self._rotation_min_score = 0.3
        self._rotation_max_score = 5.0
        self._rotation_recent_drop_threshold = 0.95
        self._rotation_enable_day_stop_filter = True
        self._rotation_day_stoploss_limit = -0.03
        self._rotation_use_rsrs = True
        self._rotation_use_volume = True
        self._rotation_volume_lookback_days = 7
        self._rotation_volume_threshold = 2.0

        # rebound params
        self._rebound_min_holding_days = 2
        self._rebound_max_holding_days = 5
        self._rebound_open_to_prev_high_threshold = 0.98
        self._rebound_intraday_rebound_threshold = 1.01

        self._rebound_current_code: Optional[str] = None
        self._rebound_holding_days = 0

        self._last_rotation_code: Optional[str] = None
        self._last_rebound_code: Optional[str] = None

    def initialize(self) -> None:
        self._rotation_ratio = float(self.get_param("rotation_ratio", 0.35))
        self._rebound_ratio = float(self.get_param("rebound_ratio", 0.10))
        self._enable_capital_balance_rule = bool(self.get_param("enable_capital_balance_rule", True))

        self._rotation_lookback_days = int(self.get_param("rotation_lookback_days", 25))
        self._rotation_min_score = float(self.get_param("rotation_min_score", 0.3))
        self._rotation_max_score = float(self.get_param("rotation_max_score", 5.0))
        self._rotation_enable_day_stop_filter = bool(self.get_param("rotation_enable_day_stop_filter", True))
        self._rotation_day_stoploss_limit = float(self.get_param("rotation_day_stoploss_limit", -0.03))

        self._rebound_min_holding_days = int(self.get_param("rebound_min_holding_days", 2))
        self._rebound_max_holding_days = int(self.get_param("rebound_max_holding_days", 5))

        self._rebound_current_code = None
        self._rebound_holding_days = 0
        self._last_rotation_code = None
        self._last_rebound_code = None

        self.log("初始化完成（三驾马车双ETF组合本地版）")

    def _available_codes(self, pool: List[str]) -> List[str]:
        return [c for c in pool if c in self._data]

    def _effective_weights(self) -> tuple[float, float]:
        rotation = max(0.0, self._rotation_ratio)
        rebound = max(0.0, self._rebound_ratio)

        if self._enable_capital_balance_rule and self.current_date is not None:
            if self.current_date.date() < self._capital_balance_date:
                rotation += rebound
                rebound = 0.0

        total = rotation + rebound
        if total <= 0:
            return 0.0, 0.0
        if total > 1.0:
            rotation /= total
            rebound /= total
        return rotation, rebound

    # ---------- rotation sleeve ----------
    def _rotation_day_ratio(self, code: str) -> Optional[float]:
        df = self.get_history(code, 1, fields=["open", "close"])
        if df.empty:
            return None
        o = float(df["open"].iloc[-1])
        c = float(df["close"].iloc[-1])
        if o <= 0:
            return None
        return c / o - 1

    def _rotation_pass_recent_drop(self, code: str) -> bool:
        prices = self.get_prices(code, 4, field="close")
        if len(prices) < 4:
            return False
        r1 = prices[-1] / prices[-2] if prices[-2] > 0 else 0.0
        r2 = prices[-2] / prices[-3] if prices[-3] > 0 else 0.0
        r3 = prices[-3] / prices[-4] if prices[-4] > 0 else 0.0
        return min(r1, r2, r3) >= self._rotation_recent_drop_threshold

    def _rotation_rsrs(self, code: str) -> bool:
        if not self._rotation_use_rsrs:
            return True

        lookback_days = 250
        window = 20
        days = 18
        min_bars = max(lookback_days, days, 10)
        df = self.get_history(code, min_bars, fields=["high", "low", "close"])
        if df.empty:
            return False

        high = df["high"].astype(float).values
        low = df["low"].astype(float).values
        close = df["close"].astype(float).values

        if len(high) < days or len(low) < days:
            return False
        low_recent = low[-days:]
        high_recent = high[-days:]
        if np.std(low_recent) == 0:
            return False

        try:
            slope = float(np.polyfit(low_recent, high_recent, 1)[0])
        except Exception:
            return False

        if len(high) < lookback_days or len(low) < lookback_days:
            return False
        hh = high[-lookback_days:]
        ll = low[-lookback_days:]
        slopes: List[float] = []
        for i in range(0, len(hh) - window + 1):
            hw = hh[i:i + window]
            lw = ll[i:i + window]
            if np.std(lw) == 0:
                continue
            if np.any(np.isnan(hw)) or np.any(np.isnan(lw)):
                continue
            try:
                slopes.append(float(np.polyfit(lw, hw, 1)[0]))
            except Exception:
                continue
        if len(slopes) < 2:
            return False
        beta = float(np.mean(slopes) - 2 * np.std(slopes))
        if slope <= beta:
            return False

        strength = 0.0 if beta == 0 else (slope - beta) / abs(beta)
        ma5 = float(np.mean(close[-5:])) if len(close) >= 5 else -1e18
        ma10 = float(np.mean(close[-10:])) if len(close) >= 10 else -1e18
        cur = float(close[-1])
        above_ma5 = cur >= ma5
        above_ma10 = cur >= ma10

        if strength > 0.15:
            return True
        if strength > 0.03 and above_ma5:
            return True
        return above_ma10

    def _rotation_volume(self, code: str) -> bool:
        if not self._rotation_use_volume:
            return True
        bars_needed = self._rotation_volume_lookback_days + 1
        df = self.get_history(code, bars_needed, fields=["volume"])
        if df.empty or len(df) < bars_needed:
            return False
        vol = df["volume"].astype(float).values
        avg = float(np.mean(vol[:-1]))
        cur = float(vol[-1])
        if avg <= 0:
            return False
        return (cur / avg) <= self._rotation_volume_threshold

    def _rotation_momentum(self, code: str) -> Optional[float]:
        prices = self.get_prices(code, self._rotation_lookback_days + 1, field="close")
        if len(prices) < self._rotation_lookback_days + 1:
            return None
        if np.any(prices <= 0):
            return None
        y = np.log(prices)
        x = np.arange(len(y))
        w = np.linspace(1.0, 2.0, len(y))
        try:
            slope, intercept = np.polyfit(x, y, 1, w=w)
        except Exception:
            return None
        ann = math.exp(slope * 250) - 1
        y_pred = slope * x + intercept
        ss_res = float(np.sum(w * (y - y_pred) ** 2))
        ss_tot = float(np.sum(w * (y - np.mean(y)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return float(ann * r2)

    def _select_rotation(self) -> Optional[str]:
        scores: Dict[str, float] = {}
        for code in self._available_codes(THREE_HORSE_ETF_ROTATION_POOL):
            if not self._rotation_pass_recent_drop(code):
                continue
            if self._rotation_enable_day_stop_filter:
                ratio = self._rotation_day_ratio(code)
                if ratio is None or ratio <= self._rotation_day_stoploss_limit:
                    continue
            if not self._rotation_rsrs(code):
                continue
            if not self._rotation_volume(code):
                continue

            score = self._rotation_momentum(code)
            if score is None:
                continue
            if score <= self._rotation_min_score or score >= self._rotation_max_score:
                continue
            scores[code] = score

        if not scores:
            return None
        return max(scores.items(), key=lambda x: x[1])[0]

    # ---------- rebound sleeve ----------
    def _rebound_scan(self) -> tuple[List[str], List[str]]:
        buy_candidates: List[str] = []
        sell_flags: List[str] = []

        for code in self._available_codes(THREE_HORSE_ETF_REBOUND_POOL):
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
                today_open / prev_high_max < self._rebound_open_to_prev_high_threshold
                and today_close / today_open > self._rebound_intraday_rebound_threshold
            ):
                buy_candidates.append(code)

            if today_close < y_close:
                sell_flags.append(code)

        prioritized = [c for c in THREE_HORSE_ETF_REBOUND_POOL if c in buy_candidates]
        if prioritized:
            prioritized = [prioritized[0]]
        return prioritized, sell_flags

    def _select_rebound(self) -> Optional[str]:
        if self.current_date is None or self.current_date.date() < self._rebound_start_trade_date:
            self._rebound_current_code = None
            self._rebound_holding_days = 0
            return None

        if self._rebound_current_code and self.has_position(self._rebound_current_code):
            self._rebound_holding_days += 1
        else:
            self._rebound_current_code = None
            self._rebound_holding_days = 0

        buy_candidates, sell_flags = self._rebound_scan()
        selected = self._rebound_current_code

        if selected:
            should_sell = (
                (selected in sell_flags and self._rebound_holding_days >= self._rebound_min_holding_days)
                or self._rebound_holding_days >= self._rebound_max_holding_days
            )
            if should_sell:
                selected = None
                self._rebound_holding_days = 0

        if buy_candidates:
            candidate = buy_candidates[0]
            if selected is None:
                selected = candidate
                self._rebound_holding_days = 0
            elif selected != candidate:
                old_i = THREE_HORSE_ETF_REBOUND_POOL.index(selected) if selected in THREE_HORSE_ETF_REBOUND_POOL else 999
                new_i = THREE_HORSE_ETF_REBOUND_POOL.index(candidate)
                if new_i < old_i:
                    selected = candidate
                    self._rebound_holding_days = 0

        self._rebound_current_code = selected
        return selected

    # ---------- trade ----------
    def _rebalance_to_targets(self, targets: Dict[str, float]) -> None:
        codes = sorted(set(targets.keys()) | set(self._portfolio.positions.keys()))

        # 先卖后买，释放现金
        for code in codes:
            price = self.get_price(code)
            if price <= 0:
                continue
            current_amount = self.get_position(code).amount if self.has_position(code) else 0
            current_value = current_amount * price
            target_value = float(targets.get(code, 0.0))
            if target_value < current_value - 100:
                sell_value = current_value - target_value
                amount = int(sell_value / price / 100) * 100
                if amount <= 0:
                    if target_value == 0 and current_amount > 0:
                        self.sell_all(code, price=price)
                    continue
                self.sell(code, price=price, amount=amount)

        for code in codes:
            price = self.get_price(code)
            if price <= 0:
                continue
            current_amount = self.get_position(code).amount if self.has_position(code) else 0
            current_value = current_amount * price
            target_value = float(targets.get(code, 0.0))
            if target_value > current_value + 100:
                buy_value = min(target_value - current_value, self.cash)
                amount = int(buy_value / price / 100) * 100
                if amount > 0:
                    self.buy(code, price=price, amount=amount, name=code)

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        rotation_code = self._select_rotation()
        rebound_code = self._select_rebound()
        self._last_rotation_code = rotation_code
        self._last_rebound_code = rebound_code

        rot_w, reb_w = self._effective_weights()
        tv = float(self.total_value)
        targets: Dict[str, float] = {}
        if rotation_code:
            targets[rotation_code] = targets.get(rotation_code, 0.0) + tv * rot_w
        if rebound_code:
            targets[rebound_code] = targets.get(rebound_code, 0.0) + tv * reb_w

        self._rebalance_to_targets(targets)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def on_end(self) -> None:
        self.log(
            f"回测结束：最后信号 rebound={self._last_rebound_code or '无'}, "
            f"rotation={self._last_rotation_code or '无'}"
        )
