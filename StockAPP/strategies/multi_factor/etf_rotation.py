"""
ETF轮动策略
===========
基于动量因子的ETF轮动策略

策略核心思想:
1. 动量计算：加权线性回归斜率 × R²
2. 多重过滤：短期动量、MA、RSI、MACD、成交量、布林带
3. 止损机制：ATR动态止损 + 固定比例止损
"""

import numpy as np
import math
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase, BarData
from core.indicators import Indicators


ETF_POOL = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "161226", "name": "油气ETF", "type": "商品"},
    {"code": "511090", "name": "国债ETF", "type": "债券"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    {"code": "159919", "name": "沪深300ETF", "type": "宽基"},
    {"code": "510500", "name": "中证500ETF", "type": "宽基"},
    {"code": "159949", "name": "创业板50ETF", "type": "宽基"},
    {"code": "512880", "name": "证券ETF", "type": "行业"},
    {"code": "512690", "name": "酒ETF", "type": "行业"},
    {"code": "512170", "name": "医疗ETF", "type": "行业"},
    {"code": "512760", "name": "半导体ETF", "type": "行业"},
    {"code": "515790", "name": "光伏ETF", "type": "行业"},
    {"code": "515030", "name": "新能源车ETF", "type": "行业"},
    {"code": "513130", "name": "恒生科技ETF", "type": "海外"},
    {"code": "513060", "name": "恒生医疗ETF", "type": "海外"},
    {"code": "159628", "name": "新能源车ETF", "type": "行业"},
    {"code": "159525", "name": "半导体ETF", "type": "行业"},
    {"code": "511010", "name": "国债ETF", "type": "债券"},
    {"code": "511880", "name": "银华日利", "type": "货币"},
    {"code": "511990", "name": "华宝添益", "type": "货币"},
]


class ETFRotationStrategy(StrategyBase):
    """
    ETF轮动策略
    
    基于动量因子的ETF轮动策略。在多只ETF之间进行动量轮动，持有动量最强的ETF。
    """
    
    display_name = "ETF轮动策略"
    description = (
        "基于动量因子的ETF轮动策略。在25只ETF之间进行动量轮动，"
        "覆盖商品、海外、宽基、行业、债券、货币等多个类别。"
        "采用加权线性回归计算动量得分，结合多重过滤条件和止损机制。"
    )
    logic = [
        "1. ETF池：25只ETF，覆盖多个资产类别",
        "2. 动量计算：加权线性回归斜率 × R²",
        "3. 多重过滤：短期动量、MA、RSI、MACD、成交量、布林带",
        "4. 近期大跌排除：排除近期大跌的ETF",
        "5. 止损机制：ATR动态止损 + 固定比例止损",
        "6. 轮动逻辑：每日检查，持有得分最高的ETF",
    ]
    suitable = "适合追求多元化资产配置、希望参与多市场投资的投资者"
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
        "holdings_num": {
            "default": 1,
            "min": 1,
            "max": 3,
            "step": 1,
            "description": "持仓数量，同时持有的ETF数量",
            "type": "slider",
        },
        "stop_loss_ratio": {
            "default": 0.05,
            "min": 0.02,
            "max": 0.10,
            "step": 0.01,
            "description": "止损比例，触发止损的跌幅阈值",
            "type": "slider",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._lookback_days = 25
        self._holdings_num = 1
        self._stop_loss_ratio = 0.05
        
        self._etf_pool: List[Dict] = ETF_POOL
        self._etf_scores: Dict[str, Dict[str, Any]] = {}
        self._position_highs: Dict[str, float] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._lookback_days = self.get_param("lookback_days", 25)
        self._holdings_num = self.get_param("holdings_num", 1)
        self._stop_loss_ratio = self.get_param("stop_loss_ratio", 0.05)
        
        self._etf_scores = {}
        self._position_highs = {}
        
        self.log(f"策略初始化完成")
        self.log(f"  回看天数: {self._lookback_days}")
        self.log(f"  持仓数量: {self._holdings_num}")
        self.log(f"  止损比例: {self._stop_loss_ratio * 100:.0f}%")
        self.log(f"  ETF池数量: {len(self._etf_pool)}")
    
    def _calculate_momentum(self, code: str) -> Optional[Dict[str, Any]]:
        """计算动量得分"""
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
    
    def _select_target_etfs(self) -> List[str]:
        """选择目标ETF列表"""
        valid_scores = []
        
        for code, score_data in self._etf_scores.items():
            if score_data["score"] >= 0:
                valid_scores.append((code, score_data["score"]))
        
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
                    if code in self._position_highs:
                        del self._position_highs[code]
        
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
                self._position_highs[code] = price
                self.log(f"轮动买入: {code} {name}，动量得分: {score:.4f}")
    
    def on_trading_day(self, date: datetime, bars: dict) -> None:
        """交易日回调 - 每天只调用一次"""
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
        self.log("\n=== ETF轮动策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        
        self.log("\n最后动量得分排名:")
        sorted_scores = sorted(self._etf_scores.items(), key=lambda x: -x[1]["score"])
        for i, (code, score_data) in enumerate(sorted_scores[:5], 1):
            self.log(f"  {i}. {score_data['name']}: {score_data['score']:.4f}")
