"""
三驾马车白马攻防策略（本地化增强版）
====================================
补齐贴近原版的月频调仓节奏，并在可用时启用财务因子筛选链路。
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase

try:
    import tushare as ts
    HAS_TUSHARE = True
except Exception:  # pragma: no cover - 环境缺少tushare时走降级分支
    ts = None
    HAS_TUSHARE = False


class ThreeHorseWhiteHorseStrategy(StrategyBase):
    """
    三驾马车白马攻防的本地近似增强版。
    """

    display_name = "三驾马车白马攻防"
    description = (
        "白马攻防策略本地增强版。根据市场温度在沪深300池内做差异化筛选，"
        "默认启用财务因子筛选（可降级为价格代理因子）并保留月频调仓节奏。"
    )
    logic = [
        "1. 计算市场温度（cold/warm/hot）",
        "2. 在沪深300池中做价格与基础过滤",
        "3. 优先按财务链路过滤（PB/现金流/盈利增速）",
        "4. 以ROE/ROA加权排序，并做动量过滤",
        "5. 财务链路不可用时，降级到价格代理因子",
        "6. 默认月频调仓（可切回日频）",
    ]
    suitable = "适合希望在本地尽量贴近三马原版白马子策略调仓节奏的场景"
    risk = "若Tushare token不可用会降级到价格代理因子，收益曲线可能偏离原版"
    params_info = {
        "holdings_num": {
            "default": 5,
            "min": 3,
            "max": 10,
            "step": 1,
            "description": "目标持仓数量",
            "type": "slider",
        },
        "price_max": {
            "default": 100.0,
            "min": 20.0,
            "max": 300.0,
            "step": 5.0,
            "description": "候选股票价格上限",
            "type": "slider",
        },
        "lookback_days": {
            "default": 25,
            "min": 10,
            "max": 60,
            "step": 5,
            "description": "动量过滤回看天数",
            "type": "slider",
        },
        "min_score": {
            "default": -1.0,
            "min": -3.0,
            "max": 1.0,
            "step": 0.1,
            "description": "动量得分下限",
            "type": "slider",
        },
        "max_score": {
            "default": 10.5,
            "min": 1.0,
            "max": 20.0,
            "step": 0.5,
            "description": "动量得分上限",
            "type": "slider",
        },
        "roe_weight": {
            "default": 10,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "代理ROE排序权重",
            "type": "slider",
        },
        "roa_weight": {
            "default": 6,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "代理ROA排序权重",
            "type": "slider",
        },
        "use_financial_filter": {
            "default": False,
            "description": "启用贴近原版的财务因子过滤（需可用Tushare token）",
            "type": "switch",
        },
        "financial_max_candidates": {
            "default": 120,
            "min": 20,
            "max": 300,
            "step": 10,
            "description": "财务筛选候选上限（按流动性预筛）",
            "type": "slider",
        },
        "rebalance_monthly": {
            "default": True,
            "description": "启用月频调仓（贴近原版）",
            "type": "switch",
        },
        "enable_daily_stoploss": {
            "default": False,
            "description": "启用日级固定止损（原版默认无）",
            "type": "switch",
        },
        "stoploss_limit": {
            "default": 0.10,
            "min": 0.03,
            "max": 0.20,
            "step": 0.01,
            "description": "固定止损比例",
            "type": "slider",
        },
        "use_defense_etf": {
            "default": False,
            "description": "无目标股票时是否持有防御ETF",
            "type": "switch",
        },
        "auto_stock_limit": {
            "default": 200,
            "min": 50,
            "max": 800,
            "step": 50,
            "description": "自动加载股票池上限（仅在未手动传入股票代码时生效）",
            "type": "slider",
        },
        "min_trade_value": {
            "default": 1000,
            "min": 100,
            "max": 5000,
            "step": 100,
            "description": "最小调仓金额",
            "type": "slider",
        },
    }

    def __init__(self):
        super().__init__()
        self._holdings_num = 5
        self._price_max = 100.0
        self._lookback_days = 25
        self._min_score = -1.0
        self._max_score = 10.5
        self._roe_weight = 10
        self._roa_weight = 6
        self._stoploss_limit = 0.10
        self._use_defense_etf = False
        self._defense_etf = "511010"
        self._min_trade_value = 1000.0

        self._rebalance_monthly = True
        self._enable_daily_stoploss = False
        self._index_code = "000300"
        self._exclude_codes: Set[str] = {"000300", "000852", "399101"}
        self._fixed_universe_codes: Optional[Set[str]] = None
        self._use_financial_filter = False
        self._financial_max_candidates = 120

        self._tushare_token = ""
        self._tushare_enabled = False
        self._pro = None
        self._financial_cache: Dict[str, Dict[str, float]] = {}

        self._market_temperature = "warm"
        self._last_targets: List[str] = []
        self._last_select_was_rebalance = False
        self._last_rebalance_month: Optional[Tuple[int, int]] = None

    def initialize(self) -> None:
        self._holdings_num = int(self.get_param("holdings_num", 5))
        self._price_max = float(self.get_param("price_max", 100.0))
        self._lookback_days = int(self.get_param("lookback_days", 25))
        self._min_score = float(self.get_param("min_score", -1.0))
        self._max_score = float(self.get_param("max_score", 10.5))
        self._roe_weight = float(self.get_param("roe_weight", 10))
        self._roa_weight = float(self.get_param("roa_weight", 6))
        self._use_financial_filter = bool(self.get_param("use_financial_filter", False))
        self._financial_max_candidates = max(20, int(self.get_param("financial_max_candidates", 120)))
        self._stoploss_limit = float(self.get_param("stoploss_limit", 0.10))
        self._use_defense_etf = bool(self.get_param("use_defense_etf", False))
        self._min_trade_value = float(self.get_param("min_trade_value", 1000))

        self._rebalance_monthly = bool(self.get_param("rebalance_monthly", True))
        self._enable_daily_stoploss = bool(self.get_param("enable_daily_stoploss", False))
        self._index_code = str(self.get_param("index_code", "000300")).strip() or "000300"
        self._exclude_codes = {"000300", "000852", "399101", self._index_code}
        self._fixed_universe_codes = self._parse_universe_codes(self.get_param("universe_codes", None))

        self._tushare_token = self._resolve_tushare_token()
        self._tushare_enabled = bool(self._use_financial_filter and HAS_TUSHARE and self._tushare_token)
        self._pro = None
        self._financial_cache = {}

        self._market_temperature = "warm"
        self._last_targets = []
        self._last_select_was_rebalance = False
        self._last_rebalance_month = None
        self.log("初始化完成（三驾马车白马攻防本地增强版）")

    @staticmethod
    def _parse_universe_codes(raw_value: Any) -> Optional[Set[str]]:
        if raw_value is None:
            return None
        codes: Set[str] = set()
        if isinstance(raw_value, (list, tuple, set)):
            for code in raw_value:
                text = str(code).strip()
                if text:
                    codes.add(text.zfill(6))
        elif isinstance(raw_value, str):
            for token in raw_value.replace(";", ",").split(","):
                text = token.strip()
                if text:
                    codes.add(text.zfill(6))
        return codes or None

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            num = float(value)
            if math.isnan(num):
                return 0.0
            return num
        except Exception:
            return 0.0

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
    def _to_ts_code(code: str) -> str:
        c = str(code).strip().zfill(6)
        suffix = "SH" if c.startswith(("5", "6", "9")) else "SZ"
        return f"{c}.{suffix}"

    def _get_pro(self):
        if not self._tushare_enabled:
            return None
        if self._pro is not None:
            return self._pro
        try:
            ts.set_token(self._tushare_token)
            self._pro = ts.pro_api(self._tushare_token)
            return self._pro
        except Exception:
            self._tushare_enabled = False
            return None

    def _safe_query(self, func_name: str, **kwargs: Any) -> pd.DataFrame:
        pro = self._get_pro()
        if pro is None:
            return pd.DataFrame()
        try:
            func = getattr(pro, func_name)
            df = func(**kwargs)
            if df is None:
                return pd.DataFrame()
            return df
        except Exception:
            return pd.DataFrame()

    def _get_financial_snapshot(self, code: str, date_key: str) -> Optional[Dict[str, float]]:
        cache_key = f"{code}_{date_key}"
        cached = self._financial_cache.get(cache_key)
        if cached is not None:
            return cached

        ts_code = self._to_ts_code(code)
        snapshot = {
            "pb_ratio": 0.0,
            "roe": 0.0,
            "roa": 0.0,
            "roic": 0.0,
            "profit_dedt": 0.0,
            "netprofit_yoy": 0.0,
            "n_cashflow_act": 0.0,
        }

        daily_basic = self._safe_query(
            "daily_basic",
            ts_code=ts_code,
            trade_date=date_key,
            fields="ts_code,pb",
        )
        if daily_basic.empty:
            daily_basic = self._safe_query(
                "daily_basic",
                ts_code=ts_code,
                end_date=date_key,
                limit=1,
                fields="ts_code,pb,trade_date",
            )
        if not daily_basic.empty:
            snapshot["pb_ratio"] = self._to_float(daily_basic.iloc[0].get("pb", 0.0))

        fina_indicator = self._safe_query(
            "fina_indicator",
            ts_code=ts_code,
            end_date=date_key,
            limit=1,
            fields="ts_code,end_date,roe,roa,roic,profit_dedt,netprofit_yoy",
        )
        if not fina_indicator.empty:
            row = fina_indicator.iloc[0]
            snapshot["roe"] = self._to_float(row.get("roe", 0.0))
            snapshot["roa"] = self._to_float(row.get("roa", 0.0))
            snapshot["roic"] = self._to_float(row.get("roic", 0.0))
            snapshot["profit_dedt"] = self._to_float(row.get("profit_dedt", 0.0))
            snapshot["netprofit_yoy"] = self._to_float(row.get("netprofit_yoy", 0.0))

        cashflow = self._safe_query(
            "cashflow",
            ts_code=ts_code,
            end_date=date_key,
            limit=1,
            fields="ts_code,end_date,n_cashflow_act",
        )
        if not cashflow.empty:
            snapshot["n_cashflow_act"] = self._to_float(cashflow.iloc[0].get("n_cashflow_act", 0.0))

        self._financial_cache[cache_key] = snapshot
        return snapshot

    @staticmethod
    def _is_stock_code(code: str) -> bool:
        c = str(code).strip()
        return len(c) == 6 and c[0] in {"0", "3", "6"}

    def _is_rebalance_day(self) -> bool:
        if self.current_date is None:
            return True
        if not self._rebalance_monthly:
            return True
        month_key = (self.current_date.year, self.current_date.month)
        return month_key != self._last_rebalance_month

    def _universe(self) -> List[str]:
        stocks = [c for c in self._data.keys() if self._is_stock_code(c) and c not in self._exclude_codes]
        filtered: List[str] = []
        for code in stocks:
            if self._fixed_universe_codes is not None and code not in self._fixed_universe_codes:
                continue
            if code.startswith(("30", "68", "8", "4")):
                continue
            price = self.get_price(code)
            if price <= 0 or price > self._price_max:
                continue
            filtered.append(code)
        return filtered

    def _calc_market_temperature(self, stock_pool: List[str]) -> str:
        # 贴近原版：直接基于沪深300指数近220日位置判断温度。
        close = self.get_prices(self._index_code, 220, field="close")
        if len(close) < 220 or np.any(close <= 0):
            return "warm"

        c_min = float(np.min(close))
        c_max = float(np.max(close))
        if c_max <= c_min:
            return "warm"

        market_height = (float(np.mean(close[-5:])) - c_min) / (c_max - c_min)
        last = float(close[-1])

        if market_height < 0.20:
            return "cold"
        if last <= c_min * 1.0001:
            return "cold"
        if market_height > 0.90:
            return "hot"
        if last >= c_max * 0.9999:
            return "hot"

        if len(close) >= 60:
            recent = close[-60:]
            recent_min = float(np.min(recent))
            if recent_min > 0 and float(np.max(recent)) / recent_min > 1.20:
                return "warm"
        return "warm"

    @staticmethod
    def _calc_max_drawdown(close: np.ndarray) -> float:
        if len(close) < 2:
            return 0.0
        peak = np.maximum.accumulate(close)
        dd = close / peak - 1.0
        return float(np.min(dd))

    def _calc_features(self, code: str) -> Optional[Dict[str, float]]:
        need = max(240, self._lookback_days + 1)
        df = self.get_history(code, need, fields=["close", "volume", "amount"])
        if df.empty or len(df) < need:
            return None

        close = df["close"].astype(float).values
        if np.any(close <= 0):
            return None

        amount = (
            df["amount"].astype(float).values
            if "amount" in df.columns
            else close * df["volume"].astype(float).values
        )

        m20 = float(close[-1] / close[-21] - 1) if len(close) >= 21 else 0.0
        m60 = float(close[-1] / close[-61] - 1) if len(close) >= 61 else 0.0
        m120 = float(close[-1] / close[-121] - 1) if len(close) >= 121 else 0.0
        log_ret60 = np.diff(np.log(close[-61:])) if len(close) >= 61 else np.array([])
        vol60 = float(np.std(log_ret60)) if len(log_ret60) > 0 else 1.0
        dd120 = self._calc_max_drawdown(close[-121:]) if len(close) >= 121 else -1.0
        liquidity = float(np.mean(amount[-20:])) if len(amount) >= 20 else float(np.mean(amount))

        return {
            "m20": m20,
            "m60": m60,
            "m120": m120,
            "vol60": vol60,
            "dd120": dd120,
            "liquidity": liquidity,
        }

    def _temperature_filter(self, feat: Dict[str, float]) -> bool:
        if self._market_temperature == "cold":
            return (
                feat["m120"] > -0.05
                and feat["m20"] > 0.0
                and feat["vol60"] < 0.035
                and feat["dd120"] > -0.25
            )
        if self._market_temperature == "hot":
            return (
                feat["m120"] > 0.08
                and feat["m20"] > 0.02
                and feat["vol60"] < 0.08
                and feat["dd120"] > -0.45
            )
        return (
            feat["m120"] > 0.0
            and feat["m20"] > -0.02
            and feat["vol60"] < 0.05
            and feat["dd120"] > -0.35
        )

    def _financial_filter(self, fin: Dict[str, float]) -> bool:
        pb = self._to_float(fin.get("pb_ratio", 0.0))
        n_cashflow_act = self._to_float(fin.get("n_cashflow_act", 0.0))
        profit_dedt = self._to_float(fin.get("profit_dedt", 0.0))
        roic = self._to_float(fin.get("roic", 0.0))
        roe = self._to_float(fin.get("roe", 0.0))
        netprofit_yoy = self._to_float(fin.get("netprofit_yoy", 0.0))

        inc_return_proxy = roic if roic > 0 else roe
        cash_profit_ratio = n_cashflow_act / profit_dedt if profit_dedt > 0 else 0.0

        if self._market_temperature == "cold":
            return (
                pb > 0.0
                and pb < 1.0
                and n_cashflow_act > 0.0
                and profit_dedt > 0.0
                and cash_profit_ratio > 2.0
                and inc_return_proxy > 1.5
                and netprofit_yoy > -15.0
            )
        if self._market_temperature == "warm":
            return (
                pb > 0.0
                and pb < 1.0
                and n_cashflow_act > 0.0
                and profit_dedt > 0.0
                and cash_profit_ratio > 1.0
                and inc_return_proxy > 2.0
                and netprofit_yoy > 0.0
            )
        return (
            pb > 3.0
            and n_cashflow_act > 0.0
            and profit_dedt > 0.0
            and cash_profit_ratio > 0.5
            and inc_return_proxy > 3.0
            and netprofit_yoy > 20.0
        )

    def _build_financial_candidates(self, features: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        if not self._tushare_enabled or not features:
            return []

        date_key = (
            self.current_date.strftime("%Y%m%d")
            if self.current_date is not None
            else datetime.now().strftime("%Y%m%d")
        )

        feature_items = [
            (code, feat)
            for code, feat in features.items()
            if self._temperature_filter(feat)
        ]
        if not feature_items:
            return []

        # 先按成交额做预筛，减少月调仓时财务接口调用次数。
        feature_items.sort(key=lambda x: x[1].get("liquidity", 0.0), reverse=True)
        max_n = max(10, int(self._financial_max_candidates))
        feature_items = feature_items[:max_n]

        candidates: List[Dict[str, Any]] = []
        for code, feat in feature_items:
            fin = self._get_financial_snapshot(code, date_key)
            if not fin:
                continue
            if not self._financial_filter(fin):
                continue
            candidates.append(
                {
                    "code": code,
                    "roe": self._to_float(fin.get("roe", 0.0)),
                    "roa": self._to_float(fin.get("roa", 0.0)),
                    "liquidity": float(feat.get("liquidity", 0.0)),
                }
            )
        return candidates

    def _moment_score(self, code: str) -> Optional[float]:
        close = self.get_prices(code, self._lookback_days, field="close")
        if len(close) < self._lookback_days or np.any(close <= 0):
            return None

        y = np.log(close)
        x = np.arange(len(y))
        w = np.linspace(1, 2, len(y))
        try:
            slope, intercept = np.polyfit(x, y, 1, w=w)
        except Exception:
            return None

        annualized = math.exp(slope * 250) - 1
        residual = y - (slope * x + intercept)
        denom = float(np.sum(w * (y - np.mean(y)) ** 2))
        if denom <= 0:
            return None
        r2 = 1 - float(np.sum(w * residual ** 2)) / denom
        return float(annualized * r2)

    def _select_targets(self) -> List[str]:
        self._last_select_was_rebalance = False
        if not self._is_rebalance_day():
            return self._last_targets[:]

        pool = self._universe()
        if not pool:
            self._last_targets = []
            self._last_select_was_rebalance = True
            return []

        self._market_temperature = self._calc_market_temperature(pool)

        features: Dict[str, Dict[str, float]] = {}
        for code in pool:
            feat = self._calc_features(code)
            if feat is None:
                continue
            features[code] = feat

        candidates: List[Dict[str, Any]] = []
        use_financial_rank = False
        if self._use_financial_filter:
            candidates = self._build_financial_candidates(features)
            use_financial_rank = len(candidates) > 0

        # Tushare不可用或财务候选为空时，回落到价格代理因子。
        if not candidates:
            for code, feat in features.items():
                if not self._temperature_filter(feat):
                    continue
                candidates.append(
                    {
                        "code": code,
                        "roe_proxy": feat["m120"],
                        "roa_proxy": feat["m60"] / (feat["vol60"] + 1e-6),
                        "liquidity": feat["liquidity"],
                    }
                )

        if not candidates:
            self._last_targets = []
            self._last_select_was_rebalance = True
            return []

        if use_financial_rank:
            sorted_roe = sorted(candidates, key=lambda x: x["roe"], reverse=True)
            sorted_roa = sorted(candidates, key=lambda x: x["roa"], reverse=True)
        else:
            sorted_roe = sorted(candidates, key=lambda x: x["roe_proxy"], reverse=True)
            sorted_roa = sorted(candidates, key=lambda x: x["roa_proxy"], reverse=True)
        roe_rank = {x["code"]: i + 1 for i, x in enumerate(sorted_roe)}
        roa_rank = {x["code"]: i + 1 for i, x in enumerate(sorted_roa)}

        scored: List[Dict[str, Any]] = []
        for x in candidates:
            code = x["code"]
            point = self._roe_weight * roe_rank[code] + self._roa_weight * roa_rank[code]
            score = self._moment_score(code)
            if score is None:
                continue
            if score <= self._min_score or score >= self._max_score:
                continue
            scored.append({"code": code, "point": point, "liquidity": x["liquidity"]})

        if not scored:
            self._last_targets = []
            self._last_select_was_rebalance = True
            return []

        scored.sort(key=lambda x: (x["point"], x["liquidity"]))
        self._last_targets = [x["code"] for x in scored[: self._holdings_num]]

        if self.current_date is not None and self._rebalance_monthly:
            self._last_rebalance_month = (self.current_date.year, self.current_date.month)
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

    def _check_stoploss(self) -> None:
        if not self._enable_daily_stoploss:
            return
        for code in list(self._portfolio.positions.keys()):
            if code == self._defense_etf:
                continue
            if not self._is_stock_code(code) or code in self._exclude_codes:
                continue
            pos = self.get_position(code)
            if pos.is_empty or pos.cost_price <= 0:
                continue
            cp = self.get_price(code)
            if cp <= 0:
                continue
            if cp < pos.cost_price * (1 - self._stoploss_limit):
                self.sell_all(code, price=cp)
                if code in self._last_targets:
                    self._last_targets = [c for c in self._last_targets if c != code]

    def _rebalance(self, targets: List[str]) -> None:
        current_codes = [c for c in self._portfolio.positions.keys() if self.has_position(c)]
        stock_holdings = [c for c in current_codes if self._is_stock_code(c) and c not in self._exclude_codes]

        if not targets:
            for c in stock_holdings:
                self._order_target_value(c, 0.0)
            if self._use_defense_etf and self._defense_etf in self._data:
                self._order_target_value(self._defense_etf, self.total_value)
            return

        if self.has_position(self._defense_etf):
            self._order_target_value(self._defense_etf, 0.0)

        target_values = {c: self.total_value / len(targets) for c in targets}
        all_codes = sorted(set(stock_holdings) | set(target_values.keys()))
        for c in all_codes:
            self._order_target_value(c, float(target_values.get(c, 0.0)))

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        self._check_stoploss()
        targets = self._select_targets()
        if self._last_select_was_rebalance:
            self._rebalance(targets)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def on_end(self) -> None:
        preview = ",".join(self._last_targets[:5]) if self._last_targets else "无"
        self.log(f"回测结束：温度={self._market_temperature}，最后目标 {preview}")
