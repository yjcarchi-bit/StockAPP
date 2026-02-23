"""
市场分析器模块
=============
提供深入的市场分析功能，包括：

1. 趋势分析：多周期趋势判断、趋势强度评估
2. 形态识别：K线形态、图表形态识别
3. 支撑阻力：智能识别关键价格位
4. 市场情绪：量价分析、资金流向
5. 多维度评分：综合评分系统

使用示例:
    >>> from core.market_analyzer import MarketAnalyzer
    >>> analyzer = MarketAnalyzer()
    >>> 
    >>> # 综合分析
    >>> report = analyzer.comprehensive_analysis("510300")
    >>> 
    >>> # 趋势分析
    >>> trend = analyzer.analyze_trend(data)
    >>> 
    >>> # 形态识别
    >>> patterns = analyzer.detect_patterns(data)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np

from .indicators import Indicators


class TrendDirection(Enum):
    """趋势方向"""
    STRONG_UP = "强势上涨"
    UP = "上涨"
    WEAK_UP = "弱势上涨"
    SIDEWAYS = "横盘震荡"
    WEAK_DOWN = "弱势下跌"
    DOWN = "下跌"
    STRONG_DOWN = "强势下跌"


class PatternType(Enum):
    """形态类型"""
    BULLISH_ENGULFING = "看涨吞没"
    BEARISH_ENGULFING = "看跌吞没"
    HAMMER = "锤子线"
    INVERTED_HAMMER = "倒锤子线"
    HANGING_MAN = "上吊线"
    SHOOTING_STAR = "流星线"
    MORNING_STAR = "启明星"
    EVENING_STAR = "黄昏星"
    DOJI = "十字星"
    THREE_WHITE_SOLDIERS = "三白兵"
    THREE_BLACK_CROWS = "三只乌鸦"
    DOUBLE_BOTTOM = "双底"
    DOUBLE_TOP = "双顶"
    HEAD_SHOULDERS_BOTTOM = "头肩底"
    HEAD_SHOULDERS_TOP = "头肩顶"
    ASCENDING_TRIANGLE = "上升三角形"
    DESCENDING_TRIANGLE = "下降三角形"


class SignalStrength(Enum):
    """信号强度"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    NEUTRAL = "中性"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    direction: TrendDirection = TrendDirection.SIDEWAYS
    strength: float = 0.0
    duration_days: int = 0
    slope: float = 0.0
    r_squared: float = 0.0
    ma_alignment: str = ""
    price_position: str = ""
    volume_confirmation: bool = False
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "strength": round(self.strength, 2),
            "duration_days": self.duration_days,
            "slope": round(self.slope, 4),
            "r_squared": round(self.r_squared, 4),
            "ma_alignment": self.ma_alignment,
            "price_position": self.price_position,
            "volume_confirmation": self.volume_confirmation,
            "score": round(self.score, 2),
        }


@dataclass
class Pattern:
    """形态识别结果"""
    pattern_type: PatternType
    date: datetime
    price: float
    reliability: float
    signal: SignalStrength
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type.value,
            "date": self.date.isoformat() if self.date else None,
            "price": round(self.price, 2),
            "reliability": round(self.reliability, 2),
            "signal": self.signal.value,
            "description": self.description,
        }


@dataclass
class SupportResistance:
    """支撑阻力分析结果"""
    support_levels: List[Dict[str, Any]] = field(default_factory=list)
    resistance_levels: List[Dict[str, Any]] = field(default_factory=list)
    current_zone: str = ""
    nearest_support: float = 0.0
    nearest_resistance: float = 0.0
    support_strength: float = 0.0
    resistance_strength: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "current_zone": self.current_zone,
            "nearest_support": round(self.nearest_support, 2),
            "nearest_resistance": round(self.nearest_resistance, 2),
            "support_strength": round(self.support_strength, 2),
            "resistance_strength": round(self.resistance_strength, 2),
        }


@dataclass
class MarketSentiment:
    """市场情绪分析结果"""
    overall_sentiment: str = "中性"
    sentiment_score: float = 50.0
    volume_trend: str = ""
    money_flow: str = ""
    volatility_state: str = ""
    fear_greed_index: float = 50.0
    breadth: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_sentiment": self.overall_sentiment,
            "sentiment_score": round(self.sentiment_score, 2),
            "volume_trend": self.volume_trend,
            "money_flow": self.money_flow,
            "volatility_state": self.volatility_state,
            "fear_greed_index": round(self.fear_greed_index, 2),
            "breadth": self.breadth,
        }


