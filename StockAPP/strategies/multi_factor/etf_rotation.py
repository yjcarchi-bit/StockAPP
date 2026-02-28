"""
ETF轮动策略
===========
基于动量因子的ETF轮动策略

策略核心思想:
1. 动量计算：加权线性回归斜率 × R²
2. 多重过滤：短期动量、MA、RSI、MACD、成交量、布林带
3. 止损机制：ATR动态止损 + 固定比例止损
"""

import numpy as np
import math
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase, BarData
from core.indicators import Indicators


ETF_POOL = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "159980", "name": "有色ETF", "type": "商品"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "161226", "name": "油气ETF", "type": "商品"},
    {"code": "501018", "name": "南方原油LOF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513500", "name": "标普500ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "513080", "name": "法国ETF", "type": "海外"},
    {"code": "513130", "name": "恒生科技ETF", "type": "海外"},
    {"code": "513060", "name": "恒生医疗ETF", "type": "海外"},
    {"code": "513050", "name": "中概互联ETF", "type": "海外"},
    {"code": "159920", "name": "恒生ETF", "type": "海外"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "159949", "name": "创业板50ETF", "type": "宽基"},
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    {"code": "159919", "name": "沪深300ETF", "type": "宽基"},
    {"code": "510500", "name": "中证500ETF", "type": "宽基"},
    {"code": "510050", "name": "上证50ETF", "type": "宽基"},
    {"code": "510210", "name": "上证指数ETF", "type": "宽基"},
    {"code": "588080", "name": "科创板50ETF", "type": "宽基"},
    {"code": "512880", "name": "证券ETF", "type": "行业"},
    {"code": "512690", "name": "酒ETF", "type": "行业"},
    {"code": "512170", "name": "医疗ETF", "type": "行业"},
    {"code": "512760", "name": "半导体ETF", "type": "行业"},
    {"code": "159525", "name": "半导体ETF", "type": "行业"},
    {"code": "159995", "name": "芯片ETF", "type": "行业"},
    {"code": "159852", "name": "半导体ETF", "type": "行业"},
    {"code": "515790", "name": "光伏ETF", "type": "行业"},
    {"code": "159806", "name": "光伏ETF", "type": "行业"},
    {"code": "515030", "name": "新能源车ETF", "type": "行业"},
    {"code": "159628", "name": "新能源车ETF", "type": "行业"},
    {"code": "159845", "name": "新能源ETF", "type": "行业"},
    {"code": "516160", "name": "新能源ETF", "type": "行业"},
    {"code": "159928", "name": "消费ETF", "type": "行业"},
    {"code": "512670", "name": "国防军工ETF", "type": "行业"},
    {"code": "511010", "name": "国债ETF", "type": "债券"},
    {"code": "511090", "name": "国债ETF", "type": "债券"},
    {"code": "511880", "name": "银华日利", "type": "货币"},
    {"code": "511990", "name": "华宝添益", "type": "货币"},
]

DEFENSIVE_ETF = "511880"


