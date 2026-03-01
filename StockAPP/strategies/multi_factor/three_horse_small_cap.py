"""
三驾马车小市值策略（本地化增强版）
==================================
在原本本地近似版基础上，补齐了更多聚宽原版交易节奏：
- 周频调仓（默认周二）
- 1月/4月空仓期切换防御ETF
- 动态持股数（参考指数MA偏离）
- 顶背离冻结窗口（近N日触发则暂停调仓）
- 个股止损 + 市场级止损
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase

try:
    import tushare as ts
except Exception:  # pragma: no cover - 缺失依赖时走降级路径
    ts = None


class ThreeHorseSmallCapStrategy(StrategyBase):
    """
    三驾马车小市值策略的本地近似增强版。
    """

    display_name = "三驾马车小市值"
    description = (
        "本地化的小市值近似策略：在中证1000成分股中按规模代理因子与动量筛选，"
        "并补齐周频调仓、顶背离冻结、动态持股数与市场级止损等原版节奏。"
    )
    logic = [
        "1. 周频调仓（默认周二），非调仓日保持持仓",
        "2. 指数MACD顶背离进入冻结窗口，暂停调仓",
        "3. 根据指数与MA10偏离动态调整持股数（3~6）",
        "4. 按规模代理因子 + 动量选股",
        "5. 个股止损/止盈与市场级止损风控",
    ]
    suitable = "适合希望在本地尽量贴近三马原版小市值交易节奏的场景"
    risk = "仍缺少聚宽财务面与分钟级行为，收益曲线只能近似贴合"
    params_info = {
        "xsz_version": {
            "default": "v3",
            "description": "小市值策略版本（v1/v2/v3）",
            "type": "text",
        },
        "stock_num": {
            "default": 5,
            "min": 3,
            "max": 10,
            "step": 1,
            "description": "默认目标持仓股票数",
            "type": "slider",
        },
        "lookback_days": {
            "default": 20,
            "min": 10,
            "max": 60,
            "step": 5,
            "description": "因子计算回看天数",
            "type": "slider",
        },
        "min_history_days": {
            "default": 80,
            "min": 40,
            "max": 260,
            "step": 10,
            "description": "最小历史数据要求",
            "type": "slider",
        },
        "min_momentum": {
            "default": -0.05,
            "min": -0.20,
            "max": 0.20,
            "step": 0.01,
            "description": "最小动量阈值",
            "type": "slider",
        },
        "max_volatility": {
            "default": 0.08,
            "min": 0.03,
            "max": 0.20,
            "step": 0.01,
            "description": "最大波动率阈值",
            "type": "slider",
        },
        "rebalance_weekly": {
            "default": True,
            "description": "启用周频调仓（贴近原版）",
            "type": "switch",
        },
        "rebalance_weekday": {
            "default": 2,
            "min": 1,
            "max": 5,
            "step": 1,
            "description": "周频调仓日（1=周一,2=周二...）",
            "type": "slider",
        },
        "enable_dynamic_stock_num": {
            "default": True,
            "description": "启用动态持股数（3~6）",
            "type": "switch",
        },
        "dbl_control": {
            "default": True,
            "description": "启用指数顶背离冻结窗口",
            "type": "switch",
        },
        "check_dbl_days": {
            "default": 10,
            "min": 3,
            "max": 20,
            "step": 1,
            "description": "顶背离冻结窗口天数",
            "type": "slider",
        },
        "stoploss_strategy": {
            "default": 3,
            "min": 1,
            "max": 3,
            "step": 1,
            "description": "止损策略 1=个股 2=市场 3=联合",
            "type": "slider",
        },
        "stoploss_limit": {
            "default": 0.09,
            "min": 0.03,
            "max": 0.20,
            "step": 0.01,
            "description": "个股固定止损比例",
            "type": "slider",
        },
        "market_stoploss": {
            "default": 0.05,
            "min": 0.02,
            "max": 0.12,
            "step": 0.01,
            "description": "市场级止损阈值",
            "type": "slider",
        },
        "no_buy_after_days": {
            "default": 3,
            "min": 1,
            "max": 10,
            "step": 1,
            "description": "止损后禁买天数",
            "type": "slider",
        },
        "use_defense_etf": {
            "default": True,
            "description": "无目标时启用防御ETF",
            "type": "switch",
        },
        "auto_stock_limit": {
            "default": 300,
            "min": 50,
            "max": 1000,
            "step": 50,
            "description": "自动加载股票池上限（仅在未手动传入股票代码时生效）",
            "type": "slider",
        },
        "min_trade_value": {
            "default": 1000,
            "min": 100,
            "max": 5000,
            "step": 100,
            "description": "最小调仓金额，避免过度碎单",
            "type": "slider",
        },
    }

    def __init__(self):
        super().__init__()
        self._stock_num = 5
        self._lookback_days = 20
        self._min_history_days = 80
        self._min_momentum = -0.05
        self._max_volatility = 0.08
        self._stoploss_limit = 0.09
        self._market_stoploss = 0.05
        self._stoploss_strategy = 3
        self._no_buy_after_days = 3
        self._use_defense_etf = True
        self._defense_etf = "512800"
        self._min_trade_value = 1000.0

        self._rebalance_weekly = True
        self._rebalance_weekday = 1  # python weekday: 周二=1
        self._enable_dynamic_stock_num = True
        self._dbl_control = True
        self._check_dbl_days = 10
        self._pause_months: Set[int] = {1, 4}
        # 原版小市值以 399101 作为核心市场信号指数（动态持仓数 + 顶背离）
        self._index_code = "399101"
        self._exclude_codes: Set[str] = {"000300", "000852", "399101"}
        self._fixed_universe_codes: Optional[Set[str]] = None

        self._cooldown_days: Dict[str, int] = {}
        self._last_targets: List[str] = []
        self._dbl_signals: List[int] = []
        self._last_select_was_rebalance = False
        self._xsz_version = "v3"
        self._warned_financial_fallback = False
        self._warned_no_tushare = False
        self._warned_no_industry = False

        self._pro = None
        self._tushare_enabled = False
        self._tushare_token = ""
        self._industry_cache: Dict[str, str] = {}
        self._financial_cache: Dict[str, Dict[str, float]] = {}
        self._audit_cache: Dict[str, bool] = {}
        self._dividend_cache: Dict[str, float] = {}

        self._yesterday_hl_list: List[str] = []
        self._dbl_bootstrapped = False

    def initialize(self) -> None:
        raw_version = str(self.get_param("xsz_version", "v3")).strip().lower()
        self._xsz_version = raw_version if raw_version in {"v1", "v2", "v3"} else "v3"
        self._stock_num = int(self.get_param("stock_num", 5))
        self._lookback_days = int(self.get_param("lookback_days", 20))
        self._min_history_days = int(self.get_param("min_history_days", 80))
        self._min_momentum = float(self.get_param("min_momentum", -0.05))
        self._max_volatility = float(self.get_param("max_volatility", 0.08))
        self._stoploss_limit = float(self.get_param("stoploss_limit", 0.09))
        self._market_stoploss = float(self.get_param("market_stoploss", 0.05))
        self._stoploss_strategy = int(self.get_param("stoploss_strategy", 3))
        self._no_buy_after_days = int(self.get_param("no_buy_after_days", 3))
        self._use_defense_etf = bool(self.get_param("use_defense_etf", True))
        self._min_trade_value = float(self.get_param("min_trade_value", 1000))

        self._rebalance_weekly = bool(self.get_param("rebalance_weekly", True))
        weekday_raw = int(self.get_param("rebalance_weekday", 2))
        self._rebalance_weekday = max(0, min(4, weekday_raw - 1))
        self._enable_dynamic_stock_num = bool(self.get_param("enable_dynamic_stock_num", True))
        self._dbl_control = bool(self.get_param("dbl_control", True))
        self._check_dbl_days = max(1, int(self.get_param("check_dbl_days", 10)))

        self._index_code = str(self.get_param("index_code", "399101")).strip() or "399101"
        self._exclude_codes = {"000300", "000852", "399101", self._index_code}
        self._fixed_universe_codes = None
        raw_universe = self.get_param("universe_codes", None)
        if isinstance(raw_universe, (list, tuple, set)):
            normalized = {
                str(code).strip().zfill(6)
                for code in raw_universe
                if str(code).strip()
            }
            if normalized:
                self._fixed_universe_codes = normalized

        self._cooldown_days = {}
        self._last_targets = []
        self._dbl_signals = []
        self._last_select_was_rebalance = False
        self._yesterday_hl_list = []
        self._dbl_bootstrapped = False
        self._warned_financial_fallback = False
        self._warned_no_tushare = False
        self._warned_no_industry = False
        self._industry_cache = {}
        self._financial_cache = {}
        self._audit_cache = {}
        self._dividend_cache = {}
        self._pro = None
        self._tushare_token = self._resolve_tushare_token()
        self._tushare_enabled = bool(ts is not None and self._tushare_token)
        self.log("初始化完成（三驾马车小市值本地增强版）")

    @staticmethod
    def _is_stock_code(code: str) -> bool:
        if not code:
            return False
        c = str(code).strip()
        return len(c) == 6 and c[0] in {"0", "3", "6"}

    def _stock_universe(self) -> List[str]:
        res: List[str] = []
        for code in self._data.keys():
            if not self._is_stock_code(code):
                continue
            if code in self._exclude_codes:
                continue
            if self._fixed_universe_codes is not None and code not in self._fixed_universe_codes:
                continue
            res.append(code)
        return res

    def _is_rebalance_day(self) -> bool:
        if self.current_date is None:
            return True
        if not self._rebalance_weekly:
            return True
        return self.current_date.weekday() == self._rebalance_weekday

    def _update_cooldown(self) -> None:
        for code in list(self._cooldown_days.keys()):
            self._cooldown_days[code] -= 1
            if self._cooldown_days[code] <= 0:
                del self._cooldown_days[code]

    def _resolve_tushare_token(self) -> str:
        env_token = os.getenv("TUSHARE_TOKEN", "").strip()
        if env_token:
            return env_token

        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env",
        )
        if not os.path.exists(env_path):
            return ""

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "TUSHARE_TOKEN":
                        return value.strip().strip('"').strip("'")
        except Exception:
            return ""
        return ""

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            num = float(value)
            if np.isnan(num):
                return 0.0
            return num
        except Exception:
            return 0.0

    @staticmethod
    def _to_ts_code(code: str) -> str:
        c = str(code).strip().zfill(6)
        suffix = "SH" if c.startswith(("5", "6", "9")) else "SZ"
        return f"{c}.{suffix}"

    def _get_pro(self):
        if not self._tushare_enabled:
            return None
        if self._pro is not None:
            return self._pro
        if ts is None:
            self._tushare_enabled = False
            return None
        try:
            ts.set_token(self._tushare_token)
            self._pro = ts.pro_api(self._tushare_token)
            return self._pro
        except Exception:
            self._tushare_enabled = False
            return None

    def _safe_query(self, func_name: str, **kwargs: Any):
        pro = self._get_pro()
        if pro is None:
            return None
        try:
            func = getattr(pro, func_name)
            df = func(**kwargs)
            return df
        except Exception:
            return None

    def _warn_no_tushare(self, message: str) -> None:
        if self._warned_no_tushare:
            return
        self._warned_no_tushare = True
        self.log(message)

    def _is_limit_up(self, code: str, prev_close: float, close: float) -> bool:
        if prev_close <= 0 or close <= 0:
            return False
        limit_ratio = 1.195 if code.startswith(("30", "68")) else 1.095
        return close >= prev_close * limit_ratio

    def _is_sealed_limit_up(self, code: str, prev_close: float, close: float, high: float) -> bool:
        if not self._is_limit_up(code, prev_close, close):
            return False
        if high <= 0:
            return False
        return close >= high * 0.999

    def _stock_scope_from_tracked_codes(self, tracked_codes: Optional[List[str]]) -> List[str]:
        if tracked_codes is None:
            return [
                c
                for c in list(self._portfolio.positions.keys())
                if self._is_stock_code(c) and c not in self._exclude_codes
            ]
        return [
            c
            for c in tracked_codes
            if self._is_stock_code(c) and c not in self._exclude_codes and self.has_position(c)
        ]

    def prepare_daily_state(self, tracked_codes: Optional[List[str]] = None) -> None:
        holdings = self._stock_scope_from_tracked_codes(tracked_codes)
        yesterday_hl: List[str] = []
        for code in holdings:
            hist = self.get_history(code, 3, fields=["close", "high"])
            if hist.empty or len(hist) < 3:
                continue
            prev2_close = float(hist["close"].iloc[-3])
            y_close = float(hist["close"].iloc[-2])
            y_high = float(hist["high"].iloc[-2]) if "high" in hist.columns else 0.0
            if self._is_sealed_limit_up(code, prev2_close, y_close, y_high):
                yesterday_hl.append(code)
        self._yesterday_hl_list = yesterday_hl

    def check_limit_up_break(self, tracked_codes: Optional[List[str]] = None) -> List[str]:
        sold_codes: List[str] = []
        candidates = self._yesterday_hl_list[:]
        if tracked_codes is not None:
            scoped = set(tracked_codes)
            candidates = [c for c in candidates if c in scoped]

        for code in candidates:
            if not self.has_position(code):
                continue
            hist = self.get_history(code, 2, fields=["close", "high"])
            if hist.empty or len(hist) < 2:
                continue
            y_close = float(hist["close"].iloc[-2])
            t_close = float(hist["close"].iloc[-1])
            t_high = float(hist["high"].iloc[-1]) if "high" in hist.columns else 0.0
            still_sealed = self._is_sealed_limit_up(code, y_close, t_close, t_high)
            if still_sealed:
                continue
            if self.sell_all(code, price=t_close):
                sold_codes.append(code)
                self._remove_from_last_targets(code)
                self._cooldown_days[code] = self._no_buy_after_days
                self.log(f"昨日涨停开板卖出: {code} (日频近似判定)")
        return sold_codes

    def close_account_if_pause_month(self, tracked_codes: Optional[List[str]] = None) -> bool:
        if self.current_date is None or self.current_date.month not in self._pause_months:
            return False

        holdings = self._stock_scope_from_tracked_codes(tracked_codes)
        changed = False
        for code in holdings:
            cp = self.get_price(code)
            if cp <= 0:
                continue
            if self.sell_all(code, price=cp):
                changed = True
                self._remove_from_last_targets(code)
                self._cooldown_days[code] = self._no_buy_after_days

        if tracked_codes is None and self._use_defense_etf and self._defense_etf in self._data:
            self._order_target_value(self._defense_etf, self.total_value)
            changed = True

        if changed:
            self.log("空仓月触发 close_account，已清理非防守持仓")
        return changed

    @staticmethod
    def _ema(values: np.ndarray, span: int) -> np.ndarray:
        if len(values) == 0:
            return np.array([])
        alpha = 2.0 / (span + 1.0)
        out = np.empty(len(values), dtype=float)
        out[0] = float(values[0])
        for i in range(1, len(values)):
            out[i] = alpha * float(values[i]) + (1.0 - alpha) * out[i - 1]
        return out

    def _macd(self, close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        dif = self._ema(close, 12) - self._ema(close, 26)
        dea = self._ema(dif, 9)
        macd = (dif - dea) * 2.0
        return dif, dea, macd

    def _detect_top_divergence_with_close(self, close: np.ndarray) -> bool:
        if len(close) < 80 or np.any(close <= 0):
            return False

        dif, _, macd = self._macd(close.astype(float))
        if len(macd) < 30:
            return False

        dead_cross = (macd < 0) & (np.r_[0.0, macd[:-1]] >= 0)
        idx = np.where(dead_cross)[0]
        if len(idx) < 2:
            return False

        key2, key1 = int(idx[-2]), int(idx[-1])
        if key2 <= 0 or key1 <= 0:
            return False

        price_cond = float(close[key2]) < float(close[key1])
        dif_cond = float(dif[key2]) > float(dif[key1]) > 0.0
        macd_cond = len(macd) >= 2 and float(macd[-2]) > 0.0 > float(macd[-1])
        trend_cond = False
        if len(dif) >= 20:
            trend_cond = float(np.mean(dif[-10:])) < float(np.mean(dif[-20:-10]))

        return bool(price_cond and dif_cond and macd_cond and trend_cond)

    def _detect_top_divergence(self) -> bool:
        close = self.get_prices(self._index_code, 260, field="close")
        return self._detect_top_divergence_with_close(close)

    def _bootstrap_dbl_signals(self) -> None:
        if not self._dbl_control or self._dbl_bootstrapped:
            return

        window = max(1, self._check_dbl_days)
        history_days = 260 + window + 2
        close = self.get_prices(self._index_code, history_days, field="close")
        if len(close) < 80:
            self._dbl_signals = []
            self._dbl_bootstrapped = True
            return

        seeded: List[int] = []
        for offset in range(window, 0, -1):
            if len(close) <= offset:
                continue
            hist = close[:-offset]
            if len(hist) < 80:
                continue
            seeded.append(1 if self._detect_top_divergence_with_close(hist) else 0)

        self._dbl_signals = seeded[-120:]
        self._dbl_bootstrapped = True

    def _liquidate_non_limit_up_positions_for_dbl(self, tracked_codes: Optional[List[str]] = None) -> List[str]:
        sold_codes: List[str] = []
        holdings = self._stock_scope_from_tracked_codes(tracked_codes)
        for code in holdings:
            if not self.has_position(code):
                continue
            hist = self.get_history(code, 2, fields=["close", "high"])
            if hist.empty or len(hist) < 2:
                continue
            y_close = float(hist["close"].iloc[-2])
            t_close = float(hist["close"].iloc[-1])
            t_high = float(hist["high"].iloc[-1]) if "high" in hist.columns else 0.0
            is_limit = self._is_sealed_limit_up(code, y_close, t_close, t_high)
            if is_limit:
                continue
            if self.sell_all(code, price=t_close):
                sold_codes.append(code)
                self._remove_from_last_targets(code)
                self._cooldown_days[code] = self._no_buy_after_days
        return sold_codes

    def _update_dbl_signal(self) -> int:
        if not self._dbl_control:
            return 0
        self._bootstrap_dbl_signals()
        signal = 1 if self._detect_top_divergence() else 0
        self._dbl_signals.append(signal)
        if len(self._dbl_signals) > 120:
            self._dbl_signals = self._dbl_signals[-120:]
        return signal

    def run_dbl_control_step(self, tracked_codes: Optional[List[str]] = None) -> bool:
        self._update_cooldown()
        signal = self._update_dbl_signal()
        if signal != 1:
            return False
        sold_codes = self._liquidate_non_limit_up_positions_for_dbl(tracked_codes=tracked_codes)
        if sold_codes:
            preview = ",".join(sold_codes[:5])
            self.log(f"DBL触发清仓(非涨停): {preview}")
        return True

    def _frozen_by_dbl(self) -> bool:
        if not self._dbl_control:
            return False
        window = max(1, self._check_dbl_days)
        return 1 in self._dbl_signals[-window:]

    def _calc_dynamic_stock_num(self) -> int:
        if not self._enable_dynamic_stock_num:
            return int(self._stock_num)
        close = self.get_prices(self._index_code, 12, field="close")
        if len(close) < 10 or np.any(close <= 0):
            return int(self._stock_num)
        ma10 = float(np.mean(close[-10:]))
        diff = float(close[-1] - ma10)
        if diff >= 200:
            n = 3
        elif diff >= -200:
            n = 4
        elif diff >= -500:
            n = 5
        else:
            n = 6
        return max(3, min(10, n))

    def _calc_factor(self, code: str) -> Optional[Dict[str, float]]:
        need_bars = max(self._min_history_days, self._lookback_days + 1)
        df = self.get_history(code, need_bars, fields=["close", "volume", "amount"])
        if df.empty or len(df) < need_bars:
            return None

        close = df["close"].astype(float).values
        if np.any(close <= 0):
            return None

        volume = df["volume"].astype(float).values if "volume" in df.columns else np.zeros(len(close))
        if "amount" in df.columns:
            amount = df["amount"].astype(float).values
        else:
            amount = close * volume

        lb = self._lookback_days
        momentum = float(close[-1] / close[-(lb + 1)] - 1) if len(close) >= lb + 1 else -999.0
        log_ret = np.diff(np.log(close[-(lb + 1):])) if len(close) >= lb + 1 else np.array([])
        volatility = float(np.std(log_ret)) if len(log_ret) > 0 else 1.0
        liquidity = float(np.mean(amount[-lb:])) if len(amount) >= lb else float(np.mean(amount))

        return {
            "momentum": momentum,
            "volatility": volatility,
            "liquidity": liquidity,
        }

    def _get_industry(self, code: str) -> str:
        cached = self._industry_cache.get(code)
        if cached is not None:
            return cached

        if not self._tushare_enabled:
            self._industry_cache[code] = ""
            return ""

        ts_code = self._to_ts_code(code)
        df = self._safe_query("stock_basic", ts_code=ts_code, fields="ts_code,industry")
        if df is None or getattr(df, "empty", True):
            self._industry_cache[code] = ""
            return ""

        value = str(df.iloc[0].get("industry", "")).strip()
        self._industry_cache[code] = value
        return value

    def _get_financial_snapshot(self, code: str) -> Dict[str, float]:
        date_key = self.current_date.strftime("%Y%m%d") if self.current_date else "00000000"
        cache_key = f"{code}_{date_key[:6]}"
        cached = self._financial_cache.get(cache_key)
        if cached is not None:
            return cached

        snapshot = {
            "roe": 0.0,
            "roa": 0.0,
            "netprofit_yoy": 0.0,
            "profit_dedt": 0.0,
            "n_cashflow_act": 0.0,
        }
        if not self._tushare_enabled:
            self._financial_cache[cache_key] = snapshot
            return snapshot

        ts_code = self._to_ts_code(code)
        fina_indicator = self._safe_query(
            "fina_indicator",
            ts_code=ts_code,
            end_date=date_key,
            limit=1,
            fields="ts_code,end_date,roe,roa,netprofit_yoy,profit_dedt",
        )
        if fina_indicator is not None and not fina_indicator.empty:
            row = fina_indicator.iloc[0]
            snapshot["roe"] = self._to_float(row.get("roe", 0.0))
            snapshot["roa"] = self._to_float(row.get("roa", 0.0))
            snapshot["netprofit_yoy"] = self._to_float(row.get("netprofit_yoy", 0.0))
            snapshot["profit_dedt"] = self._to_float(row.get("profit_dedt", 0.0))

        cashflow = self._safe_query(
            "cashflow",
            ts_code=ts_code,
            end_date=date_key,
            limit=1,
            fields="ts_code,end_date,n_cashflow_act",
        )
        if cashflow is not None and not cashflow.empty:
            snapshot["n_cashflow_act"] = self._to_float(cashflow.iloc[0].get("n_cashflow_act", 0.0))

        self._financial_cache[cache_key] = snapshot
        return snapshot

    def _passes_v2_financial_threshold(self, code: str) -> bool:
        fin = self._get_financial_snapshot(code)
        if not self._tushare_enabled:
            return True
        return (
            fin["roe"] > 0.0
            and fin["roa"] > 0.0
            and fin["netprofit_yoy"] > -20.0
            and fin["profit_dedt"] >= 0.0
        )

    def _passes_audit_filter(self, code: str) -> bool:
        date_key = self.current_date.strftime("%Y%m%d") if self.current_date else "00000000"
        cache_key = f"{code}_{date_key[:4]}"
        cached = self._audit_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self._tushare_enabled:
            self._audit_cache[cache_key] = True
            return True

        ts_code = self._to_ts_code(code)
        df = self._safe_query(
            "fina_audit",
            ts_code=ts_code,
            end_date=date_key,
            limit=3,
            fields="ts_code,end_date,audit_result,audit_opinion",
        )
        if df is None or df.empty:
            self._audit_cache[cache_key] = True
            return True

        bad_tokens = ("保留", "否定", "无法表示", "拒绝")
        passed = True
        for _, row in df.iterrows():
            text = f"{row.get('audit_result', '')}{row.get('audit_opinion', '')}"
            if any(token in str(text) for token in bad_tokens):
                passed = False
                break
        self._audit_cache[cache_key] = passed
        return passed

    def _dividend_score(self, code: str) -> float:
        date_key = self.current_date.strftime("%Y%m%d") if self.current_date else "00000000"
        cache_key = f"{code}_{date_key[:4]}"
        cached = self._dividend_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self._tushare_enabled:
            self._dividend_cache[cache_key] = 0.0
            return 0.0

        ts_code = self._to_ts_code(code)
        df = self._safe_query(
            "dividend",
            ts_code=ts_code,
            end_date=date_key,
            limit=5,
            fields="ts_code,end_date,div_proc,cash_div_tax",
        )
        if df is None or df.empty:
            self._dividend_cache[cache_key] = 0.0
            return 0.0

        score = 0.0
        for _, row in df.iterrows():
            score += max(0.0, self._to_float(row.get("cash_div_tax", 0.0)))
        self._dividend_cache[cache_key] = score
        return score

    def _build_base_scored_pool(self) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []
        for code in self._stock_universe():
            if code in self._cooldown_days:
                continue
            fac = self._calc_factor(code)
            if fac is None:
                continue
            if fac["momentum"] < self._min_momentum:
                continue
            if fac["volatility"] > self._max_volatility:
                continue
            scored.append({"code": code, **fac, "price": self.get_price(code)})
        scored.sort(key=lambda x: (x["liquidity"], -x["momentum"]))
        return scored

    def _select_v1_targets(self, scored: List[Dict[str, Any]], target_num: int) -> List[str]:
        if not scored:
            return []
        selected: List[str] = []
        used_industries: Set[str] = set()
        industry_available = False
        for item in scored:
            code = str(item["code"])
            industry = self._get_industry(code)
            if industry:
                industry_available = True
            key = industry or f"UNK_{code}"
            if key in used_industries:
                continue
            selected.append(code)
            used_industries.add(key)
            if len(selected) >= target_num:
                return selected

        if not industry_available and not self._warned_no_industry:
            self._warned_no_industry = True
            self.log("v1行业分散降级：行业数据不可用，改用纯排序选股")

        for item in scored:
            code = str(item["code"])
            if code in selected:
                continue
            selected.append(code)
            if len(selected) >= target_num:
                break
        return selected

    def _select_v2_targets(self, scored: List[Dict[str, Any]], target_num: int) -> List[str]:
        if not scored:
            return []

        if not self._tushare_enabled:
            if not self._warned_financial_fallback:
                self._warned_financial_fallback = True
                self.log("v2财务过滤降级：Tushare不可用，回退到价格/量能近似")
            return [str(x["code"]) for x in scored[:target_num]]

        filtered: List[str] = []
        top_pool = scored[: max(target_num * 8, 40)]
        for item in top_pool:
            code = str(item["code"])
            price = float(item.get("price", 0.0))
            if price <= 0 or price > 50:
                continue
            if not self._passes_v2_financial_threshold(code):
                continue
            filtered.append(code)
            if len(filtered) >= target_num:
                break

        if len(filtered) < target_num:
            for item in top_pool:
                code = str(item["code"])
                if code in filtered:
                    continue
                filtered.append(code)
                if len(filtered) >= target_num:
                    break
        return filtered

    def _select_v3_targets(self, scored: List[Dict[str, Any]], target_num: int) -> List[str]:
        if not scored:
            return []

        if not self._tushare_enabled:
            if not self._warned_financial_fallback:
                self._warned_financial_fallback = True
                self.log("v3审计/分红过滤降级：Tushare不可用，回退到价格/量能近似")
            return [str(x["code"]) for x in scored[:target_num]]

        top_pool = scored[: max(target_num * 10, 60)]
        passed: List[Tuple[str, float, float]] = []
        for item in top_pool:
            code = str(item["code"])
            if not self._passes_v2_financial_threshold(code):
                continue
            if not self._passes_audit_filter(code):
                continue
            div_score = self._dividend_score(code)
            passed.append((code, div_score, float(item["liquidity"])))

        passed.sort(key=lambda x: (-x[1], x[2]))
        selected = [x[0] for x in passed[:target_num]]

        if len(selected) < target_num:
            # 分红样本不足时，按“小市值代理（流动性）”补齐。
            for item in top_pool:
                code = str(item["code"])
                if code in selected:
                    continue
                if not self._passes_audit_filter(code):
                    continue
                selected.append(code)
                if len(selected) >= target_num:
                    break
        return selected

    def _market_stoploss_triggered(self) -> bool:
        pool = self._stock_universe()
        if not pool:
            return False
        down_list: List[float] = []
        for code in pool:
            df = self.get_history(code, 1, fields=["open", "close"])
            if df.empty:
                continue
            o = float(df["open"].iloc[-1]) if "open" in df.columns else 0.0
            c = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
            if o <= 0 or c <= 0:
                continue
            down_list.append(abs(c / o - 1.0))
        if not down_list:
            return False
        return float(np.mean(down_list)) >= self._market_stoploss

    def _remove_from_last_targets(self, code: str) -> None:
        if code in self._last_targets:
            self._last_targets = [c for c in self._last_targets if c != code]

    def _check_stoploss(self) -> None:
        stock_positions = [
            c for c in list(self._portfolio.positions.keys())
            if self._is_stock_code(c) and c not in self._exclude_codes
        ]

        if self._stoploss_strategy in {2, 3} and self._market_stoploss_triggered():
            for code in stock_positions:
                cp = self.get_price(code)
                if cp <= 0:
                    continue
                self.sell_all(code, price=cp)
                self._cooldown_days[code] = self._no_buy_after_days
                self._remove_from_last_targets(code)
            return

        if self._stoploss_strategy not in {1, 3}:
            return

        for code in stock_positions:
            pos = self.get_position(code)
            if pos.is_empty or pos.cost_price <= 0:
                continue
            current_price = self.get_price(code)
            if current_price <= 0:
                continue

            # 贴近原版：翻倍止盈
            if current_price >= pos.cost_price * 2:
                self.sell_all(code, price=current_price)
                self._remove_from_last_targets(code)
                continue

            if current_price < pos.cost_price * (1 - self._stoploss_limit):
                self.sell_all(code, price=current_price)
                self._cooldown_days[code] = self._no_buy_after_days
                self._remove_from_last_targets(code)

    def run_stoploss_step(self, tracked_codes: Optional[List[str]] = None) -> List[str]:
        if tracked_codes is None:
            before = set(self._portfolio.positions.keys())
            self._check_stoploss()
            after = set(self._portfolio.positions.keys())
            sold = sorted(c for c in before if c not in after)
            return sold

        stock_positions = self._stock_scope_from_tracked_codes(tracked_codes)
        sold_codes: List[str] = []
        if self._stoploss_strategy in {2, 3} and self._market_stoploss_triggered():
            for code in stock_positions:
                cp = self.get_price(code)
                if cp <= 0:
                    continue
                if self.sell_all(code, price=cp):
                    sold_codes.append(code)
                    self._cooldown_days[code] = self._no_buy_after_days
                    self._remove_from_last_targets(code)
            return sold_codes

        if self._stoploss_strategy not in {1, 3}:
            return sold_codes

        for code in stock_positions:
            pos = self.get_position(code)
            if pos.is_empty or pos.cost_price <= 0:
                continue
            current_price = self.get_price(code)
            if current_price <= 0:
                continue
            if current_price >= pos.cost_price * 2:
                if self.sell_all(code, price=current_price):
                    sold_codes.append(code)
                    self._remove_from_last_targets(code)
                continue
            if current_price < pos.cost_price * (1 - self._stoploss_limit):
                if self.sell_all(code, price=current_price):
                    sold_codes.append(code)
                    self._cooldown_days[code] = self._no_buy_after_days
                    self._remove_from_last_targets(code)
        return sold_codes

    def _select_targets(self) -> List[str]:
        self._last_select_was_rebalance = False

        if self.current_date is not None and self.current_date.month in self._pause_months:
            self._last_targets = []
            self._last_select_was_rebalance = True
            return []

        if not self._is_rebalance_day():
            return [c for c in self._last_targets if c not in self._cooldown_days]

        if self._frozen_by_dbl():
            return [c for c in self._last_targets if c not in self._cooldown_days]

        current_stock_num = self._calc_dynamic_stock_num()
        scored = self._build_base_scored_pool()

        if not scored:
            self._last_targets = []
            self._last_select_was_rebalance = True
            return []

        selected: List[str]
        if self._xsz_version == "v1":
            selected = self._select_v1_targets(scored, current_stock_num)
        elif self._xsz_version == "v2":
            selected = self._select_v2_targets(scored, current_stock_num)
        else:
            selected = self._select_v3_targets(scored, current_stock_num)

        self._last_targets = selected[:current_stock_num]
        self._last_select_was_rebalance = True
        return self._last_targets[:]

    def did_rebalance_select(self) -> bool:
        return self._last_select_was_rebalance

    def get_last_targets(self) -> List[str]:
        return self._last_targets[:]

    def _order_target_value(self, code: str, target_value: float) -> None:
        price = self.get_price(code)
        if price <= 0:
            return

        current_amount = self.get_position(code).amount if self.has_position(code) else 0
        current_value = current_amount * price
        diff = target_value - current_value
        if abs(diff) < self._min_trade_value:
            return

        if diff > 0:
            buy_cash = min(diff, self.cash)
            amount = int(buy_cash / price / 100) * 100
            if amount > 0:
                self.buy(code, price=price, amount=amount, name=code)
            return

        sell_value = -diff
        amount = int(sell_value / price / 100) * 100
        if amount <= 0:
            if target_value <= 0 and current_amount > 0:
                self.sell_all(code, price=price)
            return
        self.sell(code, price=price, amount=amount)

    def _rebalance(self, targets: List[str]) -> None:
        current_codes = [code for code in self._portfolio.positions.keys() if self.has_position(code)]
        stock_positions = [c for c in current_codes if self._is_stock_code(c) and c not in self._exclude_codes]
        has_defense = self.has_position(self._defense_etf)

        if not targets:
            for code in stock_positions:
                self._order_target_value(code, 0.0)
            if self._use_defense_etf and self._defense_etf in self._data:
                self._order_target_value(self._defense_etf, self.total_value)
            return

        if has_defense:
            self._order_target_value(self._defense_etf, 0.0)

        target_values: Dict[str, float] = {code: self.total_value / len(targets) for code in targets}
        all_codes = sorted(set(stock_positions) | set(target_values.keys()))
        for code in all_codes:
            self._order_target_value(code, float(target_values.get(code, 0.0)))

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        self.prepare_daily_state()
        self.run_dbl_control_step()
        self.run_stoploss_step()
        self.check_limit_up_break()

        if self.current_date is not None and self.current_date.month in self._pause_months:
            self._last_targets = []
            self._last_select_was_rebalance = True
            self.close_account_if_pause_month()
        else:
            targets = self._select_targets()
            if self._last_select_was_rebalance:
                self._rebalance(targets)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def on_end(self) -> None:
        preview = ",".join(self._last_targets[:5]) if self._last_targets else "无"
        self.log(f"回测结束：最后目标 {preview}")
