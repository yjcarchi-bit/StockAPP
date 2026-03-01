"""
三驾马车 ETF 轮动策略（本地化版）
================================
将聚宽三驾马车 v10.2 中「策略3 ETF轮动」迁移到本地回测框架。

核心迁移点:
1. 近3日大跌过滤
2. 日内跌幅过滤（使用当日开收盘近似）
3. RSRS + 均线过滤
4. 成交量异常过滤
5. 加权线性回归动量打分（年化收益 * R²）
6. 单标的轮动调仓

说明:
- 原聚宽策略依赖分钟级数据与调度，本地框架是日频 `on_trading_day`。
- 本地实现以日频近似：日内跌幅检测改为 `close/open - 1`。
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase


THREE_HORSE_ETF_POOL = [
    "510180",  # 上证180ETF
    "513030",  # 德国DAX ETF
    "513100",  # 纳指ETF
    "513520",  # 日经225ETF
    "510410",  # 自然资源ETF
    "518880",  # 黄金ETF
    "501018",  # 南方原油LOF
    "159985",  # 豆粕ETF
    "511090",  # 30年期国债ETF
    "159915",  # 创业板ETF
    "588120",  # 科创100ETF
    "512480",  # 半导体ETF
    "159851",  # 金融科技ETF
    "513020",  # 港股科技ETF
    "159637",  # 新能源车龙头ETF
    "513630",  # 港股红利ETF
    "510050",  # 上证50ETF
]


class ThreeHorseETFRotationStrategy(StrategyBase):
    """
    三驾马车中的 ETF 轮动子策略。
    """

    display_name = "三驾马车ETF轮动"
    description = (
        "从聚宽三驾马车策略中迁移的ETF轮动子策略。"
        "先做近3日跌幅过滤、日内跌幅过滤，再做RSRS+均线过滤、成交量过滤，"
        "最后按加权回归动量得分排名并轮动到最优ETF。"
    )
    logic = [
        "1. 候选池先做近3日大跌过滤",
        "2. 使用日频 close/open 近似日内跌幅过滤",
        "3. RSRS阈值 + MA5/MA10组合过滤",
        "4. 成交量异常过滤（当日量/近N日均量）",
        "5. 加权线性回归动量得分 = 年化收益 * R²",
        "6. 持有排名第一ETF，不合格则空仓",
    ]
    suitable = "适合希望复现聚宽三马ETF轮动核心逻辑，并在日频环境中运行的场景"
    risk = "震荡行情可能频繁换仓；日频近似会与聚宽分钟级回测存在偏差"
    params_info = {
        "lookback_days": {
            "default": 25,
            "min": 15,
            "max": 60,
            "step": 5,
            "description": "动量计算回看天数",
            "type": "slider",
        },
        "min_score": {
            "default": 0.3,
            "min": 0.0,
            "max": 1.5,
            "step": 0.1,
            "description": "最小动量得分阈值",
            "type": "slider",
        },
        "max_score": {
            "default": 5.0,
            "min": 1.0,
            "max": 10.0,
            "step": 0.5,
            "description": "最大动量得分阈值",
            "type": "slider",
        },
        "recent_drop_threshold": {
            "default": 0.95,
            "min": 0.90,
            "max": 0.99,
            "step": 0.01,
            "description": "近3日任意单日涨跌比阈值（低于则排除）",
            "type": "slider",
        },
        "enable_day_stop_filter": {
            "default": True,
            "description": "启用日内跌幅过滤（使用日频近似）",
            "type": "switch",
        },
        "day_stoploss_limit": {
            "default": -0.03,
            "min": -0.10,
            "max": -0.01,
            "step": 0.01,
            "description": "日内跌幅阈值（close/open-1）",
            "type": "slider",
        },
        "use_rsrs_filter": {
            "default": True,
            "description": "启用RSRS + 均线过滤",
            "type": "switch",
        },
        "rsrs_days": {
            "default": 18,
            "min": 10,
            "max": 30,
            "step": 1,
            "description": "RSRS斜率计算窗口",
            "type": "slider",
        },
        "rsrs_lookback_days": {
            "default": 250,
            "min": 120,
            "max": 500,
            "step": 10,
            "description": "RSRS阈值回看天数",
            "type": "slider",
        },
        "rsrs_window": {
            "default": 20,
            "min": 10,
            "max": 40,
            "step": 1,
            "description": "RSRS滚动窗口长度",
            "type": "slider",
        },
        "rsrs_strong_threshold": {
            "default": 0.15,
            "min": 0.05,
            "max": 0.40,
            "step": 0.01,
            "description": "RSRS强势阈值",
            "type": "slider",
        },
        "rsrs_weak_threshold": {
            "default": 0.03,
            "min": 0.0,
            "max": 0.20,
            "step": 0.01,
            "description": "RSRS弱势阈值",
            "type": "slider",
        },
        "use_volume_filter": {
            "default": True,
            "description": "启用成交量异常过滤",
            "type": "switch",
        },
        "volume_lookback_days": {
            "default": 7,
            "min": 3,
            "max": 20,
            "step": 1,
            "description": "成交量均值回看天数",
            "type": "slider",
        },
        "volume_threshold": {
            "default": 2.0,
            "min": 1.2,
            "max": 5.0,
            "step": 0.1,
            "description": "成交量异常倍数阈值",
            "type": "slider",
        },
        "use_input_universe": {
            "default": True,
            "description": "优先使用回测传入ETF列表（否则按内置池）",
            "type": "switch",
        },
    }

    def __init__(self):
        super().__init__()
        self._lookback_days = 25
        self._min_score = 0.3
        self._max_score = 5.0
        self._recent_drop_threshold = 0.95

        self._enable_day_stop_filter = True
        self._day_stoploss_limit = -0.03

        self._use_rsrs_filter = True
        self._rsrs_days = 18
        self._rsrs_lookback_days = 250
        self._rsrs_window = 20
        self._rsrs_strong_threshold = 0.15
        self._rsrs_weak_threshold = 0.03

        self._use_volume_filter = True
        self._volume_lookback_days = 7
        self._volume_threshold = 2.0
        self._use_input_universe = True

        self._latest_scores: Dict[str, float] = {}
        self._latest_rank: List[str] = []

    def initialize(self) -> None:
        self._lookback_days = int(self.get_param("lookback_days", 25))
        self._min_score = float(self.get_param("min_score", 0.3))
        self._max_score = float(self.get_param("max_score", 5.0))
        self._recent_drop_threshold = float(self.get_param("recent_drop_threshold", 0.95))

        self._enable_day_stop_filter = bool(self.get_param("enable_day_stop_filter", True))
        self._day_stoploss_limit = float(self.get_param("day_stoploss_limit", -0.03))

        self._use_rsrs_filter = bool(self.get_param("use_rsrs_filter", True))
        self._rsrs_days = int(self.get_param("rsrs_days", 18))
        self._rsrs_lookback_days = int(self.get_param("rsrs_lookback_days", 250))
        self._rsrs_window = int(self.get_param("rsrs_window", 20))
        self._rsrs_strong_threshold = float(self.get_param("rsrs_strong_threshold", 0.15))
        self._rsrs_weak_threshold = float(self.get_param("rsrs_weak_threshold", 0.03))

        self._use_volume_filter = bool(self.get_param("use_volume_filter", True))
        self._volume_lookback_days = int(self.get_param("volume_lookback_days", 7))
        self._volume_threshold = float(self.get_param("volume_threshold", 2.0))
        self._use_input_universe = bool(self.get_param("use_input_universe", True))

        self._latest_scores = {}
        self._latest_rank = []

        self.log("初始化完成（三驾马车ETF轮动本地版）")

    def _candidate_pool(self) -> List[str]:
        data_codes = list(self._data.keys())
        if self._use_input_universe:
            return data_codes
        return [code for code in THREE_HORSE_ETF_POOL if code in self._data]

    def _calc_day_open_close_ratio(self, code: str) -> Optional[float]:
        df = self.get_history(code, 1, fields=["open", "close"])
        if df.empty:
            return None
        row = df.iloc[-1]
        open_price = float(row.get("open", 0))
        close_price = float(row.get("close", 0))
        if open_price <= 0:
            return None
        return close_price / open_price - 1

    def _passes_recent_drop(self, code: str) -> bool:
        prices = self.get_prices(code, 4, field="close")
        if len(prices) < 4:
            return False
        ratios = [
            prices[-1] / prices[-2] if prices[-2] > 0 else 0.0,
            prices[-2] / prices[-3] if prices[-3] > 0 else 0.0,
            prices[-3] / prices[-4] if prices[-4] > 0 else 0.0,
        ]
        return min(ratios) >= self._recent_drop_threshold

    def _calc_rsrs_slope(self, high: np.ndarray, low: np.ndarray, days: int) -> Optional[float]:
        if len(high) < days or len(low) < days:
            return None
        h = high[-days:]
        l = low[-days:]
        if np.std(l) == 0 or np.any(np.isnan(h)) or np.any(np.isnan(l)):
            return None
        try:
            return float(np.polyfit(l, h, 1)[0])
        except Exception:
            return None

    def _calc_rsrs_beta(self, high: np.ndarray, low: np.ndarray) -> Optional[float]:
        lookback = self._rsrs_lookback_days
        window = self._rsrs_window

        if len(high) < lookback or len(low) < lookback or window < 2:
            return None

        hh = high[-lookback:]
        ll = low[-lookback:]

        slope_list: List[float] = []
        for i in range(0, len(hh) - window + 1):
            h_win = hh[i:i + window]
            l_win = ll[i:i + window]

            if np.std(l_win) == 0:
                continue
            if np.any(np.isnan(h_win)) or np.any(np.isnan(l_win)):
                continue
            if np.any(np.isinf(h_win)) or np.any(np.isinf(l_win)):
                continue

            try:
                slope = float(np.polyfit(l_win, h_win, 1)[0])
            except Exception:
                continue
            slope_list.append(slope)

        if len(slope_list) < 2:
            return None

        mean_slope = float(np.mean(slope_list))
        std_slope = float(np.std(slope_list))
        return mean_slope - 2 * std_slope

    def _check_above_ma(self, prices: np.ndarray, days: int) -> bool:
        if len(prices) < days:
            return False
        return float(prices[-1]) >= float(np.mean(prices[-days:]))

    def _passes_rsrs(self, code: str) -> bool:
        if not self._use_rsrs_filter:
            return True

        min_bars = max(self._rsrs_lookback_days, self._rsrs_days, 10)
        df = self.get_history(code, min_bars, fields=["high", "low", "close"])
        if df.empty:
            return False

        high = df["high"].astype(float).values
        low = df["low"].astype(float).values
        close = df["close"].astype(float).values

        slope = self._calc_rsrs_slope(high, low, self._rsrs_days)
        beta = self._calc_rsrs_beta(high, low)
        if slope is None or beta is None:
            return False
        if slope <= beta:
            return False

        strength = 0.0 if beta == 0 else (slope - beta) / abs(beta)
        above_ma5 = self._check_above_ma(close, 5)
        above_ma10 = self._check_above_ma(close, 10)

        if strength > self._rsrs_strong_threshold:
            return True
        if strength > self._rsrs_weak_threshold and above_ma5:
            return True
        if above_ma10:
            return True
        return False

    def _passes_volume(self, code: str) -> bool:
        if not self._use_volume_filter:
            return True

        bars_needed = self._volume_lookback_days + 1
        df = self.get_history(code, bars_needed, fields=["volume"])
        if df.empty or len(df) < bars_needed:
            return False

        volumes = df["volume"].astype(float).values
        current_volume = float(volumes[-1])
        avg_volume = float(np.mean(volumes[:-1]))
        if avg_volume <= 0:
            return False

        ratio = current_volume / avg_volume
        return ratio <= self._volume_threshold

    def _calc_momentum_score(self, code: str) -> Optional[float]:
        prices = self.get_prices(code, self._lookback_days + 1, field="close")
        if len(prices) < self._lookback_days + 1:
            return None
        if np.any(prices <= 0):
            return None

        log_prices = np.log(prices)
        x = np.arange(len(log_prices))
        weights = np.linspace(1.0, 2.0, len(log_prices))

        try:
            slope, intercept = np.polyfit(x, log_prices, 1, w=weights)
        except Exception:
            return None

        annualized_return = math.exp(slope * 250) - 1
        y_pred = slope * x + intercept

        ss_res = float(np.sum(weights * (log_prices - y_pred) ** 2))
        ss_tot = float(np.sum(weights * (log_prices - np.mean(log_prices)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        return float(annualized_return * r2)

    def _rank_etfs(self) -> List[str]:
        candidates = self._candidate_pool()
        self._latest_scores = {}

        if not candidates:
            return []

        filtered: List[str] = []
        for code in candidates:
            if not self._passes_recent_drop(code):
                continue

            if self._enable_day_stop_filter:
                ratio = self._calc_day_open_close_ratio(code)
                if ratio is None or ratio <= self._day_stoploss_limit:
                    continue

            if not self._passes_rsrs(code):
                continue

            if not self._passes_volume(code):
                continue

            score = self._calc_momentum_score(code)
            if score is None:
                continue
            if score <= self._min_score or score >= self._max_score:
                continue

            self._latest_scores[code] = score
            filtered.append(code)

        filtered.sort(key=lambda c: self._latest_scores[c], reverse=True)
        self._latest_rank = filtered
        return filtered

    def _rebalance(self, rank_list: List[str]) -> None:
        current_holdings = [code for code in self._portfolio.positions.keys() if self.has_position(code)]
        target = rank_list[0] if rank_list else None

        if target is None:
            for code in current_holdings:
                price = self.get_price(code)
                if price > 0:
                    self.sell_all(code, price)
            return

        for code in current_holdings:
            if code != target:
                price = self.get_price(code)
                if price > 0:
                    self.sell_all(code, price)

        if self.has_position(target):
            return

        price = self.get_price(target)
        if price <= 0:
            return

        amount = self.get_buy_amount(target, price=price, ratio=1.0)
        if amount <= 0:
            return

        self.buy(target, price=price, amount=amount, name=target)

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        rank_list = self._rank_etfs()
        self._rebalance(rank_list)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def on_end(self) -> None:
        top = self._latest_rank[:5]
        if not top:
            self.log("回测结束：最后一日无合格ETF")
            return
        summary = ", ".join([f"{code}:{self._latest_scores.get(code, 0):.4f}" for code in top])
        self.log(f"回测结束：最后排名 {summary}")
