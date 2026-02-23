"""
量化智能体模块
==============
一个强大的量化交易智能体，具备以下能力：

1. 市场分析：趋势判断、技术指标分析、市场情绪评估
2. 策略生成：根据需求自动生成量化策略代码
3. 回测解读：分析回测结果，提供优化建议
4. 风险评估：评估策略风险，提供风险控制建议
5. 自然语言交互：理解用户意图，提供专业建议

使用示例:
    >>> from core.quant_agent import QuantAgent
    >>> agent = QuantAgent()
    >>> 
    >>> # 分析市场
    >>> analysis = agent.analyze_market("510300", start_date="2023-01-01")
    >>> 
    >>> # 生成策略
    >>> strategy_code = agent.generate_strategy(
    ...     "我想做一个基于均线交叉的策略，快线20日，慢线60日"
    ... )
    >>> 
    >>> # 解读回测结果
    >>> insights = agent.analyze_backtest(result)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
import json
import re
import pandas as pd
import numpy as np

from .indicators import Indicators
from .data_source import DataSource
from .backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from .strategy_base import StrategyBase, BarData, StrategyCategory
from .portfolio import Portfolio


class AgentIntent(Enum):
    """智能体意图枚举"""
    MARKET_ANALYSIS = "market_analysis"
    STRATEGY_GENERATION = "strategy_generation"
    BACKTEST_ANALYSIS = "backtest_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    PORTFOLIO_ADVICE = "portfolio_advice"
    GENERAL_QUESTION = "general_question"


class MarketTrend(Enum):
    """市场趋势枚举"""
    STRONG_UPTREND = "强势上涨"
    UPTREND = "上涨趋势"
    SIDEWAYS = "震荡"
    DOWNTREND = "下跌趋势"
    STRONG_DOWNTREND = "强势下跌"
    UNCERTAIN = "不确定"


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    VERY_HIGH = "极高风险"


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    code: str
    name: str = ""
    current_price: float = 0.0
    trend: MarketTrend = MarketTrend.UNCERTAIN
    trend_strength: float = 0.0
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    indicators: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "current_price": self.current_price,
            "trend": self.trend.value,
            "trend_strength": round(self.trend_strength, 2),
            "support_levels": [round(x, 2) for x in self.support_levels],
            "resistance_levels": [round(x, 2) for x in self.resistance_levels],
            "indicators": self.indicators,
            "signals": self.signals,
            "recommendations": self.recommendations,
            "risk_level": self.risk_level.value,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class BacktestInsight:
    """回测洞察"""
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    overall_rating: str = ""
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_return": round(self.total_return, 2),
            "annual_return": round(self.annual_return, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "risks": self.risks,
            "optimization_suggestions": self.optimization_suggestions,
            "overall_rating": self.overall_rating,
            "summary": self.summary,
        }


@dataclass
class StrategyTemplate:
    """策略模板"""
    name: str
    category: StrategyCategory
    description: str
    logic: List[str]
    code_template: str
    default_params: Dict[str, Any] = field(default_factory=dict)
    param_info: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class QuantAgent:
    """
    量化智能体
    
    核心能力:
    1. 市场分析：技术指标、趋势判断、支撑阻力
    2. 策略生成：根据描述生成策略代码
    3. 回测解读：分析结果，提供优化建议
    4. 风险评估：评估策略风险
    5. 参数优化：提供参数优化建议
    
    Example:
        >>> agent = QuantAgent()
        >>> 
        >>> # 分析市场
        >>> analysis = agent.analyze_market("510300")
        >>> print(analysis.trend)
        >>> 
        >>> # 生成策略
        >>> code = agent.generate_strategy_code("均线交叉策略")
        >>> 
        >>> # 解读回测
        >>> insight = agent.analyze_backtest_result(result)
    """
    
    def __init__(self, data_source: Optional[DataSource] = None):
        self.data_source = data_source or DataSource()
        self._strategy_templates = self._init_strategy_templates()
        self._indicator_weights = {
            "trend": 0.3,
            "momentum": 0.25,
            "volatility": 0.2,
            "volume": 0.15,
            "pattern": 0.1,
        }
    
    def _init_strategy_templates(self) -> Dict[str, StrategyTemplate]:
        """初始化策略模板"""
        templates = {}
        
        templates["dual_ma"] = StrategyTemplate(
            name="双均线策略",
            category=StrategyCategory.SIMPLE,
            description="基于快慢均线交叉的趋势跟踪策略",
            logic=[
                "1. 计算快速均线和慢速均线",
                "2. 快线上穿慢线时买入",
                "3. 快线下穿慢线时卖出",
                "4. 趋势跟踪，适合单边行情",
            ],
            code_template='''
class DualMAStrategy(StrategyBase):
    """双均线策略"""
    
    category = StrategyCategory.SIMPLE
    display_name = "双均线策略"
    description = "基于快慢均线交叉的趋势跟踪策略"
    logic = [
        "1. 计算快速均线和慢速均线",
        "2. 快线上穿慢线时买入",
        "3. 快线下穿慢线时卖出",
    ]
    suitable = "适合趋势明显的市场"
    risk = "震荡市场可能频繁止损"
    params_info = {
        "fast_period": {"default": 20, "min": 5, "max": 60, "description": "快线周期"},
        "slow_period": {"default": 60, "min": 20, "max": 120, "description": "慢线周期"},
    }
    
    def __init__(self):
        super().__init__()
        self._fast_period = 20
        self._slow_period = 60
        self._prev_fast = None
        self._prev_slow = None
    
    def initialize(self) -> None:
        self._fast_period = self.get_param("fast_period", 20)
        self._slow_period = self.get_param("slow_period", 60)
        self._prev_fast = None
        self._prev_slow = None
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        closes = self.get_prices(code, self._slow_period + 2)
        
        if len(closes) < self._slow_period + 1:
            return
        
        fast_ma = self.SMA(closes, self._fast_period)
        slow_ma = self.SMA(closes, self._slow_period)
        
        current_fast = fast_ma[-1]
        current_slow = slow_ma[-1]
        prev_fast = fast_ma[-2]
        prev_slow = slow_ma[-2]
        
        if np.isnan(current_fast) or np.isnan(current_slow):
            return
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"金叉买入: 快线{current_fast:.2f} > 慢线{current_slow:.2f}")
        
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"死叉卖出: 快线{current_fast:.2f} < 慢线{current_slow:.2f}")
''',
            default_params={"fast_period": 20, "slow_period": 60},
            param_info={
                "fast_period": {"default": 20, "min": 5, "max": 60, "description": "快线周期"},
                "slow_period": {"default": 60, "min": 20, "max": 120, "description": "慢线周期"},
            }
        )
        
        templates["rsi"] = StrategyTemplate(
            name="RSI策略",
            category=StrategyCategory.SIMPLE,
            description="基于RSI超买超卖的反转策略",
            logic=[
                "1. 计算RSI指标",
                "2. RSI低于超卖线时买入",
                "3. RSI高于超买线时卖出",
                "4. 适合震荡市场",
            ],
            code_template='''
class RSIStrategy(StrategyBase):
    """RSI策略"""
    
    category = StrategyCategory.SIMPLE
    display_name = "RSI策略"
    description = "基于RSI超买超卖的反转策略"
    logic = [
        "1. 计算RSI指标",
        "2. RSI低于超卖线时买入",
        "3. RSI高于超买线时卖出",
    ]
    suitable = "适合震荡市场"
    risk = "趋势市场可能逆势操作"
    params_info = {
        "period": {"default": 14, "min": 5, "max": 30, "description": "RSI周期"},
        "oversold": {"default": 30, "min": 20, "max": 40, "description": "超卖阈值"},
        "overbought": {"default": 70, "min": 60, "max": 80, "description": "超买阈值"},
    }
    
    def __init__(self):
        super().__init__()
        self._period = 14
        self._oversold = 30
        self._overbought = 70
    
    def initialize(self) -> None:
        self._period = self.get_param("period", 14)
        self._oversold = self.get_param("oversold", 30)
        self._overbought = self.get_param("overbought", 70)
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        closes = self.get_prices(code, self._period + 10)
        
        if len(closes) < self._period + 1:
            return
        
        rsi = self.RSI(closes, self._period)
        current_rsi = rsi[-1]
        
        if np.isnan(current_rsi):
            return
        
        if current_rsi < self._oversold:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"RSI超卖买入: RSI={current_rsi:.2f}")
        
        elif current_rsi > self._overbought:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"RSI超买卖出: RSI={current_rsi:.2f}")
''',
            default_params={"period": 14, "oversold": 30, "overbought": 70},
            param_info={
                "period": {"default": 14, "min": 5, "max": 30, "description": "RSI周期"},
                "oversold": {"default": 30, "min": 20, "max": 40, "description": "超卖阈值"},
                "overbought": {"default": 70, "min": 60, "max": 80, "description": "超买阈值"},
            }
        )
        
        templates["macd"] = StrategyTemplate(
            name="MACD策略",
            category=StrategyCategory.SIMPLE,
            description="基于MACD金叉死叉的趋势策略",
            logic=[
                "1. 计算MACD指标（DIF、DEA、MACD柱）",
                "2. DIF上穿DEA（金叉）时买入",
                "3. DIF下穿DEA（死叉）时卖出",
                "4. 结合零轴位置判断趋势强弱",
            ],
            code_template='''
class MACDStrategy(StrategyBase):
    """MACD策略"""
    
    category = StrategyCategory.SIMPLE
    display_name = "MACD策略"
    description = "基于MACD金叉死叉的趋势策略"
    logic = [
        "1. 计算MACD指标",
        "2. DIF上穿DEA（金叉）时买入",
        "3. DIF下穿DEA（死叉）时卖出",
    ]
    suitable = "适合趋势市场"
    risk = "震荡市场信号可能频繁"
    params_info = {
        "fast_period": {"default": 12, "min": 8, "max": 20, "description": "快线周期"},
        "slow_period": {"default": 26, "min": 20, "max": 40, "description": "慢线周期"},
        "signal_period": {"default": 9, "min": 5, "max": 15, "description": "信号线周期"},
    }
    
    def __init__(self):
        super().__init__()
        self._fast_period = 12
        self._slow_period = 26
        self._signal_period = 9
    
    def initialize(self) -> None:
        self._fast_period = self.get_param("fast_period", 12)
        self._slow_period = self.get_param("slow_period", 26)
        self._signal_period = self.get_param("signal_period", 9)
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        closes = self.get_prices(code, self._slow_period + self._signal_period + 10)
        
        if len(closes) < self._slow_period + self._signal_period + 5:
            return
        
        dif, dea, macd_bar = self.MACD(closes, self._fast_period, self._slow_period, self._signal_period)
        
        current_dif = dif[-1]
        current_dea = dea[-1]
        prev_dif = dif[-2]
        prev_dea = dea[-2]
        
        if np.isnan(current_dif) or np.isnan(current_dea):
            return
        
        if prev_dif <= prev_dea and current_dif > current_dea:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"MACD金叉买入: DIF={current_dif:.4f}, DEA={current_dea:.4f}")
        
        elif prev_dif >= prev_dea and current_dif < current_dea:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"MACD死叉卖出: DIF={current_dif:.4f}, DEA={current_dea:.4f}")
''',
            default_params={"fast_period": 12, "slow_period": 26, "signal_period": 9},
            param_info={
                "fast_period": {"default": 12, "min": 8, "max": 20, "description": "快线周期"},
                "slow_period": {"default": 26, "min": 20, "max": 40, "description": "慢线周期"},
                "signal_period": {"default": 9, "min": 5, "max": 15, "description": "信号线周期"},
            }
        )
        
        templates["bollinger"] = StrategyTemplate(
            name="布林带策略",
            category=StrategyCategory.SIMPLE,
            description="基于布林带的均值回归策略",
            logic=[
                "1. 计算布林带（中轨、上轨、下轨）",
                "2. 价格触及下轨时买入",
                "3. 价格触及上轨时卖出",
                "4. 适合震荡市场",
            ],
            code_template='''
class BollingerStrategy(StrategyBase):
    """布林带策略"""
    
    category = StrategyCategory.SIMPLE
    display_name = "布林带策略"
    description = "基于布林带的均值回归策略"
    logic = [
        "1. 计算布林带",
        "2. 价格触及下轨时买入",
        "3. 价格触及上轨时卖出",
    ]
    suitable = "适合震荡市场"
    risk = "趋势突破时可能亏损"
    params_info = {
        "period": {"default": 20, "min": 10, "max": 30, "description": "计算周期"},
        "std_dev": {"default": 2.0, "min": 1.5, "max": 3.0, "step": 0.1, "description": "标准差倍数"},
    }
    
    def __init__(self):
        super().__init__()
        self._period = 20
        self._std_dev = 2.0
    
    def initialize(self) -> None:
        self._period = self.get_param("period", 20)
        self._std_dev = self.get_param("std_dev", 2.0)
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        closes = self.get_prices(code, self._period + 5)
        
        if len(closes) < self._period + 1:
            return
        
        middle, upper, lower = self.BOLL(closes, self._period, self._std_dev)
        
        current_close = closes[-1]
        current_upper = upper[-1]
        current_lower = lower[-1]
        current_middle = middle[-1]
        
        if np.isnan(current_upper) or np.isnan(current_lower):
            return
        
        if current_close <= current_lower:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"触及下轨买入: 价格={current_close:.2f}, 下轨={current_lower:.2f}")
        
        elif current_close >= current_upper:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"触及上轨卖出: 价格={current_close:.2f}, 上轨={current_upper:.2f}")
''',
            default_params={"period": 20, "std_dev": 2.0},
            param_info={
                "period": {"default": 20, "min": 10, "max": 30, "description": "计算周期"},
                "std_dev": {"default": 2.0, "min": 1.5, "max": 3.0, "step": 0.1, "description": "标准差倍数"},
            }
        )
        
        templates["etf_rotation"] = StrategyTemplate(
            name="ETF轮动策略",
            category=StrategyCategory.COMPOUND,
            description="多ETF动量轮动策略",
            logic=[
                "1. 计算各ETF的动量指标",
                "2. 选择动量最强的ETF",
                "3. 定期调仓持有最强ETF",
                "4. 分散投资，降低单一资产风险",
            ],
            code_template='''
class ETFRotationStrategy(StrategyBase):
    """ETF轮动策略"""
    
    category = StrategyCategory.COMPOUND
    display_name = "ETF轮动策略"
    description = "多ETF动量轮动策略"
    logic = [
        "1. 计算各ETF的动量指标",
        "2. 选择动量最强的ETF",
        "3. 定期调仓持有最强ETF",
    ]
    suitable = "适合趋势明显的市场"
    risk = "震荡市场可能频繁换仓"
    params_info = {
        "momentum_period": {"default": 20, "min": 10, "max": 60, "description": "动量计算周期"},
        "top_n": {"default": 1, "min": 1, "max": 3, "description": "持有ETF数量"},
    }
    
    def __init__(self):
        super().__init__()
        self._momentum_period = 20
        self._top_n = 1
        self._last_rebalance = None
        self._rebalance_freq = 5
    
    def initialize(self) -> None:
        self._momentum_period = self.get_param("momentum_period", 20)
        self._top_n = self.get_param("top_n", 1)
        self._last_rebalance = None
    
    def on_bar(self, bar: BarData) -> None:
        if self._last_rebalance is None:
            days_since_rebalance = self._rebalance_freq
        else:
            days_since_rebalance = (self._current_date - self._last_rebalance).days
        
        if days_since_rebalance < self._rebalance_freq:
            return
        
        self._last_rebalance = self._current_date
        
        momentum_scores = {}
        for code in self._data.keys():
            closes = self.get_prices(code, self._momentum_period + 5)
            if len(closes) >= self._momentum_period:
                momentum = (closes[-1] / closes[-self._momentum_period] - 1) * 100
                momentum_scores[code] = momentum
        
        sorted_codes = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)
        target_codes = sorted_codes[:self._top_n]
        
        for code in list(self._portfolio.positions.keys()):
            if code not in target_codes:
                self.sell_all(code)
        
        for code in target_codes:
            if not self.has_position(code):
                self.buy(code, ratio=0.95 / self._top_n)
''',
            default_params={"momentum_period": 20, "top_n": 1},
            param_info={
                "momentum_period": {"default": 20, "min": 10, "max": 60, "description": "动量计算周期"},
                "top_n": {"default": 1, "min": 1, "max": 3, "description": "持有ETF数量"},
            }
        )
        
        return templates
    
    def analyze_market(
        self,
        code: str,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        data: Optional[pd.DataFrame] = None,
    ) -> MarketAnalysis:
        """
        分析市场
        
        Args:
            code: 证券代码
            start_date: 开始日期
            end_date: 结束日期
            data: 可选的数据DataFrame
            
        Returns:
            MarketAnalysis对象
        """
        if data is None:
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=365)
            
            data = self.data_source.get_history(code, start_date, end_date, "etf")
        
        if data is None or data.empty:
            return MarketAnalysis(code=code, trend=MarketTrend.UNCERTAIN)
        
        analysis = MarketAnalysis(code=code)
        
        if "name" in data.columns:
            analysis.name = data["name"].iloc[-1]
        
        if "close" in data.columns:
            analysis.current_price = float(data["close"].iloc[-1])
        
        closes = data["close"].values
        highs = data["high"].values if "high" in data.columns else closes
        lows = data["low"].values if "low" in data.columns else closes
        volumes = data["volume"].values if "volume" in data.columns else np.ones(len(closes))
        
        trend, trend_strength = self._analyze_trend(closes)
        analysis.trend = trend
        analysis.trend_strength = trend_strength
        
        analysis.support_levels = self._find_support_levels(lows, closes)
        analysis.resistance_levels = self._find_resistance_levels(highs, closes)
        
        analysis.indicators = self._calculate_indicators(closes, highs, lows, volumes)
        
        analysis.signals = self._generate_signals(analysis)
        
        analysis.recommendations = self._generate_recommendations(analysis)
        
        analysis.risk_level = self._assess_risk(closes, analysis.indicators)
        
        analysis.confidence = self._calculate_confidence(analysis)
        
        return analysis
    
    def _analyze_trend(self, closes: np.ndarray) -> Tuple[MarketTrend, float]:
        """分析趋势"""
        if len(closes) < 60:
            return MarketTrend.UNCERTAIN, 0.0
        
        ma20 = Indicators.SMA(closes, 20)
        ma60 = Indicators.SMA(closes, 60)
        
        current_close = closes[-1]
        current_ma20 = ma20[-1]
        current_ma60 = ma60[-1]
        
        if np.isnan(current_ma20) or np.isnan(current_ma60):
            return MarketTrend.UNCERTAIN, 0.0
        
        slope_20 = Indicators.linear_regression_slope(closes[-20:], 20)[-1]
        slope_60 = Indicators.linear_regression_slope(closes[-60:], 60)[-1]
        
        if np.isnan(slope_20):
            slope_20 = 0
        if np.isnan(slope_60):
            slope_60 = 0
        
        trend_strength = 0.0
        
        if current_close > current_ma20 > current_ma60:
            if slope_20 > 0 and slope_60 > 0:
                trend = MarketTrend.STRONG_UPTREND
                trend_strength = min(100, (slope_20 * 1000 + slope_60 * 1000) / 2)
            else:
                trend = MarketTrend.UPTREND
                trend_strength = 50 + (current_close / current_ma60 - 1) * 100
        elif current_close < current_ma20 < current_ma60:
            if slope_20 < 0 and slope_60 < 0:
                trend = MarketTrend.STRONG_DOWNTREND
                trend_strength = min(100, abs(slope_20 * 1000 + slope_60 * 1000) / 2)
            else:
                trend = MarketTrend.DOWNTREND
                trend_strength = 50 + abs(current_close / current_ma60 - 1) * 100
        else:
            trend = MarketTrend.SIDEWAYS
            trend_strength = 30
        
        return trend, trend_strength
    
    def _find_support_levels(self, lows: np.ndarray, closes: np.ndarray) -> List[float]:
        """寻找支撑位"""
        if len(lows) < 20:
            return []
        
        support_levels = []
        
        recent_lows = lows[-60:] if len(lows) >= 60 else lows
        min_low = np.min(recent_lows)
        support_levels.append(min_low)
        
        ma20 = Indicators.SMA(closes, 20)
        if not np.isnan(ma20[-1]):
            support_levels.append(ma20[-1])
        
        ma60 = Indicators.SMA(closes, 60)
        if len(closes) >= 60 and not np.isnan(ma60[-1]):
            support_levels.append(ma60[-1])
        
        middle, upper, lower = Indicators.BOLL(closes, 20, 2.0)
        if not np.isnan(lower[-1]):
            support_levels.append(lower[-1])
        
        unique_levels = sorted(list(set(support_levels)))
        return unique_levels[-3:] if len(unique_levels) > 3 else unique_levels
    
    def _find_resistance_levels(self, highs: np.ndarray, closes: np.ndarray) -> List[float]:
        """寻找阻力位"""
        if len(highs) < 20:
            return []
        
        resistance_levels = []
        
        recent_highs = highs[-60:] if len(highs) >= 60 else highs
        max_high = np.max(recent_highs)
        resistance_levels.append(max_high)
        
        middle, upper, lower = Indicators.BOLL(closes, 20, 2.0)
        if not np.isnan(upper[-1]):
            resistance_levels.append(upper[-1])
        
        unique_levels = sorted(list(set(resistance_levels)), reverse=True)
        return unique_levels[:3] if len(unique_levels) > 3 else unique_levels
    
    def _calculate_indicators(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray
    ) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        
        indicators["ma5"] = float(Indicators.SMA(closes, 5)[-1]) if len(closes) >= 5 else None
        indicators["ma10"] = float(Indicators.SMA(closes, 10)[-1]) if len(closes) >= 10 else None
        indicators["ma20"] = float(Indicators.SMA(closes, 20)[-1]) if len(closes) >= 20 else None
        indicators["ma60"] = float(Indicators.SMA(closes, 60)[-1]) if len(closes) >= 60 else None
        
        rsi = Indicators.RSI(closes, 14)
        indicators["rsi"] = float(rsi[-1]) if not np.isnan(rsi[-1]) else None
        
        dif, dea, macd_bar = Indicators.MACD(closes)
        indicators["macd_dif"] = float(dif[-1]) if not np.isnan(dif[-1]) else None
        indicators["macd_dea"] = float(dea[-1]) if not np.isnan(dea[-1]) else None
        indicators["macd_bar"] = float(macd_bar[-1]) if not np.isnan(macd_bar[-1]) else None
        
        middle, upper, lower = Indicators.BOLL(closes, 20, 2.0)
        indicators["boll_middle"] = float(middle[-1]) if not np.isnan(middle[-1]) else None
        indicators["boll_upper"] = float(upper[-1]) if not np.isnan(upper[-1]) else None
        indicators["boll_lower"] = float(lower[-1]) if not np.isnan(lower[-1]) else None
        indicators["boll_width"] = float((upper[-1] - lower[-1]) / middle[-1] * 100) if not np.isnan(middle[-1]) else None
        
        atr = Indicators.ATR(highs, lows, closes, 14)
        indicators["atr"] = float(atr[-1]) if not np.isnan(atr[-1]) else None
        indicators["atr_pct"] = float(atr[-1] / closes[-1] * 100) if not np.isnan(atr[-1]) else None
        
        k, d, j = Indicators.KDJ(highs, lows, closes)
        indicators["kdj_k"] = float(k[-1]) if not np.isnan(k[-1]) else None
        indicators["kdj_d"] = float(d[-1]) if not np.isnan(d[-1]) else None
        indicators["kdj_j"] = float(j[-1]) if not np.isnan(j[-1]) else None
        
        if len(closes) >= 20:
            momentum_20 = (closes[-1] / closes[-20] - 1) * 100
            indicators["momentum_20"] = float(momentum_20)
        
        if len(closes) >= 60:
            momentum_60 = (closes[-1] / closes[-60] - 1) * 100
            indicators["momentum_60"] = float(momentum_60)
        
        for key in indicators:
            if indicators[key] is not None and np.isnan(indicators[key]):
                indicators[key] = None
        
        return indicators
    
    def _generate_signals(self, analysis: MarketAnalysis) -> List[str]:
        """生成交易信号"""
        signals = []
        indicators = analysis.indicators
        
        if indicators.get("rsi") is not None:
            rsi = indicators["rsi"]
            if rsi < 30:
                signals.append(f"RSI超卖信号: RSI={rsi:.1f}，可能存在反弹机会")
            elif rsi > 70:
                signals.append(f"RSI超买信号: RSI={rsi:.1f}，注意回调风险")
        
        if indicators.get("macd_dif") is not None and indicators.get("macd_dea") is not None:
            dif = indicators["macd_dif"]
            dea = indicators["macd_dea"]
            macd_bar = indicators.get("macd_bar", 0)
            
            if dif > dea and macd_bar > 0:
                signals.append(f"MACD金叉信号: DIF={dif:.4f} > DEA={dea:.4f}")
            elif dif < dea and macd_bar < 0:
                signals.append(f"MACD死叉信号: DIF={dif:.4f} < DEA={dea:.4f}")
        
        if analysis.trend in [MarketTrend.STRONG_UPTREND, MarketTrend.UPTREND]:
            signals.append(f"趋势信号: {analysis.trend.value}，趋势强度{analysis.trend_strength:.1f}")
        elif analysis.trend in [MarketTrend.STRONG_DOWNTREND, MarketTrend.DOWNTREND]:
            signals.append(f"趋势信号: {analysis.trend.value}，注意风险控制")
        
        if indicators.get("boll_width") is not None:
            width = indicators["boll_width"]
            if width < 5:
                signals.append(f"布林带收窄: 宽度{width:.1f}%，可能面临突破")
            elif width > 15:
                signals.append(f"布林带扩张: 宽度{width:.1f}%，波动加大")
        
        return signals
    
    def _generate_recommendations(self, analysis: MarketAnalysis) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        if analysis.trend in [MarketTrend.STRONG_UPTREND, MarketTrend.UPTREND]:
            recommendations.append("当前处于上涨趋势，可考虑逢低布局")
            recommendations.append("建议设置移动止损保护利润")
        elif analysis.trend in [MarketTrend.STRONG_DOWNTREND, MarketTrend.DOWNTREND]:
            recommendations.append("当前处于下跌趋势，建议谨慎操作")
            recommendations.append("可考虑空仓观望或轻仓试探")
        else:
            recommendations.append("当前市场震荡，适合高抛低吸操作")
        
        if analysis.support_levels:
            recommendations.append(f"关注支撑位: {', '.join([f'{x:.2f}' for x in analysis.support_levels[:2]])}")
        if analysis.resistance_levels:
            recommendations.append(f"关注阻力位: {', '.join([f'{x:.2f}' for x in analysis.resistance_levels[:2]])}")
        
        if analysis.risk_level == RiskLevel.HIGH:
            recommendations.append("当前风险较高，建议控制仓位")
        elif analysis.risk_level == RiskLevel.LOW:
            recommendations.append("当前风险较低，可适当增加仓位")
        
        return recommendations
    
    def _assess_risk(self, closes: np.ndarray, indicators: Dict[str, Any]) -> RiskLevel:
        """评估风险等级"""
        risk_score = 0
        
        if len(closes) >= 20:
            returns = np.diff(closes[-20:]) / closes[-21:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100
            if volatility > 40:
                risk_score += 2
            elif volatility > 25:
                risk_score += 1
        
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi > 80 or rsi < 20:
                risk_score += 1
        
        if indicators.get("boll_width") is not None:
            width = indicators["boll_width"]
            if width > 20:
                risk_score += 1
        
        if risk_score >= 3:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 2:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_confidence(self, analysis: MarketAnalysis) -> float:
        """计算分析置信度"""
        confidence = 0.5
        
        if analysis.indicators.get("rsi") is not None:
            confidence += 0.1
        if analysis.indicators.get("macd_dif") is not None:
            confidence += 0.1
        if analysis.indicators.get("boll_middle") is not None:
            confidence += 0.1
        
        if analysis.trend != MarketTrend.UNCERTAIN:
            confidence += 0.1
        
        if analysis.support_levels or analysis.resistance_levels:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def analyze_backtest_result(self, result: BacktestResult) -> BacktestInsight:
        """
        分析回测结果
        
        Args:
            result: 回测结果对象
            
        Returns:
            BacktestInsight对象
        """
        if not result.metrics:
            result.calculate_metrics()
        
        insight = BacktestInsight()
        metrics = result.metrics
        
        insight.total_return = metrics.get("total_return", 0)
        insight.annual_return = metrics.get("annual_return", 0)
        insight.max_drawdown = metrics.get("max_drawdown", 0)
        insight.sharpe_ratio = metrics.get("sharpe_ratio", 0)
        insight.win_rate = metrics.get("win_rate", 0)
        insight.profit_factor = metrics.get("profit_factor", 0)
        
        insight.strengths = self._identify_strengths(metrics)
        insight.weaknesses = self._identify_weaknesses(metrics)
        insight.risks = self._identify_risks(metrics)
        insight.optimization_suggestions = self._generate_optimization_suggestions(metrics, result)
        
        insight.overall_rating = self._calculate_overall_rating(metrics)
        insight.summary = self._generate_summary(insight)
        
        return insight
    
    def _identify_strengths(self, metrics: Dict[str, Any]) -> List[str]:
        """识别策略优势"""
        strengths = []
        
        if metrics.get("annual_return", 0) > 15:
            strengths.append(f"年化收益率{metrics['annual_return']:.1f}%表现优秀")
        elif metrics.get("annual_return", 0) > 8:
            strengths.append(f"年化收益率{metrics['annual_return']:.1f}%表现良好")
        
        if metrics.get("sharpe_ratio", 0) > 1.5:
            strengths.append(f"夏普比率{metrics['sharpe_ratio']:.2f}，风险调整收益优秀")
        elif metrics.get("sharpe_ratio", 0) > 1.0:
            strengths.append(f"夏普比率{metrics['sharpe_ratio']:.2f}，风险调整收益良好")
        
        if metrics.get("max_drawdown", 0) > -10:
            strengths.append(f"最大回撤{metrics['max_drawdown']:.1f}%，风险控制出色")
        elif metrics.get("max_drawdown", 0) > -20:
            strengths.append(f"最大回撤{metrics['max_drawdown']:.1f}%，风险控制良好")
        
        if metrics.get("win_rate", 0) > 60:
            strengths.append(f"胜率{metrics['win_rate']:.1f}%，交易成功率高")
        
        if metrics.get("profit_factor", 0) > 2.0:
            strengths.append(f"盈亏比{metrics['profit_factor']:.2f}，盈利能力强")
        
        return strengths if strengths else ["策略运行正常，建议进一步优化"]
    
    def _identify_weaknesses(self, metrics: Dict[str, Any]) -> List[str]:
        """识别策略劣势"""
        weaknesses = []
        
        if metrics.get("annual_return", 0) < 5:
            weaknesses.append(f"年化收益率{metrics['annual_return']:.1f}%偏低")
        
        if metrics.get("sharpe_ratio", 0) < 0.5:
            weaknesses.append(f"夏普比率{metrics['sharpe_ratio']:.2f}偏低，风险收益比不佳")
        
        if metrics.get("max_drawdown", 0) < -30:
            weaknesses.append(f"最大回撤{metrics['max_drawdown']:.1f}%过大，风险控制需改进")
        
        if metrics.get("win_rate", 0) < 40:
            weaknesses.append(f"胜率{metrics['win_rate']:.1f}%偏低")
        
        if metrics.get("profit_factor", 0) < 1.0:
            weaknesses.append(f"盈亏比{metrics['profit_factor']:.2f}<1，策略亏损")
        
        if metrics.get("total_trades", 0) < 5:
            weaknesses.append("交易次数过少，样本不足")
        elif metrics.get("total_trades", 0) > 200:
            weaknesses.append("交易次数过多，可能过度交易")
        
        return weaknesses
    
    def _identify_risks(self, metrics: Dict[str, Any]) -> List[str]:
        """识别风险因素"""
        risks = []
        
        if metrics.get("max_drawdown", 0) < -20:
            risks.append("存在较大回撤风险")
        
        if metrics.get("annual_volatility", 0) > 25:
            risks.append("策略波动性较大")
        
        if metrics.get("total_trades", 0) > 100:
            risks.append("交易频繁，交易成本可能侵蚀收益")
        
        if metrics.get("win_rate", 0) < 50 and metrics.get("profit_factor", 0) < 1.5:
            risks.append("胜率和盈亏比均不理想")
        
        return risks if risks else ["风险水平适中"]
    
    def _generate_optimization_suggestions(
        self,
        metrics: Dict[str, Any],
        result: BacktestResult
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if metrics.get("max_drawdown", 0) < -20:
            suggestions.append("建议增加止损机制，控制最大回撤")
            suggestions.append("可考虑降低单次交易仓位比例")
        
        if metrics.get("sharpe_ratio", 0) < 1.0:
            suggestions.append("建议优化入场条件，提高胜率")
            suggestions.append("可考虑增加过滤条件，减少假信号")
        
        if metrics.get("win_rate", 0) < 50:
            suggestions.append("建议调整策略参数，提高信号质量")
            suggestions.append("可考虑增加趋势过滤，避免逆势交易")
        
        if metrics.get("total_trades", 0) > 100:
            suggestions.append("交易频率较高，建议增加信号过滤条件")
            suggestions.append("可考虑延长持仓周期")
        
        if metrics.get("total_trades", 0) < 10:
            suggestions.append("交易机会较少，可考虑放宽入场条件")
            suggestions.append("可考虑增加交易标的范围")
        
        if metrics.get("annual_return", 0) < 8:
            suggestions.append("收益率偏低，建议进行参数优化")
            suggestions.append("可考虑结合其他策略进行组合")
        
        return suggestions if suggestions else ["策略表现良好，可继续观察"]
    
    def _calculate_overall_rating(self, metrics: Dict[str, Any]) -> str:
        """计算总体评级"""
        score = 0
        
        annual_return = metrics.get("annual_return", 0)
        if annual_return > 20:
            score += 25
        elif annual_return > 15:
            score += 20
        elif annual_return > 10:
            score += 15
        elif annual_return > 5:
            score += 10
        else:
            score += 5
        
        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe > 2.0:
            score += 25
        elif sharpe > 1.5:
            score += 20
        elif sharpe > 1.0:
            score += 15
        elif sharpe > 0.5:
            score += 10
        else:
            score += 5
        
        max_dd = metrics.get("max_drawdown", 0)
        if max_dd > -10:
            score += 25
        elif max_dd > -15:
            score += 20
        elif max_dd > -20:
            score += 15
        elif max_dd > -30:
            score += 10
        else:
            score += 5
        
        win_rate = metrics.get("win_rate", 0)
        if win_rate > 70:
            score += 25
        elif win_rate > 60:
            score += 20
        elif win_rate > 50:
            score += 15
        elif win_rate > 40:
            score += 10
        else:
            score += 5
        
        if score >= 85:
            return "优秀 (A+)"
        elif score >= 75:
            return "良好 (A)"
        elif score >= 65:
            return "中等 (B)"
        elif score >= 55:
            return "一般 (C)"
        else:
            return "待优化 (D)"
    
    def _generate_summary(self, insight: BacktestInsight) -> str:
        """生成总结"""
        summary_parts = []
        
        summary_parts.append(f"策略评级: {insight.overall_rating}")
        summary_parts.append(f"年化收益: {insight.annual_return:.2f}%")
        summary_parts.append(f"最大回撤: {insight.max_drawdown:.2f}%")
        summary_parts.append(f"夏普比率: {insight.sharpe_ratio:.2f}")
        
        if insight.strengths:
            summary_parts.append(f"\n优势: {insight.strengths[0]}")
        
        if insight.weaknesses:
            summary_parts.append(f"不足: {insight.weaknesses[0]}")
        
        if insight.optimization_suggestions:
            summary_parts.append(f"\n建议: {insight.optimization_suggestions[0]}")
        
        return "\n".join(summary_parts)
    
    def generate_strategy_code(
        self,
        description: str,
        strategy_type: Optional[str] = None
    ) -> str:
        """
        根据描述生成策略代码
        
        Args:
            description: 策略描述
            strategy_type: 策略类型（可选）
            
        Returns:
            策略代码字符串
        """
        description_lower = description.lower()
        
        if strategy_type and strategy_type in self._strategy_templates:
            template = self._strategy_templates[strategy_type]
            return self._customize_template(template, description)
        
        if any(kw in description_lower for kw in ["均线", "ma", "移动平均", "dual_ma", "双均线"]):
            template = self._strategy_templates["dual_ma"]
            return self._customize_template(template, description)
        
        if any(kw in description_lower for kw in ["rsi", "相对强弱", "超买", "超卖"]):
            template = self._strategy_templates["rsi"]
            return self._customize_template(template, description)
        
        if any(kw in description_lower for kw in ["macd", "异同移动平均"]):
            template = self._strategy_templates["macd"]
            return self._customize_template(template, description)
        
        if any(kw in description_lower for kw in ["布林", "boll", "bollinger"]):
            template = self._strategy_templates["bollinger"]
            return self._customize_template(template, description)
        
        if any(kw in description_lower for kw in ["轮动", "rotation", "etf轮动"]):
            template = self._strategy_templates["etf_rotation"]
            return self._customize_template(template, description)
        
        return self._generate_custom_strategy(description)
    
    def _customize_template(self, template: StrategyTemplate, description: str) -> str:
        """根据描述自定义模板"""
        code = template.code_template
        
        params = self._extract_params_from_description(description)
        
        for param_name, param_value in params.items():
            pattern = rf'("{param_name}".*?"default":\s*)\d+'
            replacement = rf'\g<1>{param_value}'
            code = re.sub(pattern, replacement, code)
        
        return code
    
    def _extract_params_from_description(self, description: str) -> Dict[str, int]:
        """从描述中提取参数"""
        params = {}
        
        numbers = re.findall(r'\d+', description)
        
        if "快线" in description or "快" in description:
            if numbers:
                params["fast_period"] = int(numbers[0])
        if "慢线" in description or "慢" in description:
            if len(numbers) > 1:
                params["slow_period"] = int(numbers[1])
        
        if "周期" in description and numbers:
            params["period"] = int(numbers[0])
        
        return params
    
    def _generate_custom_strategy(self, description: str) -> str:
        """生成自定义策略"""
        return f'''
class CustomStrategy(StrategyBase):
    """自定义策略
    
    描述: {description}
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "自定义策略"
    description = "{description}"
    logic = [
        "1. 根据您的描述实现策略逻辑",
        "2. 请根据实际需求完善代码",
    ]
    suitable = "请根据策略特点填写"
    risk = "请根据策略风险填写"
    params_info = {{}}
    
    def __init__(self):
        super().__init__()
    
    def initialize(self) -> None:
        """初始化策略参数"""
        pass
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调 - 实现您的策略逻辑"""
        code = bar.code
        
        # 获取历史数据
        closes = self.get_prices(code, 60)
        
        if len(closes) < 20:
            return
        
        # TODO: 在此实现您的策略逻辑
        # 示例: 简单的趋势跟踪
        ma20 = self.SMA(closes, 20)
        ma60 = self.SMA(closes, 60)
        
        if np.isnan(ma20[-1]) or np.isnan(ma60[-1]):
            return
        
        # 买入条件
        if ma20[-1] > ma60[-1] and not self.has_position(code):
            self.buy(code, ratio=0.95)
            self.log("买入信号触发")
        
        # 卖出条件
        elif ma20[-1] < ma60[-1] and self.has_position(code):
            self.sell_all(code)
            self.log("卖出信号触发")
'''
    
    def get_strategy_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有策略模板"""
        return {
            key: {
                "name": template.name,
                "category": template.category.value,
                "description": template.description,
                "logic": template.logic,
                "default_params": template.default_params,
                "param_info": template.param_info,
            }
            for key, template in self._strategy_templates.items()
        }
    
    def suggest_parameters(
        self,
        strategy_type: str,
        data: pd.DataFrame,
        optimization_target: str = "sharpe"
    ) -> Dict[str, Any]:
        """
        建议策略参数
        
        Args:
            strategy_type: 策略类型
            data: 历史数据
            optimization_target: 优化目标
            
        Returns:
            建议参数字典
        """
        suggestions = {}
        
        closes = data["close"].values if "close" in data.columns else None
        if closes is None or len(closes) < 60:
            return {"error": "数据不足"}
        
        if strategy_type in ["dual_ma", "双均线"]:
            suggestions = self._suggest_ma_params(closes)
        elif strategy_type in ["rsi"]:
            suggestions = self._suggest_rsi_params(closes)
        elif strategy_type in ["macd"]:
            suggestions = self._suggest_macd_params(closes)
        elif strategy_type in ["bollinger", "布林带"]:
            suggestions = self._suggest_boll_params(closes)
        
        return suggestions
    
    def _suggest_ma_params(self, closes: np.ndarray) -> Dict[str, Any]:
        """建议均线参数"""
        best_sharpe = -999
        best_params = {"fast_period": 20, "slow_period": 60}
        
        for fast in range(10, 30, 5):
            for slow in range(40, 80, 10):
                if fast >= slow:
                    continue
                
                ma_fast = Indicators.SMA(closes, fast)
                ma_slow = Indicators.SMA(closes, slow)
                
                signals = []
                for i in range(1, len(closes)):
                    if np.isnan(ma_fast[i]) or np.isnan(ma_slow[i]):
                        continue
                    if ma_fast[i-1] <= ma_slow[i-1] and ma_fast[i] > ma_slow[i]:
                        signals.append(1)
                    elif ma_fast[i-1] >= ma_slow[i-1] and ma_fast[i] < ma_slow[i]:
                        signals.append(-1)
                
                if len(signals) > 5:
                    sharpe = len(signals) / (np.std(signals) + 1)
                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_params = {"fast_period": fast, "slow_period": slow}
        
        return best_params
    
    def _suggest_rsi_params(self, closes: np.ndarray) -> Dict[str, Any]:
        """建议RSI参数"""
        best_sharpe = -999
        best_params = {"period": 14, "oversold": 30, "overbought": 70}
        
        for period in [9, 14, 21]:
            rsi = Indicators.RSI(closes, period)
            
            valid_rsi = rsi[~np.isnan(rsi)]
            if len(valid_rsi) == 0:
                continue
            
            rsi_std = np.std(valid_rsi)
            sharpe = rsi_std / 20
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params["period"] = period
        
        return best_params
    
    def _suggest_macd_params(self, closes: np.ndarray) -> Dict[str, Any]:
        """建议MACD参数"""
        return {"fast_period": 12, "slow_period": 26, "signal_period": 9}
    
    def _suggest_boll_params(self, closes: np.ndarray) -> Dict[str, Any]:
        """建议布林带参数"""
        return {"period": 20, "std_dev": 2.0}
    
    def chat(self, message: str) -> Dict[str, Any]:
        """
        智能对话接口
        
        Args:
            message: 用户消息
            
        Returns:
            回复内容
        """
        intent = self._detect_intent(message)
        
        response = {
            "intent": intent.value,
            "message": "",
            "data": None,
            "suggestions": [],
        }
        
        if intent == AgentIntent.MARKET_ANALYSIS:
            code = self._extract_code(message)
            if code:
                analysis = self.analyze_market(code)
                response["message"] = self._format_market_analysis(analysis)
                response["data"] = analysis.to_dict()
            else:
                response["message"] = "请提供要分析的证券代码，例如：分析510300的市场情况"
        
        elif intent == AgentIntent.STRATEGY_GENERATION:
            code = self.generate_strategy_code(message)
            response["message"] = "已为您生成策略代码："
            response["data"] = {"code": code}
            response["suggestions"] = [
                "可以尝试回测这个策略",
                "可以调整策略参数",
                "可以添加更多过滤条件",
            ]
        
        elif intent == AgentIntent.GENERAL_QUESTION:
            response["message"] = self._answer_general_question(message)
        
        else:
            response["message"] = "我可以帮您：\n1. 分析市场趋势\n2. 生成量化策略\n3. 解读回测结果\n4. 提供参数优化建议\n\n请告诉我您需要什么帮助？"
        
        return response
    
    def _detect_intent(self, message: str) -> AgentIntent:
        """检测用户意图"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["分析", "趋势", "行情", "走势", "市场"]):
            return AgentIntent.MARKET_ANALYSIS
        
        if any(kw in message_lower for kw in ["生成", "创建", "写", "帮我", "策略"]):
            return AgentIntent.STRATEGY_GENERATION
        
        if any(kw in message_lower for kw in ["回测", "结果", "表现", "收益"]):
            return AgentIntent.BACKTEST_ANALYSIS
        
        if any(kw in message_lower for kw in ["风险", "评估", "安全"]):
            return AgentIntent.RISK_ASSESSMENT
        
        if any(kw in message_lower for kw in ["优化", "参数", "调整"]):
            return AgentIntent.PARAMETER_OPTIMIZATION
        
        return AgentIntent.GENERAL_QUESTION
    
    def _extract_code(self, message: str) -> Optional[str]:
        """从消息中提取证券代码"""
        codes = re.findall(r'\d{6}', message)
        if codes:
            return codes[0]
        return None
    
    def _format_market_analysis(self, analysis: MarketAnalysis) -> str:
        """格式化市场分析结果"""
        lines = [
            f"📊 {analysis.code} 市场分析报告",
            "=" * 40,
            f"当前价格: {analysis.current_price:.2f}",
            f"市场趋势: {analysis.trend.value}",
            f"趋势强度: {analysis.trend_strength:.1f}",
            f"风险等级: {analysis.risk_level.value}",
            "",
        ]
        
        if analysis.support_levels:
            lines.append(f"支撑位: {', '.join([f'{x:.2f}' for x in analysis.support_levels])}")
        if analysis.resistance_levels:
            lines.append(f"阻力位: {', '.join([f'{x:.2f}' for x in analysis.resistance_levels])}")
        
        lines.append("")
        lines.append("📌 技术指标:")
        ind = analysis.indicators
        if ind.get("rsi"):
            lines.append(f"  RSI(14): {ind['rsi']:.1f}")
        if ind.get("macd_dif"):
            lines.append(f"  MACD: DIF={ind['macd_dif']:.4f}, DEA={ind['macd_dea']:.4f}")
        if ind.get("boll_width"):
            lines.append(f"  布林带宽度: {ind['boll_width']:.1f}%")
        
        if analysis.signals:
            lines.append("")
            lines.append("🔔 交易信号:")
            for signal in analysis.signals[:3]:
                lines.append(f"  • {signal}")
        
        if analysis.recommendations:
            lines.append("")
            lines.append("💡 投资建议:")
            for rec in analysis.recommendations[:3]:
                lines.append(f"  • {rec}")
        
        return "\n".join(lines)
    
    def _answer_general_question(self, message: str) -> str:
        """回答一般问题"""
        message_lower = message.lower()
        
        if "什么是" in message_lower or "介绍" in message_lower:
            if "均线" in message_lower:
                return """📈 均线(MA)介绍

