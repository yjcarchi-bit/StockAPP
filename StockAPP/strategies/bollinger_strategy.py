"""
布林带策略
==========
基于布林带指标的均值回归策略

策略逻辑:
1. 计算中轨（N日移动平均）
2. 计算上轨（中轨+K倍标准差）
3. 计算下轨（中轨-K倍标准差）
4. 价格触及下轨时买入
5. 价格触及上轨时卖出
"""

from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


class BollingerStrategy(StrategyBase):
    """
    布林带策略
    
    基于布林带指标的均值回归策略。利用价格在通道内的波动特性进行交易。
    
    【单因子量化】基于单一因子信号交易
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "布林带策略"
    description = (
        "基于布林带指标的均值回归策略。布林带由三条轨道线组成："
        "中轨是N日移动平均线，上轨和下轨分别是中轨加减K倍标准差。"
        "价格通常在上下轨之间波动，当价格触及下轨时表示超卖，触及上轨时表示超买。"
        "该策略假设价格会回归均值，在极端位置进行反向操作。"
    )
    logic = [
        "1. 计算中轨：N日移动平均线（默认20日）",
        "2. 计算标准差：N日价格的标准差",
        "3. 上轨 = 中轨 + K × 标准差（默认K=2）",
        "4. 下轨 = 中轨 - K × 标准差",
        "5. 价格触及下轨：超卖信号，买入",
        "6. 价格触及上轨：超买信号，卖出",
        "7. 可选中轨平仓：价格回归中轨时平仓",
    ]
    suitable = "适合震荡市场，价格在一定区间内波动，能够有效捕捉超买超卖机会"
    risk = "突破行情可能导致持续亏损，价格可能沿轨道运行而非回归"
    params_info = {
        "period": {
            "default": 20,
            "min": 10,
            "max": 40,
            "step": 5,
            "description": "布林带周期，移动平均和标准差的计算周期",
            "type": "slider",
        },
        "std_dev": {
            "default": 2,
            "min": 1,
            "max": 3,
            "step": 0.5,
            "description": "标准差倍数，决定通道宽度",
            "type": "slider",
        },
    }
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        use_middle_exit: bool = True
    ):
        super().__init__()
        
        self.period = period
        self.std_dev = std_dev
        self.use_middle_exit = use_middle_exit
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化布林带策略")
        self.log(f"  周期: {self.period}")
        self.log(f"  标准差倍数: {self.std_dev}")
        self.log(f"  中轨平仓: {self.use_middle_exit}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        closes = self.get_prices(bar.code, self.period + 5)
        
        if len(closes) < self.period + 1:
            return
        
        upper, middle, lower = Indicators.BOLL(closes, self.period, self.std_dev)
        
        if len(upper) < 2:
            return
        
        current_close = closes[-1]
        current_upper = upper[-1]
        current_middle = middle[-1]
        current_lower = lower[-1]
        
        prev_close = closes[-2]
        prev_lower = lower[-2]
        prev_upper = upper[-2]
        
        if prev_close <= prev_lower and current_close > current_lower:
            if not self.has_position(bar.code):
                self.buy(bar.code, bar.close, ratio=0.95)
                self.log(f"布林带下轨买入 {bar.code}, 价格={current_close:.2f}, 下轨={current_lower:.2f}")
        
        elif self.has_position(bar.code):
            if current_close >= current_upper:
                self.sell_all(bar.code, bar.close)
                self.log(f"布林带上轨卖出 {bar.code}, 价格={current_close:.2f}, 上轨={current_upper:.2f}")
            
            elif self.use_middle_exit and current_close >= current_middle:
                self.sell_all(bar.code, bar.close)
                self.log(f"布林带中轨卖出 {bar.code}, 价格={current_close:.2f}, 中轨={current_middle:.2f}")
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
