"""
三驾马车总策略（本地化版）
========================
将三驾马车四个子策略在本地单账户中统一运行：
1) 小市值
2) ETF反弹
3) ETF轮动
4) 白马攻防

实现方式:
- 每日分别生成四个子策略的目标标的
- 按资金权重映射目标仓位（同标的可叠加）
- 统一先卖后买调仓
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase
from strategies.multi_factor.three_horse_small_cap import ThreeHorseSmallCapStrategy
from strategies.multi_factor.three_horse_white_horse import ThreeHorseWhiteHorseStrategy
from strategies.multi_factor.three_horse_dual_etf import ThreeHorseDualETFStrategy


class ThreeHorseCarriageStrategy(StrategyBase):
    """
    三驾马车总策略（四子策略聚合）。
    """

    display_name = "三驾马车总策略"
    description = (
        "在单账户下聚合小市值、ETF反弹、ETF轮动、白马攻防四个子策略，"
        "按资金比例形成统一目标持仓并执行调仓。"
    )
    logic = [
        "1. 计算小市值、白马、ETF反弹、ETF轮动四个子策略目标",
        "2. 应用资金权重得到组合目标仓位",
        "3. 同标的仓位自动叠加",
        "4. 先卖后买执行统一调仓",
        "5. 支持2023-09-28前后反弹资金并入轮动",
    ]
    suitable = "适合希望在本地直接回测完整三驾马车框架的场景"
    risk = "多子策略叠加会提高系统复杂度，参数设置不当可能带来较高换手"
    params_info = {
        "small_ratio": {
            "default": 0.35,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "小市值资金占比",
            "type": "slider",
        },
        "rebound_ratio": {
            "default": 0.10,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "ETF反弹资金占比",
            "type": "slider",
        },
        "rotation_ratio": {
            "default": 0.35,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "ETF轮动资金占比",
            "type": "slider",
        },
        "white_ratio": {
            "default": 0.20,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "白马攻防资金占比",
            "type": "slider",
        },
        "enable_capital_balance_rule": {
            "default": True,
            "description": "启用2023-09-28前后反弹资金并入轮动规则",
            "type": "switch",
        },
        "small_stock_num": {
            "default": 5,
            "min": 3,
            "max": 10,
            "step": 1,
            "description": "小市值持股数",
            "type": "slider",
        },
        "white_holdings_num": {
            "default": 5,
            "min": 3,
            "max": 10,
            "step": 1,
            "description": "白马持股数",
            "type": "slider",
        },
        "auto_stock_limit": {
            "default": 0,
            "min": 0,
            "max": 1000,
            "step": 5,
            "description": "自动加载股票池上限（0表示不限制，仅在未手动传入股票代码时生效）",
            "type": "slider",
        },
        "emulate_original_timing": {
            "default": True,
            "description": "启用贴近原版调度节奏（小市值周频、白马月频）",
            "type": "switch",
        },
        "scheduler_mode": {
            "default": "phase_aligned",
            "description": "调度模式：phase_aligned(原版时序仿真) / legacy_daily(历史聚合)",
            "type": "text",
        },
        "small_xsz_version": {
            "default": "v3",
            "description": "小市值选股版本：v1/v2/v3",
            "type": "text",
        },
        "small_rebalance_weekday": {
            "default": 2,
            "min": 1,
            "max": 5,
            "step": 1,
            "description": "小市值调仓日（1=周一,2=周二...）",
            "type": "slider",
        },
        "small_dbl_control": {
            "default": True,
            "description": "小市值启用顶背离冻结",
            "type": "switch",
        },
        "small_check_dbl_days": {
            "default": 10,
            "min": 3,
            "max": 20,
            "step": 1,
            "description": "小市值顶背离冻结窗口",
            "type": "slider",
        },
        "small_enable_dynamic_stock_num": {
            "default": True,
            "description": "小市值启用动态持股数（3~6）",
            "type": "switch",
        },
        "white_rebalance_monthly": {
            "default": True,
            "description": "白马按月调仓（每月首个交易日）",
            "type": "switch",
        },
        "white_enable_daily_stoploss": {
            "default": False,
            "description": "白马启用日级止损（原版默认关闭）",
            "type": "switch",
        },
        "white_use_financial_filter": {
            "default": False,
            "description": "白马启用财务因子过滤（需Tushare token）",
            "type": "switch",
        },
        "enforce_sub_universe": {
            "default": False,
            "description": "按原版指数严格拆分小市值/白马股票池（会改变曲线）",
            "type": "switch",
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

    PHASE_ORDER: List[str] = [
        "prepare",
        "dbl_check",
        "smallcap_weekly_rebalance",
        "smallcap_stoploss",
        "rotation_rebalance",
        "rotation_intraday_stoploss_check",
        "limit_up_check",
        "capital_balance",
        "rebound_rebalance",
        "close_account",
        "whitehorse_monthly_rebalance",
        "finalize_snapshot",
    ]

    def __init__(self):
        super().__init__()
        self._small_ratio = 0.35
        self._rebound_ratio = 0.10
        self._rotation_ratio = 0.35
        self._white_ratio = 0.20
        self._enable_capital_balance_rule = True
        self._capital_balance_date = date(2023, 9, 28)
        self._min_trade_value = 1000.0
        self._emulate_original_timing = True
        self._scheduler_mode = "phase_aligned"

        self._small = ThreeHorseSmallCapStrategy()
        self._white = ThreeHorseWhiteHorseStrategy()
        self._dual = ThreeHorseDualETFStrategy()

        self._last_snapshot: Dict[str, Any] = {}
        self._small_cached_targets: List[str] = []
        self._white_cached_targets: List[str] = []
        self._small_day_start_targets: List[str] = []
        self._active_rotation_code: Optional[str] = None
        self._active_rebound_code: Optional[str] = None
        self._phase_weights: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._small_freeze_positions = True
        self._white_freeze_positions = True
        self._phase_trace: List[str] = []

    def _normalize_scheduler_mode(self, mode: str) -> str:
        m = str(mode).strip().lower()
        return m if m in {"phase_aligned", "legacy_daily"} else "phase_aligned"

    def initialize(self) -> None:
        self._small_ratio = float(self.get_param("small_ratio", 0.35))
        self._rebound_ratio = float(self.get_param("rebound_ratio", 0.10))
        self._rotation_ratio = float(self.get_param("rotation_ratio", 0.35))
        self._white_ratio = float(self.get_param("white_ratio", 0.20))
        self._enable_capital_balance_rule = bool(self.get_param("enable_capital_balance_rule", True))
        self._min_trade_value = float(self.get_param("min_trade_value", 1000))
        self._emulate_original_timing = bool(self.get_param("emulate_original_timing", True))
        self._scheduler_mode = self._normalize_scheduler_mode(self.get_param("scheduler_mode", "phase_aligned"))

        small_params = {
            "xsz_version": str(self.get_param("small_xsz_version", "v3")),
            "stock_num": int(self.get_param("small_stock_num", 5)),
            "use_defense_etf": True,
            "rebalance_weekly": bool(self._emulate_original_timing),
            "rebalance_weekday": int(self.get_param("small_rebalance_weekday", 2)),
            "enable_dynamic_stock_num": bool(self.get_param("small_enable_dynamic_stock_num", True)),
            "dbl_control": bool(self.get_param("small_dbl_control", True)),
            "check_dbl_days": int(self.get_param("small_check_dbl_days", 10)),
            "index_code": "399101",
            "stoploss_strategy": 3,
            "market_stoploss": 0.05,
            "universe_codes": self.get_param("small_universe_codes", None),
        }
        white_params = {
            "holdings_num": int(self.get_param("white_holdings_num", 5)),
            "use_defense_etf": False,
            "rebalance_monthly": bool(self.get_param("white_rebalance_monthly", True)),
            "enable_daily_stoploss": bool(self.get_param("white_enable_daily_stoploss", False)),
            "use_financial_filter": bool(self.get_param("white_use_financial_filter", False)),
            "index_code": "000300",
            "universe_codes": self.get_param("white_universe_codes", None),
        }
        dual_params = {
            "rotation_ratio": self._rotation_ratio,
            "rebound_ratio": self._rebound_ratio,
            "enable_capital_balance_rule": self._enable_capital_balance_rule,
        }

        self._small.set_params(small_params)
        self._small.initialize()
        self._white.set_params(white_params)
        self._white.initialize()
        self._dual.set_params(dual_params)
        self._dual.initialize()

        self._last_snapshot = {}
        self._small_cached_targets = []
        self._white_cached_targets = []
        self._small_day_start_targets = []
        self._active_rotation_code = None
        self._active_rebound_code = None
        self._phase_weights = self._effective_weights()
        self._small_freeze_positions = True
        self._white_freeze_positions = True
        self._phase_trace = []
        self.log(f"初始化完成（三驾马车总策略本地版，scheduler_mode={self._scheduler_mode}）")

    def _sync_helpers(self) -> None:
        for helper in (self._small, self._white, self._dual):
            helper.set_portfolio(self._portfolio)
            helper.set_data(self._data)
            helper.set_current_date(self._current_date)

    def _effective_weights(self) -> tuple[float, float, float, float]:
        s = max(0.0, self._small_ratio)
        r = max(0.0, self._rebound_ratio)
        t = max(0.0, self._rotation_ratio)
        w = max(0.0, self._white_ratio)

        if self._enable_capital_balance_rule and self.current_date is not None:
            if self.current_date.date() < self._capital_balance_date:
                t += r
                r = 0.0

        total = s + r + t + w
        if total <= 0:
            return 0.0, 0.0, 0.0, 0.0
        if total > 1.0:
            s, r, t, w = s / total, r / total, t / total, w / total
        return s, r, t, w

    def _order_target_value(self, code: str, target_value: float) -> None:
        price = self.get_price(code)
        if price <= 0:
            return

        cur_amt = self.get_position(code).amount if self.has_position(code) else 0
        cur_val = cur_amt * price
        diff = target_value - cur_val
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
            if target_value <= 0 and cur_amt > 0:
                self.sell_all(code, price=price)
            return
        self.sell(code, price=price, amount=amount)

    def _rebalance_targets(self, targets: Dict[str, float]) -> None:
        codes = sorted(set(targets.keys()) | set(self._portfolio.positions.keys()))

        for code in codes:
            price = self.get_price(code)
            if price <= 0:
                continue
            cur_amt = self.get_position(code).amount if self.has_position(code) else 0
            cur_val = cur_amt * price
            tar_val = float(targets.get(code, 0.0))
            if tar_val < cur_val - self._min_trade_value:
                self._order_target_value(code, tar_val)

        for code in codes:
            price = self.get_price(code)
            if price <= 0:
                continue
            cur_amt = self.get_position(code).amount if self.has_position(code) else 0
            cur_val = cur_amt * price
            tar_val = float(targets.get(code, 0.0))
            if tar_val > cur_val + self._min_trade_value:
                self._order_target_value(code, tar_val)

    def _build_combined_targets(self, freeze_small: bool, freeze_white: bool) -> Dict[str, float]:
        s_w, r_w, t_w, w_w = self._phase_weights
        tv = float(self.total_value)
        targets: Dict[str, float] = {}

        small_targets = self._small_cached_targets[:]
        if small_targets and s_w > 0:
            if freeze_small:
                for code in small_targets:
                    if not self.has_position(code):
                        continue
                    value = self.get_position(code).amount * self.get_price(code)
                    if value > 0:
                        targets[code] = targets.get(code, 0.0) + value
            else:
                each = tv * s_w / len(small_targets)
                for code in small_targets:
                    targets[code] = targets.get(code, 0.0) + each
        elif s_w > 0 and getattr(self._small, "_use_defense_etf", True):
            defense_code = str(getattr(self._small, "_defense_etf", "512800"))
            if defense_code in self._data:
                targets[defense_code] = targets.get(defense_code, 0.0) + tv * s_w

        white_targets = self._white_cached_targets[:]
        if white_targets and w_w > 0:
            if freeze_white:
                for code in white_targets:
                    if not self.has_position(code):
                        continue
                    value = self.get_position(code).amount * self.get_price(code)
                    if value > 0:
                        targets[code] = targets.get(code, 0.0) + value
            else:
                each = tv * w_w / len(white_targets)
                for code in white_targets:
                    targets[code] = targets.get(code, 0.0) + each

        if self._active_rotation_code and t_w > 0:
            targets[self._active_rotation_code] = targets.get(self._active_rotation_code, 0.0) + tv * t_w
        if self._active_rebound_code and r_w > 0:
            targets[self._active_rebound_code] = targets.get(self._active_rebound_code, 0.0) + tv * r_w
        return targets

    def _update_prices_from_bars(self, bars: Dict[str, Any]) -> None:
        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

    def _run_legacy_daily_pipeline(self, bars: Dict[str, Any]) -> None:
        self._sync_helpers()

        self._small.prepare_daily_state(tracked_codes=self._small_cached_targets)
        self._small.run_dbl_control_step(tracked_codes=self._small_cached_targets)
        sold_small = self._small.run_stoploss_step(tracked_codes=self._small_cached_targets)
        sold_limit = self._small.check_limit_up_break(tracked_codes=self._small_cached_targets)
        sold_codes = set(sold_small) | set(sold_limit)
        if sold_codes:
            self._small_cached_targets = [c for c in self._small_cached_targets if c not in sold_codes]

        small_selected = self._small._select_targets()
        if self._small.did_rebalance_select():
            self._small_cached_targets = small_selected[:]
        self._small_freeze_positions = not self._small.did_rebalance_select()

        self._white._check_stoploss()
        white_selected = self._white._select_targets()
        if self._white.did_rebalance_select():
            self._white_cached_targets = white_selected[:]
        self._white_freeze_positions = not self._white.did_rebalance_select()

        self._active_rotation_code = self._dual._select_rotation()
        self._active_rebound_code = self._dual._select_rebound()
        self._phase_weights = self._effective_weights()

        targets = self._build_combined_targets(
            freeze_small=self._small_freeze_positions,
            freeze_white=self._white_freeze_positions,
        )
        self._rebalance_targets(targets)
        self._update_prices_from_bars(bars)

        self._last_snapshot = {
            "mode": "legacy_daily",
            "small": self._small_cached_targets[:5],
            "white": self._white_cached_targets[:5],
            "rotation": self._active_rotation_code,
            "rebound": self._active_rebound_code,
            "targets": len(targets),
        }

    def get_trading_phases(self, date: datetime, bars: Dict[str, Any]) -> List[str]:
        if self._scheduler_mode == "legacy_daily":
            return ["legacy_daily"]
        return self.PHASE_ORDER[:]

    def on_trading_phase(self, date: datetime, bars: Dict[str, Any], phase: str) -> None:
        if self._scheduler_mode == "legacy_daily":
            if phase == "legacy_daily":
                self._run_legacy_daily_pipeline(bars)
            return

        self._phase_trace.append(phase)

        if phase == "prepare":
            self._sync_helpers()
            self._phase_trace = [phase]
            self._small_freeze_positions = True
            self._white_freeze_positions = True
            self._small_day_start_targets = self._small_cached_targets[:]
            self._small.prepare_daily_state(tracked_codes=self._small_cached_targets)
            return

        if phase == "dbl_check":
            self._small.run_dbl_control_step(tracked_codes=self._small_cached_targets)
            self._small_cached_targets = [c for c in self._small_cached_targets if self.has_position(c)]
            return

        if phase == "smallcap_weekly_rebalance":
            selected = self._small._select_targets()
            if self._small.did_rebalance_select():
                self._small_cached_targets = selected[:]
                self._small_freeze_positions = False
            else:
                self._small_freeze_positions = True
            return

        if phase == "smallcap_stoploss":
            sold_codes = self._small.run_stoploss_step(tracked_codes=self._small_cached_targets)
            if sold_codes:
                sold_set = set(sold_codes)
                self._small_cached_targets = [c for c in self._small_cached_targets if c not in sold_set]
            return

        if phase == "rotation_rebalance":
            self._active_rotation_code = self._dual._select_rotation()
            return

        if phase == "rotation_intraday_stoploss_check":
            code = self._active_rotation_code
            if not code or not self.has_position(code):
                return
            if not bool(getattr(self._dual, "_rotation_enable_day_stop_filter", True)):
                return
            ratio = self._dual._rotation_day_ratio(code)
            limit = float(getattr(self._dual, "_rotation_day_stoploss_limit", -0.03))
            if ratio is not None and ratio <= limit:
                price = self.get_price(code)
                if price > 0:
                    self.sell_all(code, price=price)
                    self._active_rotation_code = None
                    self.log(f"ETF轮动日内止损触发: {code}")
            return

        if phase == "limit_up_check":
            sold_codes = self._small.check_limit_up_break(tracked_codes=self._small_cached_targets)
            if sold_codes:
                sold_set = set(sold_codes)
                self._small_cached_targets = [c for c in self._small_cached_targets if c not in sold_set]
            return

        if phase == "capital_balance":
            self._phase_weights = self._effective_weights()
            return

        if phase == "rebound_rebalance":
            self._active_rebound_code = self._dual._select_rebound()
            return

        if phase == "close_account":
            close_scope = self._small_cached_targets[:]
            if self.current_date is not None and self.current_date.month in {1, 4}:
                close_scope = self._small_day_start_targets[:]
            if self._small.close_account_if_pause_month(tracked_codes=close_scope):
                self._small_cached_targets = [c for c in self._small_cached_targets if self.has_position(c)]
                self._small_freeze_positions = True
            return

        if phase == "whitehorse_monthly_rebalance":
            self._white._check_stoploss()
            selected = self._white._select_targets()
            if self._white.did_rebalance_select():
                self._white_cached_targets = selected[:]
                self._white_freeze_positions = False
            else:
                self._white_freeze_positions = True
            return

        if phase == "finalize_snapshot":
            targets = self._build_combined_targets(
                freeze_small=self._small_freeze_positions,
                freeze_white=self._white_freeze_positions,
            )
            self._rebalance_targets(targets)
            self._update_prices_from_bars(bars)
            self._last_snapshot = {
                "mode": "phase_aligned",
                "phases": self._phase_trace[:],
                "small": self._small_cached_targets[:5],
                "white": self._white_cached_targets[:5],
                "rotation": self._active_rotation_code,
                "rebound": self._active_rebound_code,
                "targets": len(targets),
            }
            self.log(f"phase_trace: {' -> '.join(self._phase_trace)}")
            return

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        # 兼容旧引擎路径：当引擎未启用阶段调度时，走既有日频聚合逻辑。
        self._run_legacy_daily_pipeline(bars)

    def on_end(self) -> None:
        self.log(f"回测结束：最后信号 {self._last_snapshot}")
