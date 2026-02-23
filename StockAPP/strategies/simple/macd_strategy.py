"""
MACD策略
========
基于MACD指标的趋势跟踪策略

策略逻辑:
1. 计算DIF线（快线与慢线的差值）
2. 计算DEA线（DIF的移动平均）
3. DIF上穿DEA（金叉）时买入
4. DIF下穿DEA（死叉）时卖出
"""

from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


class MACDStrategy(StrategyBase):
    """
    MACD策略
    
    基于异同移动平均线(MACD)的趋势跟踪策略。通过DIF和DEA的交叉捕捉趋势变化。
    
    【单因子量化】基于单一因子信号交易
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "MACD策略"
    description = (
        "基于异同移动平均线(MACD)的趋势跟踪策略。MACD是技术分析中最经典的指标之一，"
        "由快线EMA12、慢线EMA26和信号线DEA9组成。DIF线反映短期与长期均线的偏离程度，"
        "DEA线是DIF的平滑处理。当DIF上穿DEA形成金叉时，表示趋势转强；"
        "当DIF下穿DEA形成死叉时，表示趋势转弱。该策略适合捕捉中长线趋势。"
    )
    logic = [
        "1. 计算快速EMA（默认12日）和慢速EMA（默认26日）",
        "2. DIF = 快速EMA - 慢速EMA，反映均线偏离度",
        "3. DEA = DIF的M日EMA（默认9日），即信号线",
        "4. MACD柱 = (DIF - DEA) × 2，反映动能强度",
        "5. 金叉信号：DIF上穿DEA，买入",
        "6. 死叉信号：DIF下穿DEA，卖出",
        "7. 可选柱状图确认：只在柱状图同向时交易",
    ]
    suitable = "适合中长线趋势交易，能够有效过滤短期噪音，捕捉主要趋势"
    risk = "震荡市场信号较多，存在一定滞后性，可能错过最佳入场点"
    params_info = {
        "fast_period": {
            "default": 12,
            "min": 6,
            "max": 20,
            "step": 2,
            "description": "快线周期，快速EMA的计算周期",
            "type": "slider",
        },
        "slow_period": {
            "default": 26,
            "min": 20,
            "max": 40,
            "step": 2,
            "description": "慢线周期，慢速EMA的计算周期",
            "type": "slider",
        },
        "signal_period": {
            "default": 9,
            "min": 5,
            "max": 15,
            "step": 1,
            "description": "信号线周期，DEA的计算周期",
            "type": "slider",
        },
    }
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        use_histogram: bool = True
    ):
        super().__init__()
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.use_histogram = use_histogram
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化MACD策略")
        self.log(f"  快线周期: {self.fast_period}")
        self.log(f"  慢线周期: {self.slow_period}")
        self.log(f"  信号线周期: {self.signal_period}")
        self.log(f"  柱状图确认: {self.use_histogram}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        lookback = max(self.fast_period, self.slow_period) + self.signal_period + 5
        closes = self.get_prices(bar.code, lookback)
        
        if len(closes) < lookback:
            return
        
        dif, dea, macd_hist = Indicators.MACD(
            closes, 
            self.fast_period, 
            self.slow_period, 
            self.signal_period
        )
        
        if len(dif) < 2:
            return
        
        current_dif = dif[-1]
        current_dea = dea[-1]
        prev_dif = dif[-2]
        prev_dea = dea[-2]
        current_hist = macd_hist[-1]
        
        if prev_dif <= prev_dea and current_dif > current_dea:
            if self.use_histogram and current_hist <= 0:
                return
            
            if not self.has_position(bar.code):
                self.buy(bar.code, bar.close, ratio=0.95)
                self.log(f"MACD金叉买入 {bar.code}, DIF={current_dif:.3f}, DEA={current_dea:.3f}")
        
        elif prev_dif >= prev_dea and current_dif < current_dea:
            if self.use_histogram and current_hist >= 0:
                return
            
            if self.has_position(bar.code):
                self.sell_all(bar.code, bar.close)
                self.log(f"MACD死叉卖出 {bar.code}, DIF={current_dif:.3f}, DEA={current_dea:.3f}")
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
