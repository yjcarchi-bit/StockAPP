"""
多策略组合策略 (Multi-Strategy Portfolio)
=========================================
将多个子策略按比例组合，每个策略独立管理子组合

策略核心思想:
1. 资金分配：按配置比例将资金分配给各子策略
2. 独立管理：每个子策略独立管理自己的子组合
3. 收益汇总：总收益为各子策略收益之和
4. 风险分散：通过多策略分散风险

配置:
- 搅屎棍策略: 43% 资金
- 偷鸡摸狗策略: 22% 资金
- 多ETF轮动策略: 35% 资金

来源：克隆自聚宽文章 https://www.joinquant.com/post/66658
标题：多策略组合5年440%
作者：鱼树
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators
from core.portfolio import Portfolio, Position


@dataclass
class SubPortfolioConfig:
    """子策略配置"""
    name: str
    strategy_class: type
    pct: float
    params: Dict[str, Any] = field(default_factory=dict)


class SubPortfolio:
    """
    子组合类
    
    每个子策略独立管理自己的资金和持仓
    """
    
    def __init__(self, name: str, starting_cash: float, commission_rate: float = 0.0003):
        self.name = name
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.commission_rate = commission_rate
        self.stamp_duty = 0.001
        self.min_commission = 5.0
        self.lot_size = 100
        
        self.positions: Dict[str, Position] = {}
        self.trades: List[Dict] = []
        self.daily_values: List[Dict] = []
    
    @property
    def position_value(self) -> float:
        """持仓市值"""
        return sum(pos.market_value for pos in self.positions.values() if not pos.is_empty)
    
    @property
    def total_value(self) -> float:
        """总资产"""
        return self.cash + self.position_value
    
    @property
    def profit_pct(self) -> float:
        """收益率"""
        if self.starting_cash == 0:
            return 0.0
        return (self.total_value / self.starting_cash - 1) * 100
    
    def get_position(self, code: str) -> Position:
        """获取持仓"""
        if code not in self.positions:
            self.positions[code] = Position(code=code)
        return self.positions[code]
    
    def has_position(self, code: str) -> bool:
        """是否有持仓"""
        pos = self.positions.get(code)
        return pos is not None and not pos.is_empty
    
    def get_buy_amount(self, code: str, price: float, ratio: float = 1.0) -> int:
        """计算可买入数量"""
        available_cash = self.cash * ratio
        estimated_commission = max(available_cash * self.commission_rate, self.min_commission)
        available_cash -= estimated_commission
        
        max_shares = int(available_cash / price)
        lot_shares = (max_shares // self.lot_size) * self.lot_size
        
        return lot_shares
    
    def buy(self, code: str, price: float, amount: int, name: str = "") -> bool:
        """买入"""
        if amount <= 0 or price <= 0:
            return False
        
        value = price * amount
        commission = max(value * self.commission_rate, self.min_commission)
        total_cost = value + commission
        
        if total_cost > self.cash:
            return False
        
        self.cash -= total_cost
        
        pos = self.get_position(code)
        pos.name = name
        pos.buy(price, amount)
        
        self.trades.append({
            "action": "买入",
            "code": code,
            "name": name,
            "price": price,
            "amount": amount,
            "value": value,
            "commission": commission,
        })
        
        return True
    
    def sell(self, code: str, price: float, amount: Optional[int] = None) -> bool:
        """卖出"""
        pos = self.get_position(code)
        
        if pos.is_empty:
            return False
        
        if amount is None:
            amount = pos.amount
        elif amount > pos.amount:
            amount = pos.amount
        
        if amount <= 0:
            return False
        
        value = price * amount
        commission = max(value * self.commission_rate, self.min_commission)
        stamp_tax = value * self.stamp_duty
        total_fee = commission + stamp_tax
        
        revenue = value - total_fee
        self.cash += revenue
        
        pos.sell(amount)
        pos.update_price(price)
        
        self.trades.append({
            "action": "卖出",
            "code": code,
            "name": pos.name,
            "price": price,
            "amount": amount,
            "value": value,
            "commission": total_fee,
        })
        
        return True
    
    def sell_all(self, code: str, price: float) -> bool:
        """全部卖出"""
        return self.sell(code, price, None)
    
    def update_price(self, code: str, price: float) -> None:
        """更新持仓价格"""
        pos = self.get_position(code)
        pos.update_price(price)
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """批量更新价格"""
        for code, price in prices.items():
            self.update_price(code, price)
    
    def record_daily_value(self, date: str) -> None:
        """记录每日净值"""
        self.daily_values.append({
            "date": date,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "name": self.name,
            "starting_cash": self.starting_cash,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
            "profit_pct": self.profit_pct,
            "position_count": sum(1 for p in self.positions.values() if not p.is_empty),
            "trade_count": len(self.trades),
        }


class SubStrategyWrapper:
    """
    子策略包装器
    
    将策略与子组合关联，使策略操作子组合
    """
    
    def __init__(self, strategy: StrategyBase, subportfolio: SubPortfolio, data: Dict[str, pd.DataFrame]):
        self.strategy = strategy
        self.subportfolio = subportfolio
        self._data = data
        self._current_date: Optional[datetime] = None
        
        self.strategy._portfolio = self._create_fake_portfolio()
        self.strategy._data = data
    
    def _create_fake_portfolio(self) -> Portfolio:
        """创建一个假的Portfolio对象，用于兼容策略基类"""
        fake_portfolio = Portfolio(initial_capital=self.subportfolio.starting_cash)
        fake_portfolio.cash = self.subportfolio.cash
        fake_portfolio.positions = self.subportfolio.positions
        return fake_portfolio
    
    def set_current_date(self, date: datetime) -> None:
        """设置当前日期"""
        self._current_date = date
        self.strategy._current_date = date
    
    def sync_portfolio(self) -> None:
        """同步子组合状态到策略"""
        self.strategy._portfolio.cash = self.subportfolio.cash
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        self.sync_portfolio()
        self.strategy.on_bar(bar)
        self._sync_back()
    
    def _sync_back(self) -> None:
        """同步策略操作回子组合"""
        self.subportfolio.cash = self.strategy._portfolio.cash
    
    def initialize(self) -> None:
        """初始化"""
        self.strategy.initialize()
    
    def on_start(self) -> None:
        """开始"""
        if hasattr(self.strategy, 'on_start'):
            self.strategy.on_start()
    
    def on_end(self) -> None:
        """结束"""
        if hasattr(self.strategy, 'on_end'):
            self.strategy.on_end()


class MultiStrategyPortfolio(StrategyBase):
    """
    多策略组合策略
    
    将多个子策略按比例组合，每个策略独立管理自己的子组合。
    通过资金分配和策略分散实现风险分散和收益优化。
    
    【组合策略】多策略组合配置
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "多策略组合"
    description = (
        "将多个子策略按比例组合的投资策略。每个子策略独立管理自己的子组合，"
        "通过资金分配和策略分散实现风险分散和收益优化。"
        "默认配置：搅屎棍策略43%、偷鸡摸狗策略22%、多ETF轮动策略35%。"
    )
    logic = [
        "1. 资金分配：按配置比例将资金分配给各子策略",
        "2. 独立管理：每个子策略独立管理自己的子组合",
        "3. 策略执行：各策略独立执行交易逻辑",
        "4. 收益汇总：总收益为各子策略收益之和",
        "5. 风险分散：通过多策略分散单一策略风险",
        "6. 默认配置：搅屎棍43%、偷鸡摸狗22%、多ETF轮动35%",
    ]
    suitable = "适合追求稳健收益、希望分散投资风险的投资者"
    risk = "多策略组合可能降低单一策略风险，但仍受市场系统性风险影响"
    params_info = {
        "fms_pct": {
            "default": 0.43,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "搅屎棍策略资金比例",
            "type": "slider",
        },
        "steal_dog_pct": {
            "default": 0.22,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "偷鸡摸狗策略资金比例",
            "type": "slider",
        },
        "multi_etf_pct": {
            "default": 0.35,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "description": "多ETF轮动策略资金比例",
            "type": "slider",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._fms_pct = 0.43
        self._steal_dog_pct = 0.22
        self._multi_etf_pct = 0.35
        
        self._subportfolios: List[SubPortfolio] = []
        self._strategy_wrappers: List[SubStrategyWrapper] = []
        self._strategy_configs: List[SubPortfolioConfig] = []
        
        self._day_counter = 0
        self._initialized = False
    
    def initialize(self) -> None:
        """策略初始化"""
        self._fms_pct = self.get_param("fms_pct", 0.43)
        self._steal_dog_pct = self.get_param("steal_dog_pct", 0.22)
        self._multi_etf_pct = self.get_param("multi_etf_pct", 0.35)
        
        total_pct = self._fms_pct + self._steal_dog_pct + self._multi_etf_pct
        if abs(total_pct - 1.0) > 0.001:
            self.log(f"警告: 策略比例总和 {total_pct:.2f}，将自动归一化")
            self._fms_pct /= total_pct
            self._steal_dog_pct /= total_pct
            self._multi_etf_pct /= total_pct
        
        self._strategy_configs = [
            SubPortfolioConfig(
                name="搅屎棍",
                strategy_class=self._get_fms_class(),
                pct=self._fms_pct,
            ),
            SubPortfolioConfig(
                name="偷鸡摸狗",
                strategy_class=self._get_steal_dog_class(),
                pct=self._steal_dog_pct,
            ),
            SubPortfolioConfig(
                name="ETF轮动",
                strategy_class=self._get_multi_etf_class(),
                pct=self._multi_etf_pct,
            ),
        ]
        
        self._day_counter = 0
        self._initialized = False
        
        self.log(f"策略初始化完成")
        self.log(f"  搅屎棍策略: {self._fms_pct * 100:.0f}%")
        self.log(f"  偷鸡摸狗策略: {self._steal_dog_pct * 100:.0f}%")
        self.log(f"  多ETF轮动策略: {self._multi_etf_pct * 100:.0f}%")
    
    def _get_fms_class(self):
        """获取搅屎棍策略类"""
        from strategies.multi_factor.fms_strategy import FMSStrategy
        return FMSStrategy
    
    def _get_steal_dog_class(self):
        """获取偷鸡摸狗策略类"""
        from strategies.multi_factor.steal_dog_strategy import StealDogStrategy
        return StealDogStrategy
    
    def _get_multi_etf_class(self):
        """获取多ETF轮动策略类"""
        from strategies.multi_factor.multi_etf_rotation import MultiETFRotationStrategy
        return MultiETFRotationStrategy
    
    def _setup_subportfolios(self) -> None:
        """设置子组合"""
        self._subportfolios = []
        self._strategy_wrappers = []
        
        initial_capital = self._portfolio.initial_capital if self._portfolio else 100000
        
        for config in self._strategy_configs:
            if config.pct <= 0:
                continue
            
            sub_cash = initial_capital * config.pct
            subportfolio = SubPortfolio(
                name=config.name,
                starting_cash=sub_cash,
            )
            self._subportfolios.append(subportfolio)
            
            strategy = config.strategy_class()
            wrapper = SubStrategyWrapper(
                strategy=strategy,
                subportfolio=subportfolio,
                data=self._data,
            )
            self._strategy_wrappers.append(wrapper)
            
            wrapper.initialize()
            
            self.log(f"初始化子策略: {config.name}, 资金: {sub_cash:,.2f} ({config.pct*100:.0f}%)")
    
    def on_start(self) -> None:
        """回测开始"""
        self._setup_subportfolios()
        self._initialized = True
        
        for wrapper in self._strategy_wrappers:
            wrapper.on_start()
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        if not self._initialized:
            return
        
        for wrapper in self._strategy_wrappers:
            wrapper.set_current_date(self._current_date)
            wrapper.on_bar(bar)
        
        self._update_total_portfolio()
    
    def _update_total_portfolio(self) -> None:
        """更新总组合状态"""
        total_cash = sum(sp.cash for sp in self._subportfolios)
        total_position_value = sum(sp.position_value for sp in self._subportfolios)
        
        self._portfolio.cash = total_cash
        
        for sp in self._subportfolios:
            for code, pos in sp.positions.items():
                if not pos.is_empty:
                    if code not in self._portfolio.positions:
                        self._portfolio.positions[code] = Position(code=code)
                    self._portfolio.positions[code].amount = pos.amount
                    self._portfolio.positions[code].cost_price = pos.cost_price
                    self._portfolio.positions[code].current_price = pos.current_price
                    self._portfolio.positions[code].name = pos.name
    
    def on_end(self) -> None:
        """回测结束"""
        for wrapper in self._strategy_wrappers:
            wrapper.on_end()
        
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        self.log("\n" + "=" * 60)
        self.log("多策略组合回测结果")
        self.log("=" * 60)
        
        total_value = sum(sp.total_value for sp in self._subportfolios)
        initial_capital = sum(sp.starting_cash for sp in self._subportfolios)
        total_return = (total_value / initial_capital - 1) * 100 if initial_capital > 0 else 0
        
        self.log(f"\n总资产: {total_value:,.2f}")
        self.log(f"初始资金: {initial_capital:,.2f}")
        self.log(f"总收益率: {total_return:.2f}%")
        
        self.log("\n各子策略表现:")
        for sp in self._subportfolios:
            self.log(f"  [{sp.name}]: 收益率 {sp.profit_pct:.2f}%, "
                    f"持仓 {sum(1 for p in sp.positions.values() if not p.is_empty)} 只, "
                    f"交易 {len(sp.trades)} 笔")
        
        self.log("\n" + "=" * 60)
    
    def get_subportfolio_summaries(self) -> List[Dict[str, Any]]:
        """获取所有子组合摘要"""
        return [sp.get_summary() for sp in self._subportfolios]