class ETFRotationStrategy(StrategyBase):
    """
    ETF轮动策略
    
    基于动量因子的ETF轮动策略。在多只ETF之间进行动量轮动，持有动量最强的ETF。
    """
    
    display_name = "ETF轮动策略"
    description = (
        "基于动量因子的ETF轮动策略。在42只ETF之间进行动量轮动，"
        "覆盖商品、海外、宽基、行业、债券、货币等多个类别。"
        "采用加权线性回归计算动量得分，结合多重过滤条件和止损机制。"
    )
    logic = [
        "1. ETF池：42只ETF，覆盖多个资产类别",
        "2. 动量计算：加权线性回归斜率 × R²",
        "3. 短期动量过滤：排除短期动量不足的ETF",
        "4. 近期大跌排除：排除近期大跌的ETF",
        "5. 得分阈值过滤：排除得分异常的ETF",
        "6. 可选过滤：MA/RSI/MACD/成交量/布林带",
        "7. 止损机制：ATR动态止损 + 固定比例止损",
        "8. 防御机制：无合格ETF时持有防御ETF",
        "9. 轮动逻辑：每日检查，持有得分最高的ETF",
    ]
    suitable = "适合追求多元化资产配置、希望参与多市场投资的投资者"
    risk = "多市场轮动可能增加交易成本，动量反转时可能产生较大回撤"
    params_info = {
        "lookback_days": {
            "default": 25,
            "min": 10,
            "max": 60,
            "step": 5,
            "description": "回看天数，用于计算动量的历史天数",
            "type": "slider",
        },
        "holdings_num": {
            "default": 1,
            "min": 1,
            "max": 3,
            "step": 1,
            "description": "持仓数量，同时持有的ETF数量",
            "type": "slider",
        },
        "stop_loss_ratio": {
            "default": 0.05,
            "min": 0.02,
            "max": 0.10,
            "step": 0.01,
            "description": "固定止损比例，触发止损的跌幅阈值",
            "type": "slider",
        },
        "use_atr_stop_loss": {
            "default": True,
            "description": "是否启用ATR动态止损",
            "type": "switch",
        },
        "atr_period": {
            "default": 14,
            "min": 5,
            "max": 30,
            "step": 1,
            "description": "ATR计算周期",
            "type": "slider",
        },
        "atr_multiplier": {
            "default": 2.0,
            "min": 1.0,
            "max": 4.0,
            "step": 0.5,
            "description": "ATR止损倍数",
            "type": "slider",
        },
        "atr_trailing_stop": {
            "default": False,
            "description": "是否使用ATR跟踪止损(否则为固定止损)",
            "type": "switch",
        },
        "use_short_momentum_filter": {
            "default": True,
            "description": "是否启用短期动量过滤",
            "type": "switch",
        },
        "short_lookback_days": {
            "default": 12,
            "min": 5,
            "max": 20,
            "step": 1,
            "description": "短期动量回看天数",
            "type": "slider",
        },
        "short_momentum_threshold": {
            "default": 0.0,
            "min": -0.1,
            "max": 0.1,
            "step": 0.01,
            "description": "短期动量阈值",
            "type": "slider",
        },
        "loss_threshold": {
            "default": 0.97,
            "min": 0.90,
            "max": 0.99,
            "step": 0.01,
            "description": "近期大跌阈值(1-阈值=单日最大跌幅)",
            "type": "slider",
        },
        "use_defensive_etf": {
            "default": True,
            "description": "是否启用防御ETF机制",
            "type": "switch",
        },
        "max_score_threshold": {
            "default": 6.0,
            "min": 1.0,
            "max": 10.0,
            "step": 0.5,
            "description": "得分上限阈值，排除异常高得分",
            "type": "slider",
        },
        "min_score_threshold": {
            "default": 0.0,
            "min": 0.0,
            "max": 2.0,
            "step": 0.1,
            "description": "得分下限阈值，低于此值进入防御模式",
            "type": "slider",
        },
        "use_ma_filter": {
            "default": False,
            "description": "是否启用MA均线过滤",
            "type": "switch",
        },
        "ma_short_period": {
            "default": 5,
            "min": 3,
            "max": 10,
            "step": 1,
            "description": "短期均线周期",
            "type": "slider",
        },
        "ma_long_period": {
            "default": 25,
            "min": 10,
            "max": 60,
            "step": 5,
            "description": "长期均线周期",
            "type": "slider",
        },
        "use_rsi_filter": {
            "default": False,
            "description": "是否启用RSI过滤",
            "type": "switch",
        },
        "rsi_period": {
            "default": 6,
            "min": 3,
            "max": 14,
            "step": 1,
            "description": "RSI计算周期",
            "type": "slider",
        },
        "rsi_threshold": {
            "default": 95,
            "min": 80,
            "max": 100,
            "step": 5,
            "description": "RSI超买阈值",
            "type": "slider",
        },
        "use_macd_filter": {
            "default": False,
            "description": "是否启用MACD过滤",
            "type": "switch",
        },
        "macd_fast_period": {
            "default": 12,
            "min": 5,
            "max": 20,
            "step": 1,
            "description": "MACD快线周期",
            "type": "slider",
        },
        "macd_slow_period": {
            "default": 26,
            "min": 15,
            "max": 40,
            "step": 1,
            "description": "MACD慢线周期",
            "type": "slider",
        },
        "macd_signal_period": {
            "default": 9,
            "min": 5,
            "max": 15,
            "step": 1,
            "description": "MACD信号线周期",
            "type": "slider",
        },
        "use_volume_filter": {
            "default": False,
            "description": "是否启用成交量过滤",
            "type": "switch",
        },
        "volume_lookback_days": {
            "default": 7,
            "min": 3,
            "max": 15,
            "step": 1,
            "description": "成交量回看天数",
            "type": "slider",
        },
        "volume_threshold": {
            "default": 2.0,
            "min": 1.5,
            "max": 5.0,
            "step": 0.5,
            "description": "成交量异常倍数阈值",
            "type": "slider",
        },
        "use_bollinger_filter": {
            "default": False,
            "description": "是否启用布林带过滤",
            "type": "switch",
        },
        "bollinger_period": {
            "default": 20,
            "min": 10,
            "max": 30,
            "step": 5,
            "description": "布林带周期",
            "type": "slider",
        },
        "bollinger_std": {
            "default": 2.0,
            "min": 1.5,
            "max": 3.0,
            "step": 0.5,
            "description": "布林带标准差倍数",
            "type": "slider",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._lookback_days = 25
        self._holdings_num = 1
        self._stop_loss_ratio = 0.05
        
        self._use_atr_stop_loss = True
        self._atr_period = 14
        self._atr_multiplier = 2.0
        self._atr_trailing_stop = False
        
        self._use_short_momentum_filter = True
        self._short_lookback_days = 12
        self._short_momentum_threshold = 0.0
        
        self._loss_threshold = 0.97
        
        self._use_defensive_etf = True
        self._defensive_etf = DEFENSIVE_ETF
        
        self._max_score_threshold = 6.0
        self._min_score_threshold = 0.0
        
        self._use_ma_filter = False
        self._ma_short_period = 5
        self._ma_long_period = 25
        
        self._use_rsi_filter = False
        self._rsi_period = 6
        self._rsi_threshold = 95
        
        self._use_macd_filter = False
        self._macd_fast_period = 12
        self._macd_slow_period = 26
        self._macd_signal_period = 9
        
        self._use_volume_filter = False
        self._volume_lookback_days = 7
        self._volume_threshold = 2.0
        
        self._use_bollinger_filter = False
        self._bollinger_period = 20
        self._bollinger_std = 2.0
        
        self._etf_pool: List[Dict] = ETF_POOL
        self._etf_scores: Dict[str, Dict[str, Any]] = {}
        self._position_highs: Dict[str, float] = {}
        self._position_stop_prices: Dict[str, float] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._lookback_days = self.get_param("lookback_days", 25)
        self._holdings_num = self.get_param("holdings_num", 1)
        self._stop_loss_ratio = self.get_param("stop_loss_ratio", 0.05)
        
        self._use_atr_stop_loss = self.get_param("use_atr_stop_loss", True)
        self._atr_period = self.get_param("atr_period", 14)
        self._atr_multiplier = self.get_param("atr_multiplier", 2.0)
        self._atr_trailing_stop = self.get_param("atr_trailing_stop", False)
        
        self._use_short_momentum_filter = self.get_param("use_short_momentum_filter", True)
        self._short_lookback_days = self.get_param("short_lookback_days", 12)
        self._short_momentum_threshold = self.get_param("short_momentum_threshold", 0.0)
        
        self._loss_threshold = self.get_param("loss_threshold", 0.97)
        
        self._use_defensive_etf = self.get_param("use_defensive_etf", True)
        
        self._max_score_threshold = self.get_param("max_score_threshold", 6.0)
        self._min_score_threshold = self.get_param("min_score_threshold", 0.0)
        
        self._use_ma_filter = self.get_param("use_ma_filter", False)
        self._ma_short_period = self.get_param("ma_short_period", 5)
        self._ma_long_period = self.get_param("ma_long_period", 25)
        
        self._use_rsi_filter = self.get_param("use_rsi_filter", False)
        self._rsi_period = self.get_param("rsi_period", 6)
        self._rsi_threshold = self.get_param("rsi_threshold", 95)
        
        self._use_macd_filter = self.get_param("use_macd_filter", False)
        self._macd_fast_period = self.get_param("macd_fast_period", 12)
        self._macd_slow_period = self.get_param("macd_slow_period", 26)
        self._macd_signal_period = self.get_param("macd_signal_period", 9)
        
        self._use_volume_filter = self.get_param("use_volume_filter", False)
        self._volume_lookback_days = self.get_param("volume_lookback_days", 7)
        self._volume_threshold = self.get_param("volume_threshold", 2.0)
        
        self._use_bollinger_filter = self.get_param("use_bollinger_filter", False)
        self._bollinger_period = self.get_param("bollinger_period", 20)
        self._bollinger_std = self.get_param("bollinger_std", 2.0)
        
        self._etf_scores = {}
        self._position_highs = {}
        self._position_stop_prices = {}
        
        self.log(f"策略初始化完成")
        self.log(f"  回看天数: {self._lookback_days}")
        self.log(f"  持仓数量: {self._holdings_num}")
        self.log(f"  固定止损比例: {self._stop_loss_ratio * 100:.0f}%")
        self.log(f"  ATR动态止损: {'启用' if self._use_atr_stop_loss else '禁用'}")
        if self._use_atr_stop_loss:
            self.log(f"    ATR周期: {self._atr_period}, 倍数: {self._atr_multiplier}, 跟踪止损: {self._atr_trailing_stop}")
        self.log(f"  短期动量过滤: {'启用' if self._use_short_momentum_filter else '禁用'}")
        if self._use_short_momentum_filter:
            self.log(f"    回看天数: {self._short_lookback_days}, 阈值: {self._short_momentum_threshold:.2%}")
        self.log(f"  近期大跌阈值: {(1 - self._loss_threshold) * 100:.0f}%")
        self.log(f"  防御ETF机制: {'启用' if self._use_defensive_etf else '禁用'}")
        self.log(f"  得分阈值: [{self._min_score_threshold:.1f}, {self._max_score_threshold:.1f}]")
        self.log(f"  MA均线过滤: {'启用' if self._use_ma_filter else '禁用'}")
        self.log(f"  RSI过滤: {'启用' if self._use_rsi_filter else '禁用'}")
        self.log(f"  MACD过滤: {'启用' if self._use_macd_filter else '禁用'}")
        self.log(f"  成交量过滤: {'启用' if self._use_volume_filter else '禁用'}")
        self.log(f"  布林带过滤: {'启用' if self._use_bollinger_filter else '禁用'}")
        self.log(f"  ETF池数量: {len(self._etf_pool)}")
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """计算ATR指标"""
        if len(high) < period + 1:
            return 0.0
        
        tr_values = np.zeros(len(high))
        
        for i in range(1, len(high)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr_values[i] = max(tr1, tr2, tr3)
        
        atr = np.mean(tr_values[-period:]) if len(tr_values) >= period else 0.0
        return atr
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 6) -> np.ndarray:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return np.array([])
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.zeros(len(prices))
        avg_losses = np.zeros(len(prices))
        
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        rsi_values = np.zeros(len(prices))
        rsi_values[:period] = 50
        
        for i in range(period + 1, len(prices)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
            
            if avg_losses[i] == 0:
                rsi_values[i] = 100
            else:
                rs = avg_gains[i] / avg_losses[i]
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return rsi_values[period:]
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算EMA指标"""
        ema = np.zeros_like(data)
        ema[0] = data[0]
        alpha = 2 / (period + 1)
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """计算MACD指标"""
        if len(prices) < slow + signal:
            return np.array([]), np.array([]), np.array([])
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        dif = ema_fast - ema_slow
        dea = self._calculate_ema(dif, signal)
        macd_bar = dif - dea
        
        start_idx = slow + signal - 1
        return dif[start_idx:], dea[start_idx:], macd_bar[start_idx:]
    
    def _calculate_bollinger(self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> tuple:
        """计算布林带指标"""
        if len(prices) < period:
            return np.array([]), np.array([]), np.array([])
        
        middle = np.zeros(len(prices))
        upper = np.zeros(len(prices))
        lower = np.zeros(len(prices))
        
        for i in range(period - 1, len(prices)):
            window = prices[i-period+1:i+1]
            middle[i] = np.mean(window)
            std = np.std(window)
            upper[i] = middle[i] + std_dev * std
            lower[i] = middle[i] - std_dev * std
        
        return middle[period-1:], upper[period-1:], lower[period-1:]
    
    def _calculate_momentum(self, code: str) -> Optional[Dict[str, Any]]:
        """计算动量得分"""
        max_lookback = max(
            self._lookback_days, 
            self._short_lookback_days, 
            self._atr_period,
            self._ma_long_period,
            self._rsi_period + 1,
            self._macd_slow_period + self._macd_signal_period,
            self._volume_lookback_days,
            self._bollinger_period
        ) + 10
        
        df = self.get_history(code, max_lookback)
        
        if df is None or len(df) < self._lookback_days:
            return None
        
        close = df["close"].values
        high = df["high"].values if "high" in df.columns else close
        low = df["low"].values if "low" in df.columns else close
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(close))
        
        if len(close) < self._lookback_days:
            return None
        
        current_price = close[-1]
        if current_price <= 0:
            return None
        
        recent_closes = close[-(self._lookback_days + 1):]
        
        y = np.log(recent_closes)
        x = np.arange(len(y))
        
        weights = np.linspace(1, 2, len(y))
        
        try:
            slope, intercept = np.polyfit(x, y, 1, w=weights)
            
            annualized_return = math.exp(slope * 250) - 1
            
            y_pred = slope * x + intercept
            ss_res = np.sum(weights * (y - y_pred) ** 2)
            ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            
            score = annualized_return * r_squared
            
            short_return = 0.0
            short_annualized = 0.0
            short_momentum_pass = True
            
            if self._use_short_momentum_filter and len(close) >= self._short_lookback_days + 1:
                short_return = close[-1] / close[-(self._short_lookback_days + 1)] - 1
                short_annualized = (1 + short_return) ** (250 / self._short_lookback_days) - 1
                short_momentum_pass = short_return >= self._short_momentum_threshold
            
            recent_drop_excluded = False
            if len(close) >= 4:
                day1_ratio = close[-1] / close[-2]
                day2_ratio = close[-2] / close[-3]
                day3_ratio = close[-3] / close[-4]
                
                if min(day1_ratio, day2_ratio, day3_ratio) < self._loss_threshold:
                    score = 0
                    recent_drop_excluded = True
            
            atr = 0.0
            if self._use_atr_stop_loss:
                atr = self._calculate_atr(high, low, close, self._atr_period)
            
            ma_pass = True
            ma5 = 0.0
            ma25 = 0.0
            if self._use_ma_filter and len(close) >= self._ma_long_period:
                ma5 = np.mean(close[-self._ma_short_period:])
                ma25 = np.mean(close[-self._ma_long_period:])
                ma_pass = ma5 >= ma25
            
            rsi_pass = True
            current_rsi = 0.0
            max_rsi = 0.0
            if self._use_rsi_filter and len(close) >= self._rsi_period + 2:
                rsi_values = self._calculate_rsi(close, self._rsi_period)
                if len(rsi_values) >= 2:
                    current_rsi = rsi_values[-1]
                    max_rsi = np.max(rsi_values[-2:])
                    if max_rsi > self._rsi_threshold and current_price < np.mean(close[-5:]):
                        rsi_pass = False
            
            macd_pass = True
            dif_value = 0.0
            dea_value = 0.0
            if self._use_macd_filter and len(close) >= self._macd_slow_period + self._macd_signal_period:
                dif, dea, _ = self._calculate_macd(close, self._macd_fast_period, self._macd_slow_period, self._macd_signal_period)
                if len(dif) > 0 and len(dea) > 0:
                    dif_value = dif[-1]
                    dea_value = dea[-1]
                    macd_pass = dif_value > dea_value
            
            volume_pass = True
            volume_ratio = 0.0
            if self._use_volume_filter and len(volume) >= self._volume_lookback_days + 1:
                recent_volume = volume[-1]
                avg_volume = np.mean(volume[-(self._volume_lookback_days+1):-1])
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume
                    if self._use_defensive_etf and code == self._defensive_etf:
                        volume_pass = True
                    else:
                        volume_pass = volume_ratio <= self._volume_threshold
            
            bollinger_pass = True
            if self._use_bollinger_filter and len(close) >= self._bollinger_period + 1:
                _, upper, _ = self._calculate_bollinger(close[:-1], self._bollinger_period, self._bollinger_std)
                if len(upper) >= 1:
                    if close[-1] > upper[-1] and current_price < np.mean(close[-5:]):
                        bollinger_pass = False
            
            return {
                "code": code,
                "current_price": current_price,
                "slope": slope,
                "annualized_return": annualized_return,
                "r_squared": r_squared,
                "score": score,
                "short_return": short_return,
                "short_annualized": short_annualized,
                "short_momentum_pass": short_momentum_pass,
                "recent_drop_excluded": recent_drop_excluded,
                "atr": atr,
                "high": high,
                "low": low,
                "close": close,
                "ma_pass": ma_pass,
                "ma5": ma5,
                "ma25": ma25,
                "rsi_pass": rsi_pass,
                "current_rsi": current_rsi,
                "max_rsi": max_rsi,
                "macd_pass": macd_pass,
                "dif": dif_value,
                "dea": dea_value,
                "volume_pass": volume_pass,
                "volume_ratio": volume_ratio,
                "bollinger_pass": bollinger_pass,
            }
            
        except Exception as e:
            return None
    
    def _calculate_all_scores(self) -> None:
        """计算所有ETF的动量得分"""
        self._etf_scores = {}
        
        for etf_info in self._etf_pool:
            code = etf_info["code"]
            
            if code not in self._data:
                continue
            
            score_data = self._calculate_momentum(code)
            if score_data is not None:
                score_data["name"] = etf_info.get("name", "")
                score_data["type"] = etf_info.get("type", "")
                self._etf_scores[code] = score_data
    
    def _check_atr_stop_loss(self) -> None:
        """检查ATR动态止损"""
        if not self._use_atr_stop_loss:
            return
        
        for code in list(self._portfolio.positions.keys()):
            pos = self._portfolio.get_position(code)
            
            if pos.is_empty:
                continue
            
            if code not in self._etf_scores:
                continue
            
            if self._use_defensive_etf and code == self._defensive_etf:
                continue
            
            score_data = self._etf_scores[code]
            current_price = score_data["current_price"]
            atr = score_data.get("atr", 0)
            
            if atr <= 0:
                continue
            
            if code not in self._position_highs:
                self._position_highs[code] = current_price
            else:
                self._position_highs[code] = max(self._position_highs[code], current_price)
            
            if self._atr_trailing_stop:
                atr_stop_price = self._position_highs[code] - self._atr_multiplier * atr
            else:
                atr_stop_price = pos.cost_price - self._atr_multiplier * atr
            
            self._position_stop_prices[code] = atr_stop_price
            
            if current_price <= atr_stop_price:
                self.sell_all(code, current_price)
                loss_percent = (current_price / pos.cost_price - 1) * 100
                stop_type = "跟踪" if self._atr_trailing_stop else "固定"
                self.log(f"ATR动态止损({stop_type})卖出: {code}，成本: {pos.cost_price:.3f}，现价: {current_price:.3f}，ATR: {atr:.3f}，止损价: {atr_stop_price:.3f}，亏损: {loss_percent:.2f}%")
                
                if code in self._position_highs:
                    del self._position_highs[code]
                if code in self._position_stop_prices:
                    del self._position_stop_prices[code]
    
    def _check_fixed_stop_loss(self) -> None:
        """检查固定百分比止损"""
        for code in list(self._portfolio.positions.keys()):
            pos = self._portfolio.get_position(code)
            
            if pos.is_empty:
                continue
            
            if code not in self._etf_scores:
                continue
            
            current_price = self._etf_scores[code]["current_price"]
            
            if current_price < pos.cost_price * (1 - self._stop_loss_ratio):
                self.sell_all(code, current_price)
                loss_percent = (current_price / pos.cost_price - 1) * 100
                self.log(f"固定止损卖出: {code}，成本: {pos.cost_price:.3f}，现价: {current_price:.3f}，亏损: {loss_percent:.2f}%")
                
                if code in self._position_highs:
                    del self._position_highs[code]
                if code in self._position_stop_prices:
                    del self._position_stop_prices[code]
    
    def _check_stop_loss(self) -> None:
        """检查止损"""
        self._check_atr_stop_loss()
        self._check_fixed_stop_loss()
    
    def _is_defensive_etf_available(self) -> bool:
        """检查防御ETF是否可用"""
        if not self._use_defensive_etf:
            return False
        
        if self._defensive_etf not in self._etf_scores:
            return False
        
        score_data = self._etf_scores[self._defensive_etf]
        if score_data["current_price"] <= 0:
            return False
        
        return True
    
    def _select_target_etfs(self) -> List[str]:
        """选择目标ETF列表"""
        valid_scores = []
        
        for code, score_data in self._etf_scores.items():
            if self._use_short_momentum_filter and not score_data.get("short_momentum_pass", True):
                continue
            
            if score_data.get("recent_drop_excluded", False):
                continue
            
            if self._use_ma_filter and not score_data.get("ma_pass", True):
                continue
            
            if self._use_rsi_filter and not score_data.get("rsi_pass", True):
                continue
            
            if self._use_macd_filter and not score_data.get("macd_pass", True):
                continue
            
            if self._use_volume_filter and not score_data.get("volume_pass", True):
                continue
            
            if self._use_bollinger_filter and not score_data.get("bollinger_pass", True):
                continue
            
            score = score_data["score"]
            
            if score < self._min_score_threshold:
                continue
            
            if score > self._max_score_threshold:
                continue
            
            valid_scores.append((code, score))
        
        if not valid_scores:
            if self._is_defensive_etf_available():
                self.log(f"无合格ETF，选择防御ETF: {self._defensive_etf}")
                return [self._defensive_etf]
            return []
        
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [code for code, _ in valid_scores[:self._holdings_num]]
    
    def _rebalance(self) -> None:
        """调仓"""
        target_etfs = self._select_target_etfs()
        
        current_holdings = [
            code for code in self._portfolio.positions.keys()
            if self.has_position(code)
        ]
        
        for code in current_holdings:
            if code not in target_etfs:
                if code in self._etf_scores:
                    self.sell_all(code, self._etf_scores[code]["current_price"])
                    self.log(f"轮动卖出: {code}")
                    if code in self._position_highs:
                        del self._position_highs[code]
                    if code in self._position_stop_prices:
                        del self._position_stop_prices[code]
        
        if not target_etfs:
            self.log("无目标ETF，空仓")
            return
        
        cash_available = self._portfolio.cash
        
        if cash_available < 1000:
            return
        
        position_value = cash_available / len(target_etfs)
        
        for code in target_etfs:
            if self.has_position(code):
                continue
            
            if code not in self._etf_scores:
                continue
            
            price = self._etf_scores[code]["current_price"]
            name = self._etf_scores[code].get("name", "")
            score = self._etf_scores[code]["score"]
            
            amount = int(position_value / price / 100) * 100
            if amount <= 0:
                continue
            
            if self.buy(code, price, amount, name=name):
                self._position_highs[code] = price
                self.log(f"轮动买入: {code} {name}，动量得分: {score:.4f}")
    
    def on_trading_day(self, date: datetime, bars: dict) -> None:
        """交易日回调 - 每天只调用一次"""
        self._calculate_all_scores()
        
        self._check_stop_loss()
        
        self._rebalance()
        
        for code in self._portfolio.positions.keys():
            if code in self._etf_scores:
                self.update_position_price(code, self._etf_scores[code]["current_price"])
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        self.log("\n=== ETF轮动策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        
        self.log("\n最后动量得分排名:")
        sorted_scores = sorted(self._etf_scores.items(), key=lambda x: -x[1]["score"])
        for i, (code, score_data) in enumerate(sorted_scores[:5], 1):
            self.log(f"  {i}. {score_data['name']}: {score_data['score']:.4f}")
