"""
多ETF轮动策略 (Multi-ETF Rotation Strategy)
==========================================
基于动量因子的多ETF轮动策略（扩展版）

策略核心思想:
1. ETF池：11只精选ETF，覆盖海外、商品、宽基、债券等多个类别
2. 动量计算：加权线性回归斜率 × R²
3. 筛选条件：动量得分在0-5之间
4. 轮动逻辑：持有动量得分最高的ETF

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


ETF_POOL_EXTENDED = [
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "161226", "name": "油气ETF", "type": "商品"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "511090", "name": "国债ETF", "type": "债券"},
    {"code": "159525", "name": "半导体ETF", "type": "行业"},
    {"code": "513130", "name": "恒生科技ETF", "type": "海外"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "159628", "name": "新能源车ETF", "type": "行业"},
]


class MultiETFRotationStrategy(StrategyBase):
    """
    多ETF轮动策略 (Multi-ETF Rotation Strategy)
    
    基于动量因子的多ETF轮动策略（扩展版）。在11只精选ETF之间进行动量轮动，
    覆盖海外、商品、宽基、债券、行业等多个类别。采用加权线性回归计算动量得分，
    通过得分筛选选择最优ETF持有。
    
    【多因子量化】综合动量和趋势因子进行择时
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "多ETF轮动策略"
    description = (
        "基于动量因子的多ETF轮动策略（扩展版）。在11只精选ETF之间进行动量轮动，"
        "覆盖海外（纳指、日经、德国、恒生科技）、商品（黄金、油气、豆粕）、"
        "宽基（创业板）、债券（国债）、行业（半导体、新能源车）等多个类别。"
        "采用加权线性回归计算动量得分，选择动量最强的ETF持有。"
    )
    logic = [
        "1. ETF池：11只精选ETF，覆盖多个资产类别",
        "2. 动量计算：加权线性回归斜率 × R²",
        "3. 权重设计：近期数据权重更高（线性递增）",
        "4. 年化收益：斜率 × 250 转换为年化收益率",
        "5. 动量得分 = 年化收益率 × R²",
        "6. 筛选条件：动量得分在0到5之间",
        "7. 轮动逻辑：每日检查，持有得分最高的ETF",
        "8. 空仓条件：无ETF满足筛选条件时空仓",
    ]
    suitable = "适合追求多元化资产配置、希望参与全球市场投资的投资者"
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
        "min_score_threshold": {
            "default": 0.0,
            "min": -1.0,
            "max": 3.0,
            "step": 0.1,
            "description": "最小动量得分阈值",
            "type": "slider",
        },
        "max_score_threshold": {
            "default": 5.0,
            "min": 2.0,
            "max": 10.0,
            "step": 0.5,
            "description": "最大动量得分阈值（排除过热）",
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
    }
    
    def __init__(self):
        super().__init__()
        
        self._lookback_days = 25
        self._min_score_threshold = 0.0
        self._max_score_threshold = 5.0
        self._holdings_num = 1
        
        self._etf_pool: List[Dict] = ETF_POOL_EXTENDED
        self._etf_scores: Dict[str, Dict[str, Any]] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._lookback_days = self.get_param("lookback_days", 25)
        self._min_score_threshold = self.get_param("min_score_threshold", 0.0)
        self._max_score_threshold = self.get_param("max_score_threshold", 5.0)
        self._holdings_num = self.get_param("holdings_num", 1)
        
        self._etf_scores = {}
        
        self.log(f"策略初始化完成")
        self.log(f"  回看天数: {self._lookback_days}")
        self.log(f"  得分范围: [{self._min_score_threshold}, {self._max_score_threshold}]")
        self.log(f"  持仓数量: {self._holdings_num}")
        self.log(f"  ETF池数量: {len(self._etf_pool)}")
    
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
    
    def _select_target_etfs(self) -> List[str]:
        """
        选择目标ETF列表
        
        Returns:
            目标ETF代码列表
        """
        valid_scores = []
        
        for code, score_data in self._etf_scores.items():
            score = score_data["score"]
            
            if score < self._min_score_threshold:
                continue
            
            if score > self._max_score_threshold:
                continue
            
            valid_scores.append((code, score))
        
        if not valid_scores:
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
        
        if not target_etfs:
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
                self.log(f"轮动买入: {code} {name}，动量得分: {score:.4f}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        self._calculate_all_scores()
        
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
        self.log("\n=== 多ETF轮动策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        
        self.log("\n最后动量得分排名:")
        sorted_scores = sorted(self._etf_scores.items(), key=lambda x: -x[1]["score"])
        for i, (code, score_data) in enumerate(sorted_scores[:5], 1):
            status = "✓" if score_data["score"] >= self._min_score_threshold and score_data["score"] <= self._max_score_threshold else "✗"
            self.log(f"  {i}. {score_data['name']}: {score_data['score']:.4f} {status}")
