"""
实时数据模块
============
提供实时行情获取、推送和策略信号计算功能

特性:
- 实时行情获取（支持频率限制）
- WebSocket 数据推送
- 策略信号实时计算
- 交易时间判断
- 异常重连机制
"""

import asyncio
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    import efinance as ef
except ImportError:
    raise ImportError("请安装efinance: pip install efinance")


class MarketStatus(Enum):
    """市场状态"""
    PRE_MARKET = "盘前"
    TRADING = "交易中"
    CLOSED = "已收盘"
    WEEKEND = "周末"


@dataclass
class RealtimeQuote:
    """实时行情数据"""
    code: str
    name: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    amount: float
    change: float
    change_pct: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "amount": self.amount,
            "change": self.change,
            "change_pct": self.change_pct,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StrategySignal:
    """策略信号"""
    action: str
    target_etf: str
    target_name: str
    score: float
    reason: str
    timestamp: datetime
    all_scores: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target_etf": self.target_etf,
            "target_name": self.target_name,
            "score": self.score,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "all_scores": self.all_scores,
        }


class TradingTimeChecker:
    """交易时间检查器"""
    
    MORNING_START = dt_time(9, 30)
    MORNING_END = dt_time(11, 30)
    AFTERNOON_START = dt_time(13, 0)
    AFTERNOON_END = dt_time(15, 0)
    
    @classmethod
    def get_market_status(cls, dt: Optional[datetime] = None) -> MarketStatus:
        """获取市场状态"""
        if dt is None:
            dt = datetime.now()
        
        if dt.weekday() >= 5:
            return MarketStatus.WEEKEND
        
        current_time = dt.time()
        
        if current_time < cls.MORNING_START:
            return MarketStatus.PRE_MARKET
        elif cls.MORNING_START <= current_time <= cls.MORNING_END:
            return MarketStatus.TRADING
        elif cls.MORNING_END < current_time < cls.AFTERNOON_START:
            return MarketStatus.CLOSED
        elif cls.AFTERNOON_START <= current_time <= cls.AFTERNOON_END:
            return MarketStatus.TRADING
        else:
            return MarketStatus.CLOSED
    
    @classmethod
    def is_trading_time(cls, dt: Optional[datetime] = None) -> bool:
        """判断是否为交易时间"""
        return cls.get_market_status(dt) == MarketStatus.TRADING
    
    @classmethod
    def get_next_trading_time(cls, dt: Optional[datetime] = None) -> Optional[datetime]:
        """获取下一个交易时间"""
        if dt is None:
            dt = datetime.now()
        
        current_time = dt.time()
        
        if cls.is_trading_time(dt):
            return dt
        
        if dt.weekday() >= 5:
            days_ahead = 7 - dt.weekday()
            next_day = dt + timedelta(days=days_ahead)
            return next_day.replace(
                hour=cls.MORNING_START.hour,
                minute=cls.MORNING_START.minute,
                second=0,
                microsecond=0
            )
        
        if current_time < cls.MORNING_START:
            return dt.replace(
                hour=cls.MORNING_START.hour,
                minute=cls.MORNING_START.minute,
                second=0,
                microsecond=0
            )
        elif cls.MORNING_END < current_time < cls.AFTERNOON_START:
            return dt.replace(
                hour=cls.AFTERNOON_START.hour,
                minute=cls.AFTERNOON_START.minute,
                second=0,
                microsecond=0
            )
        else:
            next_day = dt + timedelta(days=1)
            if next_day.weekday() >= 5:
                days_ahead = 7 - next_day.weekday()
                next_day += timedelta(days=days_ahead)
            return next_day.replace(
                hour=cls.MORNING_START.hour,
                minute=cls.MORNING_START.minute,
                second=0,
                microsecond=0
            )


