"""
订单管理模块
============
定义订单类型、订单状态和订单类

特性:
- 支持多种订单类型（市价单、限价单）
- 订单状态追踪
- 订单历史记录
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """
    订单类
    
    Attributes:
        code: 证券代码
        side: 买卖方向
        amount: 委托数量
        price: 委托价格（限价单需要）
        order_type: 订单类型
        status: 订单状态
        filled_amount: 已成交数量
        filled_price: 成交均价
        create_time: 创建时间
        fill_time: 成交时间
        commission: 佣金
        message: 备注信息
    """
    
    code: str
    side: OrderSide
    amount: int
    price: Optional[float] = None
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: int = 0
    filled_price: float = 0.0
    create_time: datetime = field(default_factory=datetime.now)
    fill_time: Optional[datetime] = None
    commission: float = 0.0
    message: str = ""
    order_id: str = ""
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"{self.code}_{self.create_time.strftime('%Y%m%d%H%M%S%f')}"
    
    @property
    def is_buy(self) -> bool:
        """是否为买入订单"""
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        """是否为卖出订单"""
        return self.side == OrderSide.SELL
    
    @property
    def is_filled(self) -> bool:
        """是否已完全成交"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """是否为活动订单"""
        return self.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED)
    
    @property
    def unfilled_amount(self) -> int:
        """未成交数量"""
        return self.amount - self.filled_amount
    
    @property
    def filled_value(self) -> float:
        """已成交金额"""
        return self.filled_amount * self.filled_price
    
    @property
    def total_value(self) -> float:
        """委托总金额"""
        return self.amount * (self.price or 0)
    
    def fill(self, price: float, amount: Optional[int] = None, commission: float = 0.0) -> None:
        """
        成交订单
        
        Args:
            price: 成交价格
            amount: 成交数量，默认为全部成交
            commission: 佣金
        """
        fill_amount = amount if amount is not None else self.unfilled_amount
        
        if self.filled_amount == 0:
            self.filled_price = price
        else:
            total_filled = self.filled_amount + fill_amount
            self.filled_price = (
                (self.filled_price * self.filled_amount + price * fill_amount) / total_filled
            )
        
        self.filled_amount += fill_amount
        self.commission += commission
        
        if self.filled_amount >= self.amount:
            self.status = OrderStatus.FILLED
            self.fill_time = datetime.now()
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self, reason: str = "") -> None:
        """
        取消订单
        
        Args:
            reason: 取消原因
        """
        if self.is_active:
            self.status = OrderStatus.CANCELLED
            self.message = reason
    
    def reject(self, reason: str = "") -> None:
        """
        拒绝订单
        
        Args:
            reason: 拒绝原因
        """
        self.status = OrderStatus.REJECTED
        self.message = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "code": self.code,
            "side": self.side.value,
            "amount": self.amount,
            "price": self.price,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "filled_amount": self.filled_amount,
            "filled_price": self.filled_price,
            "create_time": self.create_time.isoformat(),
            "fill_time": self.fill_time.isoformat() if self.fill_time else None,
            "commission": self.commission,
            "message": self.message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """从字典创建订单"""
        return cls(
            order_id=data.get("order_id", ""),
            code=data["code"],
            side=OrderSide(data["side"]),
            amount=data["amount"],
            price=data.get("price"),
            order_type=OrderType(data.get("order_type", "market")),
            status=OrderStatus(data.get("status", "pending")),
            filled_amount=data.get("filled_amount", 0),
            filled_price=data.get("filled_price", 0.0),
            create_time=datetime.fromisoformat(data["create_time"]) if "create_time" in data else datetime.now(),
            fill_time=datetime.fromisoformat(data["fill_time"]) if data.get("fill_time") else None,
            commission=data.get("commission", 0.0),
            message=data.get("message", ""),
        )
    
    def __repr__(self) -> str:
        return (
            f"Order(code={self.code}, side={self.side.value}, amount={self.amount}, "
            f"price={self.price}, status={self.status.value}, filled={self.filled_amount})"
        )


@dataclass
class Trade:
    """
    成交记录
    
    Attributes:
        order_id: 关联订单ID
        code: 证券代码
        side: 买卖方向
        price: 成交价格
        amount: 成交数量
        commission: 佣金
        timestamp: 成交时间
    """
    
    order_id: str
    code: str
    side: OrderSide
    price: float
    amount: int
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = ""
    
    def __post_init__(self):
        if not self.trade_id:
            self.trade_id = f"{self.code}_{self.timestamp.strftime('%Y%m%d%H%M%S%f')}"
    
    @property
    def value(self) -> float:
        """成交金额"""
        return self.price * self.amount
    
    @property
    def is_buy(self) -> bool:
        """是否为买入"""
        return self.side == OrderSide.BUY
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "code": self.code,
            "side": self.side.value,
            "price": self.price,
            "amount": self.amount,
            "value": self.value,
            "commission": self.commission,
            "timestamp": self.timestamp.isoformat(),
        }
