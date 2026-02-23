"""
双均线策略
==========
基于快慢均线交叉的趋势跟踪策略

策略逻辑:
1. 计算快线（短期均线）和慢线（长期均线）
2. 快线上穿慢线时买入（金叉）
3. 快线下穿慢线时卖出（死叉）
"""

from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


class DualMAStrategy(StrategyBase):
    """
    双均线策略
    
    经典的趋势跟踪策略。通过快慢均线的交叉来判断买卖时机。
    
    【单因子量化】基于单一因子信号交易
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "双均线策略"
    description = (
        "经典的趋势跟踪策略。通过计算两条不同周期的移动平均线，"
        "利用它们的交叉来判断市场趋势的变化。当短期均线上穿长期均线时形成金叉，"
        "视为买入信号；当短期均线下穿长期均线时形成死叉，视为卖出信号。"
        "该策略简单有效，是技术分析中最基础的趋势判断方法之一。"
    )
    logic = [
        "1. 计算快速均线（短期，如5日、10日）",
        "2. 计算慢速均线（长期，如20日、30日）",
        "3. 金叉信号：快线上穿慢线，表示短期趋势转强，买入",
        "4. 死叉信号：快线下穿慢线，表示短期趋势转弱，卖出",
        "5. 支持SMA（简单移动平均）和EMA（指数移动平均）两种类型",
        "6. EMA对近期价格赋予更高权重，反应更灵敏",
    ]
    suitable = "适合有明显趋势的单边市场，能够有效捕捉中长期趋势行情"
    risk = "震荡市场会产生频繁的假信号，可能导致连续止损"
    params_info = {
        "fast_period": {
            "default": 10,
            "min": 5,
            "max": 30,
            "step": 5,
            "description": "快线周期，快速均线的计算周期",
            "type": "slider",
        },
        "slow_period": {
            "default": 30,
            "min": 20,
            "max": 60,
            "step": 10,
            "description": "慢线周期，慢速均线的计算周期",
            "type": "slider",
        },
        "ma_type": {
            "default": "SMA",
            "options": ["SMA", "EMA"],
            "description": "均线类型，SMA为简单移动平均，EMA为指数移动平均",
            "type": "select",
        },
    }
    
    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
        ma_type: str = "SMA"
    ):
        super().__init__()
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.upper()
        
        self._prev_fast: dict = {}
        self._prev_slow: dict = {}
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化双均线策略")
        self.log(f"  快线周期: {self.fast_period}")
        self.log(f"  慢线周期: {self.slow_period}")
        self.log(f"  均线类型: {self.ma_type}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        closes = self.get_prices(bar.code, self.slow_period + 1)
        
        if len(closes) < self.slow_period + 1:
            return
        
        if self.ma_type == "EMA":
            fast_ma = Indicators.EMA(closes, self.fast_period)
            slow_ma = Indicators.EMA(closes, self.slow_period)
        else:
            fast_ma = Indicators.SMA(closes, self.fast_period)
            slow_ma = Indicators.SMA(closes, self.slow_period)
        
        current_fast = fast_ma[-1]
        current_slow = slow_ma[-1]
        prev_fast = fast_ma[-2]
        prev_slow = slow_ma[-2]
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            if not self.has_position(bar.code):
                self.buy(bar.code, bar.close, ratio=0.95)
                self.log(f"金叉买入 {bar.code}")
        
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if self.has_position(bar.code):
                self.sell_all(bar.code, bar.close)
                self.log(f"死叉卖出 {bar.code}")
        
        self._prev_fast[bar.code] = current_fast
        self._prev_slow[bar.code] = current_slow
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
