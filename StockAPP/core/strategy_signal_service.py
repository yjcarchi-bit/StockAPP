"""
策略信号服务模块
================
基于实时数据计算策略信号，支持信号去重和历史记录

特性:
- 实时动量计算
- 信号去重机制
- 信号历史记录
- 防御模式切换
"""

import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .realtime_data import RealtimeQuote, StrategySignal
from .data_source import DataSource


@dataclass
class ETFMetrics:
    """ETF动量指标"""
    code: str
    name: str
    current_price: float
    annualized_return: float
    r_squared: float
    score: float
    short_return: float
    pass_filters: bool
    filter_reasons: List[str]
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "current_price": self.current_price,
            "annualized_return": self.annualized_return,
            "r_squared": self.r_squared,
            "score": self.score,
            "short_return": self.short_return,
            "pass_filters": self.pass_filters,
            "filter_reasons": self.filter_reasons,
        }


class StrategySignalService:
    """
    策略信号服务
    
    基于实时数据计算ETF轮动策略信号
    
    Example:
        >>> service = StrategySignalService(etf_pool)
        >>> signal = await service.calculate_signal()
        >>> history = service.get_signal_history()
    """
    
    def __init__(
        self,
        etf_pool: List[str],
        etf_names: Optional[Dict[str, str]] = None,
        lookback_days: int = 25,
        short_lookback_days: int = 12,
        min_score_threshold: float = 0.0,
        max_score_threshold: float = 6.0,
        defensive_etf: str = "511880",
        loss_threshold: float = 0.97,
        use_short_momentum: bool = True,
        short_momentum_threshold: float = 0.0,
    ):
        """
        初始化策略信号服务
        
        Args:
            etf_pool: ETF代码列表
            etf_names: ETF名称映射
            lookback_days: 回看天数
            short_lookback_days: 短期动量天数
            min_score_threshold: 最小得分阈值
            max_score_threshold: 最大得分阈值
            defensive_etf: 防御ETF代码
            loss_threshold: 近期大跌阈值
            use_short_momentum: 是否使用短期动量过滤
            short_momentum_threshold: 短期动量阈值
        """
        self.etf_pool = etf_pool
        self.etf_names = etf_names or {}
        self.lookback_days = lookback_days
        self.short_lookback_days = short_lookback_days
        self.min_score_threshold = min_score_threshold
        self.max_score_threshold = max_score_threshold
        self.defensive_etf = defensive_etf
        self.loss_threshold = loss_threshold
        self.use_short_momentum = use_short_momentum
        self.short_momentum_threshold = short_momentum_threshold
        
        self.data_source = DataSource()
        self._signal_history: List[StrategySignal] = []
        self._last_signal: Optional[StrategySignal] = None
        self._history_data: Dict[str, np.ndarray] = {}
        self._last_history_update: Optional[datetime] = None
    
    def _get_etf_name(self, code: str) -> str:
        """获取ETF名称"""
        return self.etf_names.get(code, code)
    
    def _load_history_data(self) -> None:
        """加载历史数据"""
        now = datetime.now()
        
        if self._last_history_update:
            if (now - self._last_history_update).total_seconds() < 3600:
                return
        
        lookback = self.lookback_days + 50
        start_date = now - timedelta(days=lookback * 2)
        
        for code in self.etf_pool:
            df = self.data_source.get_etf_history(code, start_date, now)
            if df is not None and len(df) > 0:
                self._history_data[code] = df["close"].values
        
        self._last_history_update = now
    
    def _merge_realtime_data(
        self, 
        history: np.ndarray, 
        realtime_quote: RealtimeQuote
    ) -> np.ndarray:
        """合并历史数据和实时数据"""
        if len(history) == 0:
            return np.array([realtime_quote.price])
        
        last_history_price = history[-1]
        
        if abs(last_history_price - realtime_quote.price) / last_history_price < 0.15:
            return np.append(history, realtime_quote.price)
        else:
            return history
    
    def _calculate_momentum(
        self, 
        closes: np.ndarray
    ) -> tuple:
        """
        计算动量指标
        
        Args:
            closes: 收盘价序列
            
        Returns:
            (annualized_return, r_squared, score)
        """
        recent_days = min(self.lookback_days, len(closes) - 1)
        
        if recent_days < 10:
            return 0.0, 0.0, 0.0
        
        recent_closes = closes[-(recent_days + 1):]
        
        try:
            y = np.log(recent_closes)
            x = np.arange(len(y))
            weights = np.linspace(1, 2, len(y))
            
            slope, intercept = np.polyfit(x, y, 1, w=weights)
            annualized_return = math.exp(slope * 250) - 1
            
            y_pred = slope * x + intercept
            ss_res = np.sum(weights * (y - y_pred) ** 2)
            ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            
            score = annualized_return * r_squared
            
            return annualized_return, r_squared, score
            
        except Exception:
            return 0.0, 0.0, 0.0
    
    def _check_recent_drop(self, closes: np.ndarray) -> bool:
        """
        检查近期是否有大跌
        
        Returns:
            True表示有大跌，应排除
        """
        if len(closes) < 4:
            return False
        
        day1_ratio = closes[-1] / closes[-2]
        day2_ratio = closes[-2] / closes[-3]
        day3_ratio = closes[-3] / closes[-4]
        
        return min(day1_ratio, day2_ratio, day3_ratio) < self.loss_threshold
    
    def _calculate_short_return(self, closes: np.ndarray) -> float:
        """计算短期收益率"""
        if len(closes) < self.short_lookback_days + 1:
            return 0.0
        
        return closes[-1] / closes[-(self.short_lookback_days + 1)] - 1
    
    def calculate_metrics(
        self, 
        code: str, 
        realtime_quote: Optional[RealtimeQuote] = None
    ) -> Optional[ETFMetrics]:
        """
        计算单个ETF的动量指标
        
        Args:
            code: ETF代码
            realtime_quote: 实时行情（可选）
            
        Returns:
            ETFMetrics对象
        """
        self._load_history_data()
        
        history = self._history_data.get(code)
        if history is None or len(history) < 10:
            return None
        
        if realtime_quote:
            closes = self._merge_realtime_data(history, realtime_quote)
        else:
            closes = history
        
        current_price = closes[-1]
        filter_reasons = []
        pass_filters = True
        
        if self._check_recent_drop(closes):
            pass_filters = False
            filter_reasons.append(f"近3日有单日跌幅超{((1-self.loss_threshold)*100):.0f}%")
        
        short_return = self._calculate_short_return(closes)
        
        if self.use_short_momentum:
            if short_return < self.short_momentum_threshold:
                pass_filters = False
                filter_reasons.append(f"短期动量不足: {short_return:.2%}")
        
        annualized_return, r_squared, score = self._calculate_momentum(closes)
        
        if score <= 0 or score >= self.max_score_threshold:
            pass_filters = False
            if score <= 0:
                filter_reasons.append("动量得分为负或零")
            else:
                filter_reasons.append(f"动量得分异常: {score:.2f}")
        
        return ETFMetrics(
            code=code,
            name=self._get_etf_name(code),
            current_price=current_price,
            annualized_return=annualized_return,
            r_squared=r_squared,
            score=score,
            short_return=short_return,
            pass_filters=pass_filters,
            filter_reasons=filter_reasons,
        )
    
    def calculate_all_metrics(
        self, 
        realtime_quotes: Optional[Dict[str, RealtimeQuote]] = None
    ) -> Dict[str, ETFMetrics]:
        """
        计算所有ETF的动量指标
        
        Args:
            realtime_quotes: 实时行情字典
            
        Returns:
            字典，键为代码，值为ETFMetrics
        """
        metrics = {}
        
        for code in self.etf_pool:
            quote = realtime_quotes.get(code) if realtime_quotes else None
            etf_metrics = self.calculate_metrics(code, quote)
            if etf_metrics:
                metrics[code] = etf_metrics
        
        return metrics
    
    def calculate_signal(
        self, 
        realtime_quotes: Optional[Dict[str, RealtimeQuote]] = None
    ) -> StrategySignal:
        """
        计算策略信号
        
        Args:
            realtime_quotes: 实时行情字典
            
        Returns:
            StrategySignal对象
        """
        all_metrics = self.calculate_all_metrics(realtime_quotes)
        
        valid_metrics = [
            (code, m) for code, m in all_metrics.items()
            if m.pass_filters and m.score > 0
        ]
        
        valid_metrics.sort(key=lambda x: x[1].score, reverse=True)
        
        all_scores = [
            {
                "code": m.code,
                "name": m.name,
                "score": m.score,
                "annualized_return": m.annualized_return,
                "r_squared": m.r_squared,
            }
            for _, m in valid_metrics[:10]
        ]
        
        now = datetime.now()
        
        if valid_metrics and valid_metrics[0][1].score >= self.min_score_threshold:
            target_code = valid_metrics[0][0]
            target_metrics = valid_metrics[0][1]
            
            signal = StrategySignal(
                action="buy",
                target_etf=target_code,
                target_name=target_metrics.name,
                score=target_metrics.score,
                reason=f"动量得分最高: {target_metrics.score:.4f}, 年化收益: {target_metrics.annualized_return:.2%}",
                timestamp=now,
                all_scores=all_scores,
            )
        else:
            signal = StrategySignal(
                action="defensive",
                target_etf=self.defensive_etf,
                target_name=self._get_etf_name(self.defensive_etf),
                score=0.0,
                reason="所有ETF动量为负或未通过过滤，进入防御模式",
                timestamp=now,
                all_scores=all_scores,
            )
        
        if self._should_record_signal(signal):
            self._signal_history.append(signal)
            self._last_signal = signal
        
        return signal
    
    def _should_record_signal(self, new_signal: StrategySignal) -> bool:
        """
        判断是否应该记录信号（去重）
        
        Args:
            new_signal: 新信号
            
        Returns:
            True表示应该记录
        """
        if self._last_signal is None:
            return True
        
        if self._last_signal.action != new_signal.action:
            return True
        
        if self._last_signal.target_etf != new_signal.target_etf:
            return True
        
        if new_signal.action == "buy":
            score_change = abs(new_signal.score - self._last_signal.score)
            if score_change > 0.5:
                return True
        
        return False
    
    def get_signal_history(self, limit: int = 100) -> List[StrategySignal]:
        """
        获取信号历史
        
        Args:
            limit: 最大返回数量
            
        Returns:
            信号列表
        """
        return self._signal_history[-limit:]
    
    def get_last_signal(self) -> Optional[StrategySignal]:
        """获取最近一次信号"""
        return self._last_signal
    
    def clear_history(self) -> None:
        """清空信号历史"""
        self._signal_history.clear()
        self._last_signal = None
    
    def refresh_history_data(self) -> None:
        """强制刷新历史数据"""
        self._last_history_update = None
        self._load_history_data()
