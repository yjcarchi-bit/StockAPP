"""
组合管理模块
============
管理持仓、资金和组合状态

特性:
- 持仓管理
- 资金管理
- 交易记录
- 资产计算
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import pandas as pd
import numpy as np

from .order import Order, Trade, OrderSide


@dataclass
class Position:
    """
    持仓类
    
    Attributes:
        code: 证券代码
        amount: 持仓数量
        cost_price: 成本价
        current_price: 当前价格
        available: 可用数量
    """
    
    code: str
    amount: int = 0
    cost_price: float = 0.0
    current_price: float = 0.0
    available: int = 0
    name: str = ""
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.amount * self.current_price
    
    @property
    def cost_value(self) -> float:
        """成本市值"""
        return self.amount * self.cost_price
    
    @property
    def profit(self) -> float:
        """浮动盈亏"""
        return self.market_value - self.cost_value
    
    @property
    def profit_pct(self) -> float:
        """盈亏比例"""
        if self.cost_price == 0:
            return 0.0
        return (self.current_price / self.cost_price - 1) * 100
    
    @property
    def is_empty(self) -> bool:
        """是否为空仓"""
        return self.amount == 0
    
    def update_price(self, price: float) -> None:
        """更新当前价格"""
        self.current_price = price
    
    def buy(self, price: float, amount: int) -> None:
        """
        买入
        
        Args:
            price: 买入价格
            amount: 买入数量
        """
        if self.amount == 0:
            self.cost_price = price
            self.amount = amount
        else:
            total_cost = self.cost_price * self.amount + price * amount
            self.amount += amount
            self.cost_price = total_cost / self.amount
        
        self.available += amount
    
    def sell(self, amount: int) -> float:
        """
        卖出
        
        Args:
            amount: 卖出数量
            
        Returns:
            卖出金额
        """
        if amount > self.amount:
            amount = self.amount
        
        self.amount -= amount
        self.available -= amount
        
        if self.amount == 0:
            self.cost_price = 0.0
        
        return amount * self.current_price
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "name": self.name,
            "amount": self.amount,
            "available": self.available,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit": self.profit,
            "profit_pct": self.profit_pct,
        }


class Portfolio:
    """
    组合管理类
    
    管理资金、持仓和交易记录
    
    Example:
        >>> portfolio = Portfolio(initial_capital=100000)
        >>> portfolio.buy("510300", 3.5, 1000)
        >>> portfolio.update_price("510300", 3.6)
        >>> print(portfolio.total_value)
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.0003,
        stamp_duty: float = 0.001,
        min_commission: float = 5.0,
        lot_size: int = 100,
    ):
        """
        初始化组合
        
        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_duty: 印花税率（仅卖出）
            min_commission: 最低佣金
            lot_size: 每手股数
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.min_commission = min_commission
        self.lot_size = lot_size
        
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_values: List[Dict[str, Any]] = []
        
        self._total_commission = 0.0
        self._total_stamp_duty = 0.0
    
    @property
    def position_value(self) -> float:
        """持仓市值"""
        return sum(pos.market_value for pos in self.positions.values() if not pos.is_empty)
    
    @property
    def total_value(self) -> float:
        """总资产"""
        return self.cash + self.position_value
    
    @property
    def total_profit(self) -> float:
        """总盈亏"""
        return self.total_value - self.initial_capital
    
    @property
    def total_profit_pct(self) -> float:
        """总收益率"""
        return (self.total_value / self.initial_capital - 1) * 100
    
    @property
    def position_count(self) -> int:
        """持仓数量"""
        return sum(1 for pos in self.positions.values() if not pos.is_empty)
    
    def get_position(self, code: str) -> Position:
        """
        获取持仓
        
        Args:
            code: 证券代码
            
        Returns:
            Position对象
        """
        if code not in self.positions:
            self.positions[code] = Position(code=code)
        return self.positions[code]
    
    def has_position(self, code: str) -> bool:
        """是否有持仓"""
        pos = self.positions.get(code)
        return pos is not None and not pos.is_empty
    
    def get_buy_amount(self, code: str, price: float, ratio: float = 1.0) -> int:
        """
        计算可买入数量
        
        Args:
            code: 证券代码
            price: 买入价格
            ratio: 资金使用比例
            
        Returns:
            可买入数量（整手）
        """
        available_cash = self.cash * ratio
        estimated_commission = max(available_cash * self.commission_rate, self.min_commission)
        available_cash -= estimated_commission
        
        max_shares = int(available_cash / price)
        lot_shares = (max_shares // self.lot_size) * self.lot_size
        
        return lot_shares
    
    def calculate_commission(self, value: float, is_sell: bool = False) -> float:
        """
        计算交易费用
        
        Args:
            value: 交易金额
            is_sell: 是否为卖出
            
        Returns:
            总费用（佣金 + 印花税）
        """
        commission = max(value * self.commission_rate, self.min_commission)
        stamp = value * self.stamp_duty if is_sell else 0
        
        return commission + stamp
    
    def buy(
        self,
        code: str,
        price: float,
        amount: int,
        timestamp: Optional[datetime] = None,
        name: str = ""
    ) -> Optional[Trade]:
        """
        买入
        
        Args:
            code: 证券代码
            price: 买入价格
            amount: 买入数量
            timestamp: 交易时间
            name: 证券名称
            
        Returns:
            成交记录，失败返回None
        """
        if amount <= 0:
            return None
        
        value = price * amount
        commission = self.calculate_commission(value, is_sell=False)
        total_cost = value + commission
        
        if total_cost > self.cash:
            return None
        
        self.cash -= total_cost
        self._total_commission += commission
        
        pos = self.get_position(code)
        pos.name = name
        pos.buy(price, amount)
        
        trade = Trade(
            order_id="",
            code=code,
            side=OrderSide.BUY,
            price=price,
            amount=amount,
            commission=commission,
            timestamp=timestamp or datetime.now()
        )
        self.trades.append(trade)
        
        return trade
    
    def sell(
        self,
        code: str,
        price: float,
        amount: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[Trade]:
        """
        卖出
        
        Args:
            code: 证券代码
            price: 卖出价格
            amount: 卖出数量，None表示全部卖出
            timestamp: 交易时间
            
        Returns:
            成交记录，失败返回None
        """
        pos = self.get_position(code)
        
        if pos.is_empty:
            return None
        
        if amount is None:
            amount = pos.amount
        elif amount > pos.amount:
            amount = pos.amount
        
        if amount <= 0:
            return None
        
        value = price * amount
        commission = self.calculate_commission(value, is_sell=True)
        
        self._total_commission += commission - value * self.stamp_duty
        self._total_stamp_duty += value * self.stamp_duty
        
        revenue = value - commission
        self.cash += revenue
        
        pos.sell(amount)
        pos.update_price(price)
        
        trade = Trade(
            order_id="",
            code=code,
            side=OrderSide.SELL,
            price=price,
            amount=amount,
            commission=commission,
            timestamp=timestamp or datetime.now()
        )
        self.trades.append(trade)
        
        return trade
    
    def update_price(self, code: str, price: float) -> None:
        """
        更新持仓价格
        
        Args:
            code: 证券代码
            price: 当前价格
        """
        pos = self.get_position(code)
        pos.update_price(price)
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        批量更新持仓价格
        
        Args:
            prices: 价格字典 {code: price}
        """
        for code, price in prices.items():
            self.update_price(code, price)
    
    def record_daily_value(self, date: datetime, prices: Optional[Dict[str, float]] = None) -> None:
        """
        记录每日资产价值
        
        Args:
            date: 日期
            prices: 价格字典
        """
        if prices:
            self.update_prices(prices)
        
        self.daily_values.append({
            "date": date,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
            "positions": {code: pos.to_dict() for code, pos in self.positions.items() if not pos.is_empty}
        })
    
    def get_trade_records(self) -> pd.DataFrame:
        """
        获取交易记录DataFrame
        
        Returns:
            交易记录DataFrame
        """
        if not self.trades:
            return pd.DataFrame()
        
        records = [trade.to_dict() for trade in self.trades]
        df = pd.DataFrame(records)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
        
        return df
    
    def get_daily_values_df(self) -> pd.DataFrame:
        """
        获取每日资产DataFrame
        
        Returns:
            每日资产DataFrame
        """
        if not self.daily_values:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.daily_values)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        
        return df
    
    def get_positions_df(self) -> pd.DataFrame:
        """
        获取持仓DataFrame
        
        Returns:
            持仓DataFrame
        """
        positions = [pos.to_dict() for pos in self.positions.values() if not pos.is_empty]
        
        if not positions:
            return pd.DataFrame()
        
        return pd.DataFrame(positions)
    
    def reset(self) -> None:
        """重置组合状态"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.daily_values.clear()
        self._total_commission = 0.0
        self._total_stamp_duty = 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取组合摘要
        
        Returns:
            组合摘要字典
        """
        return {
            "initial_capital": self.initial_capital,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
            "total_profit": self.total_profit,
            "total_profit_pct": self.total_profit_pct,
            "position_count": self.position_count,
            "trade_count": len(self.trades),
            "total_commission": self._total_commission,
            "total_stamp_duty": self._total_stamp_duty,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions": {code: pos.to_dict() for code, pos in self.positions.items()},
            "trades": [trade.to_dict() for trade in self.trades],
            "daily_values": self.daily_values,
        }