@dataclass
class ComprehensiveReport:
    """综合分析报告"""
    code: str
    name: str = ""
    current_price: float = 0.0
    analysis_date: datetime = None
    trend: TrendAnalysis = None
    patterns: List[Pattern] = field(default_factory=list)
    support_resistance: SupportResistance = None
    sentiment: MarketSentiment = None
    indicators: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    overall_score: float = 0.0
    overall_signal: SignalStrength = SignalStrength.NEUTRAL
    recommendation: str = ""
    risk_warning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "current_price": round(self.current_price, 2),
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "trend": self.trend.to_dict() if self.trend else None,
            "patterns": [p.to_dict() for p in self.patterns],
            "support_resistance": self.support_resistance.to_dict() if self.support_resistance else None,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "indicators": self.indicators,
            "signals": self.signals,
            "overall_score": round(self.overall_score, 2),
            "overall_signal": self.overall_signal.value,
            "recommendation": self.recommendation,
            "risk_warning": self.risk_warning,
        }


class MarketAnalyzer:
    """
    市场分析器
    
    提供全面的市场分析功能
    
    Example:
        >>> analyzer = MarketAnalyzer()
        >>> report = analyzer.comprehensive_analysis("510300", data)
        >>> print(report.overall_signal)
    """
    
    def __init__(self):
        self._pattern_reliability = {
            PatternType.BULLISH_ENGULFING: 0.7,
            PatternType.BEARISH_ENGULFING: 0.7,
            PatternType.HAMMER: 0.6,
            PatternType.INVERTED_HAMMER: 0.55,
            PatternType.HANGING_MAN: 0.55,
            PatternType.SHOOTING_STAR: 0.6,
            PatternType.MORNING_STAR: 0.75,
            PatternType.EVENING_STAR: 0.75,
            PatternType.DOJI: 0.5,
            PatternType.THREE_WHITE_SOLDIERS: 0.8,
            PatternType.THREE_BLACK_CROWS: 0.8,
        }
    
    def comprehensive_analysis(
        self,
        code: str,
        data: pd.DataFrame,
        name: str = ""
    ) -> ComprehensiveReport:
        """
        综合分析
        
        Args:
            code: 证券代码
            data: 历史数据DataFrame
            name: 证券名称
            
        Returns:
            ComprehensiveReport对象
        """
        report = ComprehensiveReport(
            code=code,
            name=name,
            analysis_date=datetime.now()
        )
        
        if data is None or data.empty:
            return report
        
        if "close" in data.columns:
            report.current_price = float(data["close"].iloc[-1])
        
        report.trend = self.analyze_trend(data)
        
        report.patterns = self.detect_patterns(data)
        
        report.support_resistance = self.analyze_support_resistance(data)
        
        report.sentiment = self.analyze_sentiment(data)
        
        report.indicators = self._calculate_all_indicators(data)
        
        report.signals = self._generate_signals(report)
        
        report.overall_score, report.overall_signal = self._calculate_overall_score(report)
        
        report.recommendation = self._generate_recommendation(report)
        
        report.risk_warning = self._generate_risk_warning(report)
        
        return report
    
    def analyze_trend(self, data: pd.DataFrame) -> TrendAnalysis:
        """
        趋势分析
        
        Args:
            data: 历史数据
            
        Returns:
            TrendAnalysis对象
        """
        analysis = TrendAnalysis()
        
        if data is None or len(data) < 60:
            return analysis
        
        closes = data["close"].values
        
        ma5 = Indicators.SMA(closes, 5)
        ma10 = Indicators.SMA(closes, 10)
        ma20 = Indicators.SMA(closes, 20)
        ma60 = Indicators.SMA(closes, 60)
        
        current_close = closes[-1]
        current_ma5 = ma5[-1]
        current_ma10 = ma10[-1]
        current_ma20 = ma20[-1]
        current_ma60 = ma60[-1]
        
        if np.isnan(current_ma5) or np.isnan(current_ma60):
            return analysis
        
        if current_ma5 > current_ma10 > current_ma20 > current_ma60:
            analysis.ma_alignment = "完美多头排列"
        elif current_ma5 > current_ma20 > current_ma60:
            analysis.ma_alignment = "多头排列"
        elif current_ma5 < current_ma10 < current_ma20 < current_ma60:
            analysis.ma_alignment = "完美空头排列"
        elif current_ma5 < current_ma20 < current_ma60:
            analysis.ma_alignment = "空头排列"
        else:
            analysis.ma_alignment = "均线交织"
        
        if current_close > current_ma20:
            if current_close > current_ma5:
                analysis.price_position = "强势区域"
            else:
                analysis.price_position = "多头区域"
        else:
            if current_close < current_ma5:
                analysis.price_position = "弱势区域"
            else:
                analysis.price_position = "空头区域"
        
        slope_20 = Indicators.linear_regression_slope(closes[-20:], 20)[-1]
        slope_60 = Indicators.linear_regression_slope(closes[-60:], 60)[-1]
        
        if not np.isnan(slope_20):
            analysis.slope = slope_20
        
        r2_20 = Indicators.r_squared(closes[-20:], 20)[-1]
        if not np.isnan(r2_20):
            analysis.r_squared = r2_20
        
        trend_score = 0
        
        if current_ma5 > current_ma20:
            trend_score += 20
        if current_ma20 > current_ma60:
            trend_score += 20
        if current_close > current_ma20:
            trend_score += 15
        if slope_20 > 0:
            trend_score += 15
        if r2_20 > 0.7:
            trend_score += 10
        
        if "volume" in data.columns:
            volumes = data["volume"].values
            vol_ma5 = Indicators.SMA(volumes, 5)
            if not np.isnan(vol_ma5[-1]):
                recent_vol = np.mean(volumes[-5:])
                if recent_vol > vol_ma5[-1]:
                    trend_score += 10
                    analysis.volume_confirmation = True
        
        analysis.strength = min(100, trend_score)
        
        if trend_score >= 70:
            analysis.direction = TrendDirection.STRONG_UP
        elif trend_score >= 55:
            analysis.direction = TrendDirection.UP
        elif trend_score >= 45:
            analysis.direction = TrendDirection.WEAK_UP
        elif trend_score >= 35:
            analysis.direction = TrendDirection.SIDEWAYS
        elif trend_score >= 25:
            analysis.direction = TrendDirection.WEAK_DOWN
        elif trend_score >= 10:
            analysis.direction = TrendDirection.DOWN
        else:
            analysis.direction = TrendDirection.STRONG_DOWN
        
        analysis.score = trend_score
        
        trend_start = 0
        for i in range(len(closes) - 1, 0, -1):
            if i < 20 or np.isnan(ma20[i]) or np.isnan(ma60[i]):
                break
            if (ma20[i] > ma60[i]) != (ma20[-1] > ma60[-1]):
                trend_start = i
                break
        analysis.duration_days = len(closes) - trend_start
        
        return analysis
    
    def detect_patterns(self, data: pd.DataFrame) -> List[Pattern]:
        """
        形态识别
        
        Args:
            data: 历史数据
            
        Returns:
            形态列表
        """
        patterns = []
        
        if data is None or len(data) < 10:
            return patterns
        
        for i in range(len(data) - 3, len(data)):
            if i < 1:
                continue
            
            pattern = self._detect_single_candle_pattern(data, i)
            if pattern:
                patterns.append(pattern)
            
            if i >= 2:
                pattern = self._detect_double_candle_pattern(data, i)
                if pattern:
                    patterns.append(pattern)
            
            if i >= 3:
                pattern = self._detect_triple_candle_pattern(data, i)
                if pattern:
                    patterns.append(pattern)
        
        return patterns[-5:] if len(patterns) > 5 else patterns
    
    def _detect_single_candle_pattern(self, data: pd.DataFrame, i: int) -> Optional[Pattern]:
        """检测单K线形态"""
        row = data.iloc[i]
        open_price = row.get("open", row["close"])
        high = row.get("high", row["close"])
        low = row.get("low", row["close"])
        close = row["close"]
        
        body = abs(close - open_price)
        upper_shadow = high - max(open_price, close)
        lower_shadow = min(open_price, close) - low
        total_range = high - low
        
        if total_range == 0:
            return None
        
        if body < total_range * 0.1:
            return Pattern(
                pattern_type=PatternType.DOJI,
                date=row.get("date", None),
                price=close,
                reliability=0.5,
                signal=SignalStrength.NEUTRAL,
                description="十字星，市场犹豫不决"
            )
        
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
            prev_close = data.iloc[i-1]["close"]
            signal = SignalStrength.BUY if close < prev_close else SignalStrength.NEUTRAL
            return Pattern(
                pattern_type=PatternType.HAMMER,
                date=row.get("date", None),
                price=close,
                reliability=0.6,
                signal=signal,
                description="锤子线，可能见底反转"
            )
        
        if upper_shadow > body * 2 and lower_shadow < body * 0.5:
            prev_close = data.iloc[i-1]["close"]
            signal = SignalStrength.SELL if close > prev_close else SignalStrength.NEUTRAL
            return Pattern(
                pattern_type=PatternType.SHOOTING_STAR,
                date=row.get("date", None),
                price=close,
                reliability=0.6,
                signal=signal,
                description="流星线，可能见顶反转"
            )
        
        return None
    
    def _detect_double_candle_pattern(self, data: pd.DataFrame, i: int) -> Optional[Pattern]:
        """检测双K线形态"""
        curr = data.iloc[i]
        prev = data.iloc[i-1]
        
        curr_open = curr.get("open", curr["close"])
        curr_close = curr["close"]
        prev_open = prev.get("open", prev["close"])
        prev_close = prev["close"]
        
        prev_body = prev_close - prev_open
        curr_body = curr_close - curr_open
        
        if prev_body < 0 and curr_body > 0:
            if curr_close > prev_open and curr_open < prev_close:
                if abs(curr_body) > abs(prev_body):
                    return Pattern(
                        pattern_type=PatternType.BULLISH_ENGULFING,
                        date=curr.get("date", None),
                        price=curr_close,
                        reliability=0.7,
                        signal=SignalStrength.BUY,
                        description="看涨吞没，强烈买入信号"
                    )
        
        if prev_body > 0 and curr_body < 0:
            if curr_close < prev_open and curr_open > prev_close:
                if abs(curr_body) > abs(prev_body):
                    return Pattern(
                        pattern_type=PatternType.BEARISH_ENGULFING,
                        date=curr.get("date", None),
                        price=curr_close,
                        reliability=0.7,
                        signal=SignalStrength.SELL,
                        description="看跌吞没，强烈卖出信号"
                    )
        
        return None
    
    def _detect_triple_candle_pattern(self, data: pd.DataFrame, i: int) -> Optional[Pattern]:
        """检测三K线形态"""
        if i < 2:
            return None
        
        c1 = data.iloc[i-2]
        c2 = data.iloc[i-1]
        c3 = data.iloc[i]
        
        c1_open = c1.get("open", c1["close"])
        c1_close = c1["close"]
        c2_open = c2.get("open", c2["close"])
        c2_close = c2["close"]
        c3_open = c3.get("open", c3["close"])
        c3_close = c3["close"]
        
        c1_body = c1_close - c1_open
        c2_body = c2_close - c2_open
        c3_body = c3_close - c3_open
        
        if c1_body < 0 and abs(c2_body) < abs(c1_body) * 0.3 and c3_body > 0:
            if c3_close > (c1_open + c1_close) / 2:
                return Pattern(
                    pattern_type=PatternType.MORNING_STAR,
                    date=c3.get("date", None),
                    price=c3_close,
                    reliability=0.75,
                    signal=SignalStrength.STRONG_BUY,
                    description="启明星，底部反转信号"
                )
        
        if c1_body > 0 and abs(c2_body) < abs(c1_body) * 0.3 and c3_body < 0:
            if c3_close < (c1_open + c1_close) / 2:
                return Pattern(
                    pattern_type=PatternType.EVENING_STAR,
                    date=c3.get("date", None),
                    price=c3_close,
                    reliability=0.75,
                    signal=SignalStrength.STRONG_SELL,
                    description="黄昏星，顶部反转信号"
                )
        
        if i >= 4:
            all_bullish = True
            all_bearish = True
            
            for j in range(i-2, i+1):
                row = data.iloc[j]
                open_p = row.get("open", row["close"])
                close_p = row["close"]
                
                if close_p <= open_p:
                    all_bullish = False
                if close_p >= open_p:
                    all_bearish = False
            
            if all_bullish:
                return Pattern(
                    pattern_type=PatternType.THREE_WHITE_SOLDIERS,
                    date=c3.get("date", None),
                    price=c3_close,
                    reliability=0.8,
                    signal=SignalStrength.STRONG_BUY,
                    description="三白兵，强势上涨信号"
                )
            
            if all_bearish:
                return Pattern(
                    pattern_type=PatternType.THREE_BLACK_CROWS,
                    date=c3.get("date", None),
                    price=c3_close,
                    reliability=0.8,
                    signal=SignalStrength.STRONG_SELL,
                    description="三只乌鸦，强势下跌信号"
                )
        
        return None
    
    def analyze_support_resistance(self, data: pd.DataFrame) -> SupportResistance:
        """
        支撑阻力分析
        
        Args:
            data: 历史数据
            
        Returns:
            SupportResistance对象
        """
        sr = SupportResistance()
        
        if data is None or len(data) < 20:
            return sr
        
        closes = data["close"].values
        highs = data["high"].values if "high" in data.columns else closes
        lows = data["low"].values if "low" in data.columns else closes
        current_price = closes[-1]
        
        pivot_levels = self._find_pivot_points(highs, lows, closes)
        
        ma_levels = self._find_ma_levels(closes)
        
        boll_levels = self._find_bollinger_levels(closes)
        
        all_supports = []
        all_resistances = []
        
        for level in pivot_levels:
            if level["price"] < current_price:
                all_supports.append(level)
            else:
                all_resistances.append(level)
        
        for level in ma_levels:
            if level["price"] < current_price:
                all_supports.append(level)
            else:
                all_resistances.append(level)
        
        for level in boll_levels:
            if level["price"] < current_price:
                all_supports.append(level)
            else:
                all_resistances.append(level)
        
        all_supports.sort(key=lambda x: x["price"], reverse=True)
        all_resistances.sort(key=lambda x: x["price"])
        
        sr.support_levels = self._merge_levels(all_supports)[:5]
        sr.resistance_levels = self._merge_levels(all_resistances)[:5]
        
        if sr.support_levels:
            sr.nearest_support = sr.support_levels[0]["price"]
            sr.support_strength = sr.support_levels[0].get("strength", 50)
        
        if sr.resistance_levels:
            sr.nearest_resistance = sr.resistance_levels[0]["price"]
            sr.resistance_strength = sr.resistance_levels[0].get("strength", 50)
        
        if sr.nearest_support and sr.nearest_resistance:
            range_size = sr.nearest_resistance - sr.nearest_support
            price_position = (current_price - sr.nearest_support) / range_size if range_size > 0 else 0.5
            
            if price_position < 0.3:
                sr.current_zone = "支撑区"
            elif price_position > 0.7:
                sr.current_zone = "阻力区"
            else:
                sr.current_zone = "中性区"
        
        return sr
    
    def _find_pivot_points(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> List[Dict]:
        """寻找枢轴点"""
        levels = []
        lookback = min(60, len(closes))
        
        for i in range(2, lookback - 2):
            idx = len(closes) - lookback + i
            
            if highs[idx] > highs[idx-1] and highs[idx] > highs[idx-2] and \
               highs[idx] > highs[idx+1] and highs[idx] > highs[idx+2]:
                levels.append({
                    "price": float(highs[idx]),
                    "type": "pivot_high",
                    "strength": 60,
                    "touches": 1
                })
            
            if lows[idx] < lows[idx-1] and lows[idx] < lows[idx-2] and \
               lows[idx] < lows[idx+1] and lows[idx] < lows[idx+2]:
                levels.append({
                    "price": float(lows[idx]),
                    "type": "pivot_low",
                    "strength": 60,
                    "touches": 1
                })
        
        return levels
    
    def _find_ma_levels(self, closes: np.ndarray) -> List[Dict]:
        """寻找均线位"""
        levels = []
        
        ma20 = Indicators.SMA(closes, 20)
        ma60 = Indicators.SMA(closes, 60)
        
        if not np.isnan(ma20[-1]):
            levels.append({
                "price": float(ma20[-1]),
                "type": "ma20",
                "strength": 50,
                "touches": 1
            })
        
        if not np.isnan(ma60[-1]):
            levels.append({
                "price": float(ma60[-1]),
                "type": "ma60",
                "strength": 60,
                "touches": 1
            })
        
        return levels
    
    def _find_bollinger_levels(self, closes: np.ndarray) -> List[Dict]:
        """寻找布林带位"""
        levels = []
        
        middle, upper, lower = Indicators.BOLL(closes, 20, 2.0)
        
        if not np.isnan(upper[-1]):
            levels.append({
                "price": float(upper[-1]),
                "type": "boll_upper",
                "strength": 55,
                "touches": 1
            })
        
        if not np.isnan(lower[-1]):
            levels.append({
                "price": float(lower[-1]),
                "type": "boll_lower",
                "strength": 55,
                "touches": 1
            })
        
        return levels
    
    def _merge_levels(self, levels: List[Dict], threshold_pct: float = 0.02) -> List[Dict]:
        """合并相近的价位"""
        if not levels:
            return []
        
        merged = []
        current_group = [levels[0]]
        
        for level in levels[1:]:
            if abs(level["price"] - current_group[0]["price"]) / current_group[0]["price"] < threshold_pct:
                current_group.append(level)
            else:
                avg_price = np.mean([l["price"] for l in current_group])
                max_strength = max([l.get("strength", 50) for l in current_group])
                merged.append({
                    "price": round(avg_price, 2),
                    "type": "merged",
                    "strength": min(100, max_strength + len(current_group) * 5),
                    "touches": len(current_group)
                })
                current_group = [level]
        
        if current_group:
            avg_price = np.mean([l["price"] for l in current_group])
            max_strength = max([l.get("strength", 50) for l in current_group])
            merged.append({
                "price": round(avg_price, 2),
                "type": "merged",
                "strength": min(100, max_strength + len(current_group) * 5),
                "touches": len(current_group)
            })
        
        return merged
    
    def analyze_sentiment(self, data: pd.DataFrame) -> MarketSentiment:
        """
        市场情绪分析
        
        Args:
            data: 历史数据
            
        Returns:
            MarketSentiment对象
        """
        sentiment = MarketSentiment()
        
        if data is None or len(data) < 20:
            return sentiment
        
        closes = data["close"].values
        volumes = data["volume"].values if "volume" in data.columns else np.ones(len(closes))
        highs = data["high"].values if "high" in data.columns else closes
        lows = data["low"].values if "low" in data.columns else closes
        
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns[-20:]) * np.sqrt(252) * 100
        
        if volatility > 40:
            sentiment.volatility_state = "高波动"
        elif volatility > 25:
            sentiment.volatility_state = "中等波动"
        else:
            sentiment.volatility_state = "低波动"
        
        vol_ma5 = Indicators.SMA(volumes, 5)
        vol_ma20 = Indicators.SMA(volumes, 20)
        
        if not np.isnan(vol_ma5[-1]) and not np.isnan(vol_ma20[-1]):
            if vol_ma5[-1] > vol_ma20[-1] * 1.5:
                sentiment.volume_trend = "放量"
            elif vol_ma5[-1] < vol_ma20[-1] * 0.7:
                sentiment.volume_trend = "缩量"
            else:
                sentiment.volume_trend = "量能平稳"
        
        obv = Indicators.OBV(closes, volumes)
        if len(obv) > 5:
            obv_slope = (obv[-1] - obv[-5]) / abs(obv[-5]) if obv[-5] != 0 else 0
            if obv_slope > 0.1:
                sentiment.money_flow = "资金流入"
            elif obv_slope < -0.1:
                sentiment.money_flow = "资金流出"
            else:
                sentiment.money_flow = "资金平衡"
        
        rsi = Indicators.RSI(closes, 14)
        if not np.isnan(rsi[-1]):
            sentiment.fear_greed_index = float(rsi[-1])
        
        up_days = np.sum(returns[-20:] > 0)
        down_days = 20 - up_days
        
        if up_days > 14:
            sentiment.breadth = "强势上涨"
        elif up_days > 10:
            sentiment.breadth = "偏强"
        elif down_days > 14:
            sentiment.breadth = "弱势下跌"
        elif down_days > 10:
            sentiment.breadth = "偏弱"
        else:
            sentiment.breadth = "多空平衡"
        
        score = 50
        
        if sentiment.volume_trend == "放量":
            if closes[-1] > closes[-5]:
                score += 10
            else:
                score -= 5
        
        if sentiment.money_flow == "资金流入":
            score += 10
        elif sentiment.money_flow == "资金流出":
            score -= 10
        
        if sentiment.fear_greed_index > 70:
            score -= 5
        elif sentiment.fear_greed_index < 30:
            score += 5
        
        sentiment.sentiment_score = max(0, min(100, score))
        
        if score >= 70:
            sentiment.overall_sentiment = "极度乐观"
        elif score >= 55:
            sentiment.overall_sentiment = "乐观"
        elif score >= 45:
            sentiment.overall_sentiment = "中性"
        elif score >= 30:
            sentiment.overall_sentiment = "悲观"
        else:
            sentiment.overall_sentiment = "极度悲观"
        
        return sentiment
    
    def _calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """计算所有指标"""
        indicators = {}
        
        if data is None or len(data) < 5:
            return indicators
        
        closes = data["close"].values
        highs = data["high"].values if "high" in data.columns else closes
        lows = data["low"].values if "low" in data.columns else closes
        volumes = data["volume"].values if "volume" in data.columns else np.ones(len(closes))
        
        for period in [5, 10, 20, 60]:
            if len(closes) >= period:
                ma = Indicators.SMA(closes, period)
                if not np.isnan(ma[-1]):
                    indicators[f"ma{period}"] = round(float(ma[-1]), 2)
        
        rsi = Indicators.RSI(closes, 14)
        if not np.isnan(rsi[-1]):
            indicators["rsi"] = round(float(rsi[-1]), 2)
        
        dif, dea, macd_bar = Indicators.MACD(closes)
        if not np.isnan(dif[-1]):
            indicators["macd_dif"] = round(float(dif[-1]), 4)
            indicators["macd_dea"] = round(float(dea[-1]), 4)
            indicators["macd_bar"] = round(float(macd_bar[-1]), 4)
        
        middle, upper, lower = Indicators.BOLL(closes, 20, 2.0)
        if not np.isnan(middle[-1]):
            indicators["boll_middle"] = round(float(middle[-1]), 2)
            indicators["boll_upper"] = round(float(upper[-1]), 2)
            indicators["boll_lower"] = round(float(lower[-1]), 2)
            indicators["boll_width"] = round(float((upper[-1] - lower[-1]) / middle[-1] * 100), 2)
        
        atr = Indicators.ATR(highs, lows, closes, 14)
        if not np.isnan(atr[-1]):
            indicators["atr"] = round(float(atr[-1]), 2)
            indicators["atr_pct"] = round(float(atr[-1] / closes[-1] * 100), 2)
        
        k, d, j = Indicators.KDJ(highs, lows, closes)
        if not np.isnan(k[-1]):
            indicators["kdj_k"] = round(float(k[-1]), 2)
            indicators["kdj_d"] = round(float(d[-1]), 2)
            indicators["kdj_j"] = round(float(j[-1]), 2)
        
        obv = Indicators.OBV(closes, volumes)
        if len(obv) > 1:
            indicators["obv"] = float(obv[-1])
        
        return indicators
    
    def _generate_signals(self, report: ComprehensiveReport) -> List[str]:
        """生成交易信号"""
        signals = []
        
        if report.trend:
            if report.trend.direction in [TrendDirection.STRONG_UP, TrendDirection.UP]:
                signals.append(f"趋势信号: {report.trend.direction.value}，趋势强度{report.trend.strength:.0f}")
            elif report.trend.direction in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
                signals.append(f"趋势信号: {report.trend.direction.value}，注意风险")
        
        for pattern in report.patterns:
            if pattern.signal in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
                signals.append(f"形态信号: {pattern.description}")
            elif pattern.signal in [SignalStrength.STRONG_SELL, SignalStrength.SELL]:
                signals.append(f"形态信号: {pattern.description}")
        
        if report.indicators.get("rsi"):
            rsi = report.indicators["rsi"]
            if rsi < 30:
                signals.append(f"RSI超卖: {rsi:.1f}，可能反弹")
            elif rsi > 70:
                signals.append(f"RSI超买: {rsi:.1f}，注意回调")
        
        if report.indicators.get("macd_dif") and report.indicators.get("macd_dea"):
            dif = report.indicators["macd_dif"]
            dea = report.indicators["macd_dea"]
            if dif > dea:
                signals.append("MACD金叉，多头信号")
            else:
                signals.append("MACD死叉，空头信号")
        
        return signals[:5]
    
    def _calculate_overall_score(self, report: ComprehensiveReport) -> Tuple[float, SignalStrength]:
        """计算综合评分"""
        score = 50
        
        if report.trend:
            if report.trend.direction in [TrendDirection.STRONG_UP]:
                score += 20
            elif report.trend.direction == TrendDirection.UP:
                score += 12
            elif report.trend.direction == TrendDirection.WEAK_UP:
                score += 5
            elif report.trend.direction == TrendDirection.WEAK_DOWN:
                score -= 5
            elif report.trend.direction == TrendDirection.DOWN:
                score -= 12
            elif report.trend.direction == TrendDirection.STRONG_DOWN:
                score -= 20
        
        for pattern in report.patterns:
            if pattern.signal == SignalStrength.STRONG_BUY:
                score += 10
            elif pattern.signal == SignalStrength.BUY:
                score += 5
            elif pattern.signal == SignalStrength.SELL:
                score -= 5
            elif pattern.signal == SignalStrength.STRONG_SELL:
                score -= 10
        
        if report.indicators.get("rsi"):
            rsi = report.indicators["rsi"]
            if rsi < 30:
                score += 8
            elif rsi > 70:
                score -= 8
        
        if report.sentiment:
            score += (report.sentiment.sentiment_score - 50) * 0.3
        
        score = max(0, min(100, score))
        
        if score >= 75:
            signal = SignalStrength.STRONG_BUY
        elif score >= 60:
            signal = SignalStrength.BUY
        elif score >= 40:
            signal = SignalStrength.NEUTRAL
        elif score >= 25:
            signal = SignalStrength.SELL
        else:
            signal = SignalStrength.STRONG_SELL
        
        return score, signal
    
    def _generate_recommendation(self, report: ComprehensiveReport) -> str:
        """生成投资建议"""
        recommendations = []
        
        if report.overall_signal == SignalStrength.STRONG_BUY:
            recommendations.append("强烈买入信号，可考虑积极布局")
        elif report.overall_signal == SignalStrength.BUY:
            recommendations.append("买入信号，可考虑逢低建仓")
        elif report.overall_signal == SignalStrength.SELL:
            recommendations.append("卖出信号，建议减仓或观望")
        elif report.overall_signal == SignalStrength.STRONG_SELL:
            recommendations.append("强烈卖出信号，建议离场观望")
        else:
            recommendations.append("中性信号，建议观望或轻仓操作")
        
        if report.support_resistance:
            sr = report.support_resistance
            if sr.current_zone == "支撑区":
                recommendations.append("当前处于支撑区，是较好的买入位置")
            elif sr.current_zone == "阻力区":
                recommendations.append("当前接近阻力位，注意突破或回落")
        
        return "；".join(recommendations)
    
    def _generate_risk_warning(self, report: ComprehensiveReport) -> str:
        """生成风险提示"""
        warnings = []
        
        if report.trend and report.trend.direction in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
            warnings.append("当前处于下跌趋势，注意控制仓位")
        
        if report.indicators.get("boll_width") and report.indicators["boll_width"] > 15:
            warnings.append("市场波动较大，注意风险")
        
        if report.sentiment and report.sentiment.fear_greed_index > 70:
            warnings.append("市场情绪过热，注意回调风险")
        elif report.sentiment and report.sentiment.fear_greed_index < 30:
            warnings.append("市场情绪恐慌，可能存在机会但也伴随风险")
        
        if report.support_resistance:
            sr = report.support_resistance
            if sr.current_zone == "阻力区":
                warnings.append("接近阻力位，突破失败可能回落")
        
        return "；".join(warnings) if warnings else "风险水平适中"