class RealtimeDataProvider:
    """
    实时数据提供者
    
    负责获取实时行情数据，支持频率限制和异常重试
    
    Example:
        >>> provider = RealtimeDataProvider(etf_pool)
        >>> quote = await provider.get_realtime_quote("510300")
        >>> provider.subscribe(my_callback)
        >>> await provider.start_streaming()
    """
    
    def __init__(
        self,
        etf_pool: List[str],
        etf_names: Optional[Dict[str, str]] = None,
        request_interval: float = 0.5,
        streaming_interval: float = 3.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        初始化实时数据提供者
        
        Args:
            etf_pool: ETF代码列表
            etf_names: ETF名称映射
            request_interval: 请求间隔（秒），控制频率
            streaming_interval: 推送间隔（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.etf_pool = etf_pool
        self.etf_names = etf_names or {}
        self.request_interval = request_interval
        self.streaming_interval = streaming_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._callbacks: List[Callable[[RealtimeQuote], None]] = []
        self._running = False
        self._last_request_time = 0
        self._quote_cache: Dict[str, RealtimeQuote] = {}
        self._error_counts: Dict[str, int] = {}
        self._max_error_count = 5
        
        self._load_etf_names()
    
    def _load_etf_names(self) -> None:
        """加载ETF名称"""
        default_names = {
            "159915": "创业板ETF",
            "518880": "黄金ETF",
            "513100": "纳指ETF",
            "511220": "城投债ETF",
            "159980": "有色ETF",
            "159985": "豆粕ETF",
            "501018": "南方原油LOF",
            "513500": "标普500ETF",
            "513520": "日经ETF",
            "513030": "德国ETF",
            "513080": "法国ETF",
            "159920": "恒生ETF",
            "510300": "沪深300ETF",
            "510500": "中证500ETF",
            "510050": "上证50ETF",
            "510210": "上证指数ETF",
            "588080": "科创板50ETF",
            "159995": "芯片ETF",
            "513050": "中概互联ETF",
            "159852": "半导体ETF",
            "159845": "新能源ETF",
            "515030": "新能源车ETF",
            "159806": "光伏ETF",
            "516160": "新能源ETF",
            "159928": "消费ETF",
            "512670": "国防军工ETF",
            "511010": "国债ETF",
            "511880": "银华日利",
        }
        for code, name in default_names.items():
            if code not in self.etf_names:
                self.etf_names[code] = name
    
    def _rate_limit(self) -> None:
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_etf_name(self, code: str) -> str:
        """获取ETF名称"""
        return self.etf_names.get(code, code)
    
    def get_realtime_quote(self, code: str) -> Optional[RealtimeQuote]:
        """
        获取单只ETF实时行情
        
        Args:
            code: ETF代码
            
        Returns:
            RealtimeQuote对象，失败返回None
        """
        if self._error_counts.get(code, 0) >= self._max_error_count:
            return self._quote_cache.get(code)
        
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                
                df = ef.stock.get_quote_history(
                    code,
                    beg=(datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                    end=datetime.now().strftime("%Y%m%d"),
                    klt=101,
                    fqt=1
                )
                
                if df is not None and len(df) > 0:
                    row = df.iloc[-1]
                    quote = RealtimeQuote(
                        code=code,
                        name=self._get_etf_name(code),
                        price=float(row.get("收盘", 0)),
                        open=float(row.get("开盘", 0)),
                        high=float(row.get("最高", 0)),
                        low=float(row.get("最低", 0)),
                        volume=float(row.get("成交量", 0)),
                        amount=float(row.get("成交额", 0)),
                        change=float(row.get("涨跌额", 0)),
                        change_pct=float(row.get("涨跌幅", 0)),
                        timestamp=datetime.now(),
                    )
                    self._quote_cache[code] = quote
                    self._error_counts[code] = 0
                    return quote
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self._error_counts[code] = self._error_counts.get(code, 0) + 1
                    print(f"获取{code}实时行情失败: {e}")
        
        return self._quote_cache.get(code)
    
    def get_all_quotes(self) -> Dict[str, RealtimeQuote]:
        """
        获取所有ETF实时行情
        
        Returns:
            字典，键为代码，值为RealtimeQuote
        """
        quotes = {}
        for code in self.etf_pool:
            quote = self.get_realtime_quote(code)
            if quote:
                quotes[code] = quote
        return quotes
    
    def subscribe(self, callback: Callable[[RealtimeQuote], None]) -> None:
        """
        订阅行情更新
        
        Args:
            callback: 回调函数，接收RealtimeQuote参数
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unsubscribe(self, callback: Callable[[RealtimeQuote], None]) -> None:
        """取消订阅"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def start_streaming(self) -> None:
        """启动实时数据流"""
        self._running = True
        
        while self._running:
            try:
                if TradingTimeChecker.is_trading_time():
                    quotes = self.get_all_quotes()
                    
                    for code, quote in quotes.items():
                        for callback in self._callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(quote)
                                else:
                                    callback(quote)
                            except Exception as e:
                                print(f"回调执行错误: {e}")
                else:
                    pass
                
                await asyncio.sleep(self.streaming_interval)
                
            except Exception as e:
                print(f"数据流错误: {e}")
                await asyncio.sleep(self.retry_delay)
    
    def stop_streaming(self) -> None:
        """停止实时数据流"""
        self._running = False
    
    def get_cached_quotes(self) -> Dict[str, RealtimeQuote]:
        """获取缓存的行情数据"""
        return dict(self._quote_cache)
    
    def reset_error_counts(self) -> None:
        """重置错误计数"""
        self._error_counts.clear()
