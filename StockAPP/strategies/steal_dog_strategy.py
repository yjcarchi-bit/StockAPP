"""
偷鸡摸狗策略 (Steal Dog Strategy)
=================================
基于动量因子的ETF轮动策略（精选版）

策略核心思想:
1. ETF池：黄金ETF、纳指ETF、创业板ETF（3只精选ETF）
2. 动量计算：加权线性回归斜率 × R²
3. 轮动逻辑：持有动量得分最高的ETF
4. 止损机制：亏损8%止损

来源：克隆自聚宽文章 https://www.joinquant.com/post/66658
标题：多策略组合5年440%
作者：鱼树
"""

import numpy as np
import math
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


ETF_POOL = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
]


class StealDogStrategy(StrategyBase):
    """
    偷鸡摸狗策略 (Steal Dog Strategy)
    
    基于动量因子的ETF轮动策略（精选版）。在黄金、纳指、创业板三只ETF之间
    进行动量轮动，持有动量最强的ETF。采用加权线性回归计算动量得分，
    结合止损机制控制风险。
    
    【多因子量化】综合动量和趋势因子进行择时
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "偷鸡摸狗策略"
    description = (
        "基于动量因子的ETF轮动策略（精选版）。在黄金、纳指、创业板三只ETF之间"
        "进行动量轮动，持有动量最强的ETF。采用加权线性回归计算动量得分，"
        "结合止损机制控制风险。适合追求稳健收益的投资者。"
    )
    logic = [
        "1. ETF池：黄金ETF(518880)、纳指ETF(513100)、创业板ETF(159915)",
        "2. 动量计算：加权线性回归斜率 × R²",
        "3. 权重设计：近期数据权重更高（线性递增）",
        "4. 年化收益：斜率 × 250 转换为年化收益率",
        "5. 动量得分 = 年化收益率 × R²（兼顾收益和稳定性）",
        "6. 轮动逻辑：每日检查，持有得分最高的ETF",
        "7. 止损机制：亏损超过8%止损",
    ]
    suitable = "适合追求稳健收益、希望参与多市场配置的投资者"
    risk = "动量反转时可能产生较大回撤，三只ETF均为高风险品种"
    params_info = {
        "lookback_days": {
            "default": 25,
            "min": 10,
            "max": 60,
            "step": 5,
            "description": "回看天数，用于计算动量的历史天数",
            "type": "slider",
        },
        "stop_loss_ratio": {
            "default": 0.08,
            "min": 0.03,
            "max": 0.15,
            "step": 0.01,
            "description": "止损比例，触发止损的跌幅阈值",
            "type": "slider",
        },
        "min_score_threshold": {
            "default": 0.0,
            "min": -1.0,
            "max": 2.0,
            "step": 0.1,
            "description": "最小动量得分阈值",
            "type": "slider",
        },
        "use_stop_loss": {
            "default": True,
            "description": "启用止损机制",
            "type": "boolean",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._lookback_days = 25
        self._stop_loss_ratio = 0.08
        self._min_score_threshold = 0.0
        self._use_stop_loss = True
        
        self._etf_pool: List[Dict] = ETF_POOL
        self._etf_scores: Dict[str, Dict[str, Any]] = {}
        self._position_highs: Dict[str, float] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._lookback_days = self.get_param("lookback_days", 25)
        self._stop_loss_ratio = self.get_param("stop_loss_ratio", 0.08)
        self._min_score_threshold = self.get_param("min_score_threshold", 0.0)
        self._use_stop_loss = self.get_param("use_stop_loss", True)
        
        self._etf_scores = {}
        self._position_highs = {}
        
        self.log(f"策略初始化完成")
        self.log(f"  回看天数: {self._lookback_days}")
        self.log(f"  止损比例: {self._stop_loss_ratio * 100:.0f}%")
        self.log(f"  ETF池: {[e['name'] for e in self._etf_pool]}")
    
    def _calculate_momentum(self, code: str) -> Optional[Dict[str, Any]]:
        """
        计算动量得分
        
        使用加权线性回归计算动量：
        1. 取过去N天收盘价的对数序列
        2. 对时间序列进行加权线性回归（近期权重更高）
        3. 斜率代表动量方向和强度
        4. R²代表趋势的稳定性
        5. 动量得分 = 年化收益率 × R²
        
        Args:
            code: ETF代码
            
        Returns:
            动量得分详情字典
        """
        df = self.get_history(code, self._lookback_days + 10)
        
        if df is None or len(df) < self._lookback_days:
            return None
        
        close = df["close"].values
        
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
            
            return {
                "code": code,
                "current_price": current_price,
                "slope": slope,
                "annualized_return": annualized_return,
                "r_squared": r_squared,
                "score": score,
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
    
    def _check_stop_loss(self) -> None:
        """检查止损"""
        if not self._use_stop_loss:
            return
        
        for code in list(self._portfolio.positions.keys()):
            pos = self._portfolio.get_position(code)
            
            if pos.is_empty:
                continue
            
            if code not in self._etf_scores:
                continue
            
            current_price = self._etf_scores[code]["current_price"]
            
            if code not in self._position_highs:
                self._position_highs[code] = current_price
            else:
                self._position_highs[code] = max(self._position_highs[code], current_price)
            
            if current_price < pos.cost_price * (1 - self._stop_loss_ratio):
                self.sell_all(code, current_price)
                self.log(f"止损卖出: {code}，亏损: {((current_price / pos.cost_price - 1) * 100):.2f}%")
                
                if code in self._position_highs:
                    del self._position_highs[code]
    
    def _select_target_etf(self) -> Optional[str]:
        """
        选择目标ETF
        
        Returns:
            目标ETF代码
        """
        valid_scores = []
        
        for code, score_data in self._etf_scores.items():
            if score_data["score"] >= self._min_score_threshold:
                valid_scores.append((code, score_data["score"]))
        
        if not valid_scores:
            return None
        
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        
        return valid_scores[0][0]
    
    def _rebalance(self) -> None:
        """调仓"""
        target_etf = self._select_target_etf()
        
        current_holdings = [
            code for code in self._portfolio.positions.keys()
            if self.has_position(code)
        ]
        
        for code in current_holdings:
            if code != target_etf:
                if code in self._etf_scores:
                    self.sell_all(code, self._etf_scores[code]["current_price"])
                    self.log(f"轮动卖出: {code}")
                    if code in self._position_highs:
                        del self._position_highs[code]
        
        if target_etf is None:
            return
        
        if self.has_position(target_etf):
            return
        
        if target_etf not in self._etf_scores:
            return
        
        price = self._etf_scores[target_etf]["current_price"]
        name = self._etf_scores[target_etf].get("name", "")
        score = self._etf_scores[target_etf]["score"]
        
        cash = self._portfolio.cash
        if cash < 1000:
            return
        
        amount = int(cash / price / 100) * 100
        if amount <= 0:
            return
        
        if self.buy(target_etf, price, amount, name=name):
            self._position_highs[target_etf] = price
            self.log(f"轮动买入: {target_etf} {name}，动量得分: {score:.4f}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
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
        self.log("\n=== 偷鸡摸狗策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        
        self.log("\n最后动量得分:")
        for code, score_data in sorted(self._etf_scores.items(), key=lambda x: -x[1]["score"]):
            self.log(f"  {score_data['name']}: {score_data['score']:.4f}")
