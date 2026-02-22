"""
RSI策略
=======
基于RSI指标的超买超卖策略

策略逻辑:
1. 计算RSI指标（相对强弱指数）
2. RSI低于超卖阈值时买入
3. RSI高于超买阈值时卖出
"""

from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


class RSIStrategy(StrategyBase):
    """
    RSI策略
    
    基于相对强弱指标(RSI)的超买超卖策略。利用价格过度反应后的均值回归特性。
    
    【单因子量化】基于单一因子信号交易
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "RSI策略"
    description = (
        "基于相对强弱指标(RSI)的超买超卖策略。RSI是衡量价格变动速度和变化幅度的动量指标，"
        "取值范围0-100。当RSI低于超卖阈值时，表示价格可能过度下跌，存在反弹机会；"
        "当RSI高于超买阈值时，表示价格可能过度上涨，存在回调风险。"
        "该策略利用价格过度反应后的均值回归特性进行反向操作。"
    )
    logic = [
        "1. 计算N日RSI指标值（默认14日）",
        "2. RSI取值范围0-100，反映价格变动的相对强度",
        "3. RSI < 超卖阈值（默认30）：表示超卖，买入信号",
        "4. RSI > 超买阈值（默认70）：表示超买，卖出信号",
        "5. 中性区间（30-70）：持有当前仓位，不操作",
        "6. 可根据市场特性调整超买超卖阈值",
    ]
    suitable = "适合震荡市场，价格围绕均值波动的行情，能够有效捕捉短期超调机会"
    risk = "单边趋势市场中可能持续超买或超卖，导致逆势操作产生亏损"
    params_info = {
        "rsi_period": {
            "default": 14,
            "min": 6,
            "max": 30,
            "step": 2,
            "description": "RSI周期，RSI指标的计算周期",
            "type": "slider",
        },
        "oversold": {
            "default": 30,
            "min": 20,
            "max": 40,
            "step": 5,
            "description": "超卖阈值，RSI低于此值视为超卖",
            "type": "slider",
        },
        "overbought": {
            "default": 70,
            "min": 60,
            "max": 80,
            "step": 5,
            "description": "超买阈值，RSI高于此值视为超买",
            "type": "slider",
        },
    }
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0
    ):
        super().__init__()
        
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化RSI策略")
        self.log(f"  RSI周期: {self.rsi_period}")
        self.log(f"  超卖阈值: {self.oversold}")
        self.log(f"  超买阈值: {self.overbought}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        closes = self.get_prices(bar.code, self.rsi_period + 20)
        
        if len(closes) < self.rsi_period + 1:
            return
        
        rsi_values = Indicators.RSI(closes, self.rsi_period)
        
        if len(rsi_values) == 0:
            return
        
        current_rsi = rsi_values[-1]
        
        if current_rsi < self.oversold:
            if not self.has_position(bar.code):
                self.buy(bar.code, bar.close, ratio=0.95)
                self.log(f"RSI超卖买入 {bar.code}, RSI={current_rsi:.1f}")
        
        elif current_rsi > self.overbought:
            if self.has_position(bar.code):
                self.sell_all(bar.code, bar.close)
                self.log(f"RSI超买卖出 {bar.code}, RSI={current_rsi:.1f}")
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
