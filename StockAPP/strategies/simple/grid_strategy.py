"""
网格交易策略
============
基于价格区间的网格交易策略

策略逻辑:
1. 设定价格区间和网格数量
2. 在每个网格点预设买卖单
3. 价格下跌时逐格买入
4. 价格上涨时逐格卖出
"""

from typing import Optional, Dict, List
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


class GridTradingStrategy(StrategyBase):
    """
    网格交易策略
    
    在设定价格区间内划分网格，低买高卖赚取震荡收益。
    
    【单因子量化】基于单一因子信号交易
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "网格交易策略"
    description = (
        "在设定价格区间内划分网格，低买高卖赚取震荡收益的自动化交易策略。"
        "策略将价格区间划分为若干网格，当价格下跌穿越网格线时分批买入，"
        "当价格上涨穿越网格线时分批卖出。通过频繁的小额交易累积收益，"
        "适合波动较大但整体横盘震荡的市场环境。"
    )
    logic = [
        "1. 设定价格区间和网格数量（如10格）",
        "2. 计算网格间距 = (上限 - 下限) / 网格数",
        "3. 在每个网格点预设买卖单",
        "4. 价格下跌穿越网格线：买入一份",
        "5. 价格上涨穿越网格线：卖出一份",
        "6. 循环操作，赚取波动收益",
        "7. 支持ATR动态调整网格范围",
    ]
    suitable = "适合震荡市场，价格在一定区间内波动，能够稳定赚取波动收益"
    risk = "单边趋势行情可能导致踏空或套牢，需要设置止损"
    params_info = {
        "grid_num": {
            "default": 10,
            "min": 5,
            "max": 20,
            "step": 1,
            "description": "网格数量，划分的网格数量",
            "type": "slider",
        },
        "price_range": {
            "default": 0.2,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "description": "价格区间，相对当前价格的波动范围",
            "type": "slider",
        },
    }
    
    def __init__(
        self,
        grid_num: int = 10,
        grid_range_pct: float = 0.2,
        position_per_grid: float = 0.1,
        use_atr_range: bool = False,
        atr_period: int = 14
    ):
        super().__init__()
        
        self.grid_num = grid_num
        self.grid_range_pct = grid_range_pct
        self.position_per_grid = position_per_grid
        self.use_atr_range = use_atr_range
        self.atr_period = atr_period
        
        self._grid_levels: Dict[str, List[float]] = {}
        self._base_price: Dict[str, float] = {}
        self._last_grid_idx: Dict[str, int] = {}
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化网格交易策略")
        self.log(f"  网格数量: {self.grid_num}")
        self.log(f"  网格范围: {self.grid_range_pct * 100}%")
        self.log(f"  每格仓位: {self.position_per_grid * 100}%")
    
    def _init_grid(self, code: str, current_price: float, atr: float = None):
        """初始化网格"""
        if code in self._grid_levels:
            return
        
        if self.use_atr_range and atr is not None:
            grid_range = atr * 2
        else:
            grid_range = current_price * self.grid_range_pct
        
        upper = current_price + grid_range
        lower = current_price - grid_range
        
        grid_step = (upper - lower) / self.grid_num
        self._grid_levels[code] = [lower + i * grid_step for i in range(self.grid_num + 1)]
        self._base_price[code] = current_price
        
        idx = int((current_price - lower) / grid_step)
        self._last_grid_idx[code] = min(max(idx, 0), self.grid_num)
        
        self.log(f"初始化网格 {code}: 基准价={current_price:.2f}, 区间=[{lower:.2f}, {upper:.2f}]")
    
    def _get_grid_index(self, code: str, price: float) -> int:
        """获取当前价格所在的网格索引"""
        levels = self._grid_levels.get(code, [])
        if not levels:
            return -1
        
        for i in range(len(levels) - 1):
            if levels[i] <= price < levels[i + 1]:
                return i
        
        if price >= levels[-1]:
            return len(levels) - 1
        return 0
    
    def _update_grid(self, code: str, current_price: float, atr: float = None):
        """动态更新网格"""
        if code not in self._base_price:
            return
        
        base = self._base_price[code]
        
        if self.use_atr_range and atr is not None:
            threshold = atr * 0.5
        else:
            threshold = base * self.grid_range_pct * 0.3
        
        if abs(current_price - base) > threshold:
            self._grid_levels.pop(code, None)
            self._base_price.pop(code, None)
            self._last_grid_idx.pop(code, None)
            self._init_grid(code, current_price, atr)
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        lookback = max(self.atr_period + 5, 30)
        df = self.get_history(bar.code, lookback)
        
        if df.empty or len(df) < lookback:
            return
        
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        
        atr = None
        if self.use_atr_range:
            atr_values = Indicators.ATR(highs, lows, closes, self.atr_period)
            if len(atr_values) > 0:
                atr = atr_values[-1]
        
        current_price = bar.close
        
        if bar.code not in self._grid_levels:
            self._init_grid(bar.code, current_price, atr)
        
        self._update_grid(bar.code, current_price, atr)
        
        current_idx = self._get_grid_index(bar.code, current_price)
        last_idx = self._last_grid_idx.get(bar.code, current_idx)
        
        if current_idx < 0:
            return
        
        if current_idx > last_idx:
            for i in range(last_idx, current_idx):
                if self.has_position(bar.code):
                    self.sell(bar.code, current_price, ratio=self.position_per_grid)
                    self.log(f"网格卖出 {bar.code}, 网格{i}->{i+1}, 价格={current_price:.2f}")
        
        elif current_idx < last_idx:
            for i in range(last_idx, current_idx, -1):
                if self.cash > current_price * 100:
                    self.buy(bar.code, current_price, ratio=self.position_per_grid)
                    self.log(f"网格买入 {bar.code}, 网格{i}->{i-1}, 价格={current_price:.2f}")
        
        self._last_grid_idx[bar.code] = current_idx
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