均线是最常用的技术指标之一，通过计算一段时间内的平均价格来平滑价格波动。

常用均线:
• MA5: 短期趋势，适合短线交易
• MA20: 中期趋势，月线级别
• MA60: 长期趋势，季度级别

交易信号:
• 金叉: 短期均线上穿长期均线，买入信号
• 死叉: 短期均线下穿长期均线，卖出信号
• 多头排列: MA5>MA20>MA60，强势上涨
• 空头排列: MA5<MA20<MA60，弱势下跌"""
            
            if "rsi" in message_lower:
                return """📊 RSI相对强弱指标介绍

RSI衡量价格变动的速度和幅度，范围0-100。

超买超卖:
• RSI > 70: 超买区，可能回调
• RSI < 30: 超卖区，可能反弹

交易信号:
• 超卖反弹: RSI从30以下回升
• 超买回落: RSI从70以上回落
• 背离: 价格创新高但RSI未创新高"""
            
            if "macd" in message_lower:
                return """📈 MACD指标介绍

MACD由DIF线、DEA线和MACD柱组成。

组成部分:
• DIF: 快线与慢线的差值
• DEA: DIF的移动平均
• MACD柱: (DIF-DEA)×2

交易信号:
• 金叉: DIF上穿DEA，买入信号
• 死叉: DIF下穿DEA，卖出信号
• 零轴: DIF在零轴上方为多头市场"""
        
        if "怎么" in message_lower or "如何" in message_lower:
            if "选股" in message_lower:
                return """🎯 量化选股建议

基本面筛选:
1. 市值适中，流动性好
2. 盈利稳定，ROE>15%
3. 负债率合理，<60%

技术面筛选:
1. 趋势向上，均线多头排列
2. 量价配合，放量上涨
3. 相对强度高，跑赢大盘

风险控制:
1. 分散投资，不超5只
2. 设置止损，控制回撤
3. 定期调仓，优化组合"""
        
        return "我是量化交易智能助手，可以帮您分析市场、生成策略、解读回测结果。请告诉我您需要什么帮助？"
