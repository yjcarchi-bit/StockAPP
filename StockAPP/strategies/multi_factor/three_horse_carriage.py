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
from typing import Any, Dict, List

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

        self._small = ThreeHorseSmallCapStrategy()
        self._white = ThreeHorseWhiteHorseStrategy()
        self._dual = ThreeHorseDualETFStrategy()

        self._last_snapshot: Dict[str, Any] = {}
        self._small_cached_targets: List[str] = []
        self._white_cached_targets: List[str] = []

    def initialize(self) -> None:
        self._small_ratio = float(self.get_param("small_ratio", 0.35))
        self._rebound_ratio = float(self.get_param("rebound_ratio", 0.10))
        self._rotation_ratio = float(self.get_param("rotation_ratio", 0.35))
        self._white_ratio = float(self.get_param("white_ratio", 0.20))
        self._enable_capital_balance_rule = bool(self.get_param("enable_capital_balance_rule", True))
        self._min_trade_value = float(self.get_param("min_trade_value", 1000))
        self._emulate_original_timing = bool(self.get_param("emulate_original_timing", True))

        small_params = {
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
        self.log("初始化完成（三驾马车总策略本地版）")

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

    def _apply_small_stoploss_on_cached_positions(self) -> None:
        if not self._small_cached_targets:
            return

        # 市场级止损（贴近原版 strategy_1 的 stoploss_strategy=3）
        if int(getattr(self._small, "_stoploss_strategy", 3)) in {2, 3}:
            if self._small._market_stoploss_triggered():
                for code in list(self._small_cached_targets):
                    if not self.has_position(code):
                        continue
                    cp = self.get_price(code)
                    if cp <= 0:
                        continue
                    self.sell_all(code, price=cp)
                    self._small._cooldown_days[code] = int(getattr(self._small, "_no_buy_after_days", 3))
                self._small_cached_targets = []
                return

        if int(getattr(self._small, "_stoploss_strategy", 3)) not in {1, 3}:
            return

        next_targets: List[str] = []
        for code in list(self._small_cached_targets):
            if not self.has_position(code):
                continue
            pos = self.get_position(code)
            if pos.is_empty or pos.cost_price <= 0:
                continue
            cp = self.get_price(code)
            if cp <= 0:
                continue

            # 贴近原版：翻倍止盈 + 固定止损
            if cp >= pos.cost_price * 2:
                self.sell_all(code, price=cp)
                continue
            if cp < pos.cost_price * (1 - float(getattr(self._small, "_stoploss_limit", 0.09))):
                self.sell_all(code, price=cp)
                self._small._cooldown_days[code] = int(getattr(self._small, "_no_buy_after_days", 3))
                continue
            next_targets.append(code)

        self._small_cached_targets = next_targets

    def on_trading_day(self, date: datetime, bars: Dict[str, Any]) -> None:
        self._sync_helpers()

        # 子策略信号
        self._small._update_cooldown()
        self._small._update_dbl_signal()
        self._apply_small_stoploss_on_cached_positions()
        small_selected = self._small._select_targets()
        if self._small.did_rebalance_select():
            self._small_cached_targets = small_selected[:]
        small_targets = self._small_cached_targets[:]

        white_selected = self._white._select_targets()
        if self._white.did_rebalance_select():
            self._white_cached_targets = white_selected[:]
        white_targets = self._white_cached_targets[:]

        rotation_code = self._dual._select_rotation()
        rebound_code = self._dual._select_rebound()

        s_w, r_w, t_w, w_w = self._effective_weights()
        tv = float(self.total_value)

        targets: Dict[str, float] = {}
        if small_targets and s_w > 0:
            if self._small.did_rebalance_select():
                each = tv * s_w / len(small_targets)
                for c in small_targets:
                    targets[c] = targets.get(c, 0.0) + each
            else:
                # 非小市值调仓日，冻结已有仓位，避免日频回归造成额外换手
                for c in small_targets:
                    if not self.has_position(c):
                        continue
                    v = self.get_position(c).amount * self.get_price(c)
                    if v > 0:
                        targets[c] = targets.get(c, 0.0) + v
        elif s_w > 0 and getattr(self._small, "_use_defense_etf", True):
            defense_code = str(getattr(self._small, "_defense_etf", "512800"))
            if defense_code in self._data:
                targets[defense_code] = targets.get(defense_code, 0.0) + tv * s_w

        if white_targets and w_w > 0:
            if self._white.did_rebalance_select():
                each = tv * w_w / len(white_targets)
                for c in white_targets:
                    targets[c] = targets.get(c, 0.0) + each
            else:
                # 非白马调仓日，冻结已有仓位，贴近月频调仓节奏
                for c in white_targets:
                    if not self.has_position(c):
                        continue
                    v = self.get_position(c).amount * self.get_price(c)
                    if v > 0:
                        targets[c] = targets.get(c, 0.0) + v

        if rotation_code and t_w > 0:
            targets[rotation_code] = targets.get(rotation_code, 0.0) + tv * t_w

        if rebound_code and r_w > 0:
            targets[rebound_code] = targets.get(rebound_code, 0.0) + tv * r_w

        self._rebalance_targets(targets)

        for code in list(self._portfolio.positions.keys()):
            if code in bars:
                self.update_position_price(code, float(bars[code].close))

        self._last_snapshot = {
            "small": small_targets[:5],
            "white": white_targets[:5],
            "rotation": rotation_code,
            "rebound": rebound_code,
            "targets": len(targets),
        }

    def on_end(self) -> None:
        self.log(f"回测结束：最后信号 {self._last_snapshot}")
