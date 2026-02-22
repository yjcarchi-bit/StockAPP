"""
策略基类模块
============
定义策略接口和基类，所有策略都应继承此类

特性:
- 统一的策略接口
- 内置指标计算方法
- 交易便捷方法
- 参数管理
- 支持简易策略和复合策略分类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
import pandas as pd
import numpy as np

from .indicators import Indicators
from .portfolio import Portfolio, Position


class StrategyCategory(Enum):
    """
    策略类别枚举
    
    SIMPLE: 简易策略 - 针对单一证券进行交易信号判断
    COMPOUND: 复合策略 - 需要多个证券数据进行比较、选择、轮动
    """
    SIMPLE = "simple"
    COMPOUND = "compound"


@dataclass
class BarData:
    """
    K线数据
    
    Attributes:
        code: 证券代码
        name: 证券名称
        date: 日期
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        amount: 成交额
    """
    
    code: str
    name: str = ""
    date: datetime = None
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    
    @classmethod
    def from_series(cls, code: str, series: pd.Series, name: str = "") -> "BarData":
        """从pandas Series创建"""
        return cls(
            code=code,
            name=name,
            date=series.get("date", series.name) if "date" in series or series.name else None,
            open=float(series.get("open", 0)),
            high=float(series.get("high", 0)),
            low=float(series.get("low", 0)),
            close=float(series.get("close", 0)),
            volume=float(series.get("volume", 0)),
            amount=float(series.get("amount", 0)),
        )


@dataclass
class StrategyConfig:
    """
    策略配置基类
    
    所有策略的配置类应继承此类
    """
    pass


class StrategyBase(ABC):
    """
    策略基类
    
    所有策略必须继承此类并实现以下方法:
    - initialize(): 策略初始化
    - on_bar(bar): K线回调
    
    子类应重写以下类属性:
    - category: 策略类别 (SIMPLE/COMPOUND)
    - display_name: 显示名称
    - description: 策略描述
    - logic: 策略逻辑列表
    - suitable: 适用场景
    - risk: 风险提示
    - params_info: 参数信息字典
    
    Example:
        class MyStrategy(StrategyBase):
            category = StrategyCategory.SIMPLE
            display_name = "我的策略"
            description = "这是一个示例策略"
            logic = ["1. 计算指标", "2. 生成信号"]
            suitable = "适合趋势市场"
            risk = "震荡市场可能亏损"
            params_info = {
                "fast_period": {"default": 10, "min": 5, "max": 30, "description": "快线周期"}
            }
    """
    
    category: StrategyCategory = StrategyCategory.SIMPLE
    display_name: str = ""
    description: str = ""
    logic: List[str] = []
    suitable: str = ""
    risk: str = ""
    params_info: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self):
        self._portfolio: Optional[Portfolio] = None
        self._data: Dict[str, pd.DataFrame] = {}
        self._current_date: Optional[datetime] = None
        self._context: Dict[str, Any] = {}
        self._params: Dict[str, Any] = {}
        self._name: str = self.__class__.__name__
    
    @property
    def name(self) -> str:
        """策略名称"""
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value
    
    @property
    def portfolio(self) -> Portfolio:
        """组合对象"""
        return self._portfolio
    
    @property
    def current_date(self) -> datetime:
        """当前日期"""
        return self._current_date
    
    @property
    def cash(self) -> float:
        """当前现金"""
        return self._portfolio.cash if self._portfolio else 0
    
    @property
    def total_value(self) -> float:
        """总资产"""
        return self._portfolio.total_value if self._portfolio else 0
    
    def set_portfolio(self, portfolio: Portfolio) -> None:
        """设置组合对象"""
        self._portfolio = portfolio
    
    def set_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """设置数据"""
        self._data = data
    
    def set_current_date(self, date: datetime) -> None:
        """设置当前日期"""
        self._current_date = date
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取参数"""
        return self._params.get(key, default)
    
    def set_param(self, key: str, value: Any) -> None:
        """设置参数"""
        self._params[key] = value
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """批量设置参数"""
        self._params.update(params)
    
    def get_all_params(self) -> Dict[str, Any]:
        """获取所有参数"""
        return self._params.copy()
    
    @abstractmethod
    def initialize(self) -> None:
        """
        策略初始化
        
        在回测开始前调用，用于设置策略参数、初始化变量等
        """
        pass
    
    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """
        K线回调
        
        每根K线触发一次，在此实现策略逻辑
        
        Args:
            bar: K线数据
        """
        pass
    
    def on_start(self) -> None:
        """回测开始时调用"""
        pass
    
    def on_end(self) -> None:
        """回测结束时调用"""
        pass
    
    def on_trade(self, trade) -> None:
        """交易成交时调用"""
        pass
    
    def get_data(self, code: str) -> Optional[pd.DataFrame]:
        """
        获取证券数据
        
        Args:
            code: 证券代码
            
        Returns:
            数据DataFrame
        """
        return self._data.get(code)
    
    def get_history(
        self,
        code: str,
        length: int,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            code: 证券代码
            length: 数据长度
            fields: 需要的字段列表
            
        Returns:
            历史数据DataFrame
        """
        df = self._data.get(code)
        
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        if self._current_date is not None:
            df = df[df["date"] <= self._current_date]
        
        df = df.tail(length)
        
        if fields:
            available_fields = [f for f in fields if f in df.columns]
            df = df[available_fields] if available_fields else df
        
        return df
    
    def get_price(self, code: str, field: str = "close") -> float:
        """
        获取当前价格
        
        Args:
            code: 证券代码
            field: 价格字段
            
        Returns:
            当前价格
        """
        df = self.get_history(code, 1)
        
        if df.empty or field not in df.columns:
            return 0.0
        
        return float(df[field].iloc[-1])
    
    def get_prices(self, code: str, length: int, field: str = "close") -> np.ndarray:
        """
        获取历史价格序列
        
        Args:
            code: 证券代码
            length: 数据长度
            field: 价格字段
            
        Returns:
            价格数组
        """
        df = self.get_history(code, length)
        
        if df.empty or field not in df.columns:
            return np.array([])
        
        return df[field].values
    
    def buy(
        self,
        code: str,
        price: Optional[float] = None,
        amount: Optional[int] = None,
        ratio: float = 1.0,
        name: str = ""
    ) -> bool:
        """
        买入
        
        Args:
            code: 证券代码
            price: 买入价格，None则使用当前价格
            amount: 买入数量，None则自动计算
            ratio: 资金使用比例（当amount为None时有效）
            name: 证券名称
            
        Returns:
            是否成功
        """
        if price is None:
            price = self.get_price(code)
        
        if price <= 0:
            return False
        
        if amount is None:
            amount = self._portfolio.get_buy_amount(code, price, ratio)
        
        if amount <= 0:
            return False
        
        trade = self._portfolio.buy(
            code=code,
            price=price,
            amount=amount,
            timestamp=self._current_date,
            name=name
        )
        
        return trade is not None
    
    def sell(
        self,
        code: str,
        price: Optional[float] = None,
        amount: Optional[int] = None
    ) -> bool:
        """
        卖出
        
        Args:
            code: 证券代码
            price: 卖出价格，None则使用当前价格
            amount: 卖出数量，None则全部卖出
            
        Returns:
            是否成功
        """
        if price is None:
            price = self.get_price(code)
        
        if price <= 0:
            return False
        
        trade = self._portfolio.sell(
            code=code,
            price=price,
            amount=amount,
            timestamp=self._current_date
        )
        
        return trade is not None
    
    def sell_all(self, code: str, price: Optional[float] = None) -> bool:
        """
        全部卖出
        
        Args:
            code: 证券代码
            price: 卖出价格
            
        Returns:
            是否成功
        """
        return self.sell(code, price, amount=None)
    
    def get_position(self, code: str) -> Position:
        """获取持仓"""
        return self._portfolio.get_position(code)
    
    def has_position(self, code: str) -> bool:
        """是否有持仓"""
        return self._portfolio.has_position(code)
    
    def get_buy_amount(self, code: str, price: Optional[float] = None, ratio: float = 1.0) -> int:
        """
        计算可买入数量
        
        Args:
            code: 证券代码
            price: 买入价格
            ratio: 资金使用比例
            
        Returns:
            可买入数量
        """
        if price is None:
            price = self.get_price(code)
        
        return self._portfolio.get_buy_amount(code, price, ratio)
    
    def update_position_price(self, code: str, price: float) -> None:
        """更新持仓价格"""
        self._portfolio.update_price(code, price)
    
    def SMA(self, data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
        """简单移动平均"""
        return Indicators.SMA(data, period)
    
    def EMA(self, data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
        """指数移动平均"""
        return Indicators.EMA(data, period)
    
    def MACD(
        self,
        close: Union[np.ndarray, pd.Series],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """MACD指标"""
        return Indicators.MACD(close, fast, slow, signal)
    
    def RSI(self, close: Union[np.ndarray, pd.Series], period: int = 14) -> np.ndarray:
        """RSI指标"""
        return Indicators.RSI(close, period)
    
    def KDJ(
        self,
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> tuple:
        """KDJ指标"""
        return Indicators.KDJ(high, low, close, n, m1, m2)
    
    def ATR(
        self,
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> np.ndarray:
        """ATR指标"""
        return Indicators.ATR(high, low, close, period)
    
    def BOLL(
        self,
        close: Union[np.ndarray, pd.Series],
        period: int = 20,
        std_dev: float = 2.0
    ) -> tuple:
        """布林带"""
        return Indicators.BOLL(close, period, std_dev)
    
    def OBV(
        self,
        close: Union[np.ndarray, pd.Series],
        volume: Union[np.ndarray, pd.Series]
    ) -> np.ndarray:
        """OBV指标"""
        return Indicators.OBV(close, volume)
    
    def log(self, message: str) -> None:
        """输出日志"""
        date_str = self._current_date.strftime("%Y-%m-%d") if self._current_date else ""
        print(f"[{date_str}] {self._name}: {message}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            "name": self._name,
            "display_name": self.display_name or self._name,
            "category": self.category.value,
            "description": self.description,
            "logic": self.logic,
            "suitable": self.suitable,
            "risk": self.risk,
            "params_info": self.params_info,
            "params": self._params.copy(),
            "portfolio_summary": self._portfolio.get_summary() if self._portfolio else None,
        }
