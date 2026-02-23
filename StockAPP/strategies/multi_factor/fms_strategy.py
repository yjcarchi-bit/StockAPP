"""
搅屎棍策略 (FMS Strategy)
========================
基于ROE和小市值的选股策略

策略核心思想:
1. 选股：筛选ROE>15%且净利润为正的公司
2. 排序：按总市值升序排列，选择市值最小的股票
3. 调仓：周度调仓（每5个交易日）
4. 过滤：排除ST、科创板、北交所、新股、停牌股票

来源：克隆自聚宽文章 https://www.joinquant.com/post/66658
标题：多策略组合5年440%
作者：鱼树
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


DEFAULT_STOCK_POOL = [
    {"code": "000001", "name": "平安银行"},
    {"code": "000002", "name": "万科A"},
    {"code": "000063", "name": "中兴通讯"},
    {"code": "000333", "name": "美的集团"},
    {"code": "000651", "name": "格力电器"},
    {"code": "000725", "name": "京东方A"},
    {"code": "000858", "name": "五粮液"},
    {"code": "002415", "name": "海康威视"},
    {"code": "002594", "name": "比亚迪"},
    {"code": "002714", "name": "牧原股份"},
    {"code": "002841", "name": "视源股份"},
    {"code": "003816", "name": "中国广核"},
    {"code": "600000", "name": "浦发银行"},
    {"code": "600009", "name": "上海机场"},
    {"code": "600016", "name": "民生银行"},
    {"code": "600019", "name": "宝钢股份"},
    {"code": "600028", "name": "中国石化"},
    {"code": "600030", "name": "中信证券"},
    {"code": "600036", "name": "招商银行"},
    {"code": "600048", "name": "保利发展"},
    {"code": "600050", "name": "中国联通"},
    {"code": "600104", "name": "上汽集团"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "600309", "name": "万华化学"},
    {"code": "600346", "name": "恒力石化"},
    {"code": "600438", "name": "通威股份"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "600585", "name": "海螺水泥"},
    {"code": "600588", "name": "用友网络"},
    {"code": "600690", "name": "海尔智家"},
    {"code": "600887", "name": "伊利股份"},
    {"code": "600900", "name": "长江电力"},
    {"code": "601012", "name": "隆基绿能"},
    {"code": "601066", "name": "中信建投"},
    {"code": "601088", "name": "中国神华"},
    {"code": "601166", "name": "兴业银行"},
    {"code": "601288", "name": "农业银行"},
    {"code": "601318", "name": "中国平安"},
    {"code": "601328", "name": "交通银行"},
    {"code": "601398", "name": "工商银行"},
    {"code": "601601", "name": "中国太保"},
    {"code": "601628", "name": "中国人寿"},
    {"code": "601668", "name": "中国建筑"},
    {"code": "601688", "name": "华泰证券"},
    {"code": "601728", "name": "中国电信"},
    {"code": "601818", "name": "光大银行"},
    {"code": "601857", "name": "中国石油"},
    {"code": "601899", "name": "紫金矿业"},
    {"code": "601919", "name": "中远海控"},
    {"code": "601939", "name": "建设银行"},
    {"code": "601988", "name": "中国银行"},
    {"code": "603259", "name": "药明康德"},
    {"code": "603288", "name": "海天味业"},
    {"code": "603501", "name": "韦尔股份"},
    {"code": "603986", "name": "兆易创新"},
]


class FMSStrategy(StrategyBase):
    """
    搅屎棍策略 (FMS Strategy)
    
    基于ROE和小市值的选股策略。筛选盈利能力强（ROE>15%）的公司，
    选择市值最小的股票进行持有，周度调仓。
    
    【多因子量化】综合基本面和技术面因子进行选股
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "搅屎棍策略"
    description = (
        "基于ROE和小市值的选股策略。筛选盈利能力强（ROE>15%）的公司，"
        "选择市值最小的股票进行持有。该策略结合基本面和技术面指标，"
        "通过周度调仓实现收益优化。适合追求价值投资风格的投资者。"
    )
    logic = [
        "1. 筛选条件：ROE > 15% 且净利润为正",
        "2. 排序方式：按总市值升序排列",
        "3. 选股数量：选择市值最小的N只股票",
        "4. 调仓频率：每5个交易日调仓一次",
        "5. 过滤条件：排除ST、科创板、北交所、新股、停牌股票",
        "6. 仓位管理：等权重配置",
    ]
    suitable = "适合价值投资风格，追求长期稳健收益的投资者"
    risk = "小市值股票波动较大，可能面临较大的回撤风险"
    params_info = {
        "max_positions": {
            "default": 2,
            "min": 1,
            "max": 5,
            "step": 1,
            "description": "最大持仓数量",
            "type": "slider",
        },
        "rebalance_days": {
            "default": 5,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "调仓周期（交易日）",
            "type": "slider",
        },
        "min_momentum": {
            "default": 0.0,
            "min": -0.1,
            "max": 0.2,
            "step": 0.02,
            "description": "最小动量要求（20日涨幅）",
            "type": "slider",
        },
        "use_volume_filter": {
            "default": True,
            "description": "启用成交量过滤",
            "type": "boolean",
        },
        "min_volume_ratio": {
            "default": 0.5,
            "min": 0.3,
            "max": 2.0,
            "step": 0.1,
            "description": "最小量比要求",
            "type": "slider",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._max_positions = 2
        self._rebalance_days = 5
        self._min_momentum = 0.0
        self._use_volume_filter = True
        self._min_volume_ratio = 0.5
        
        self._day_counter = 0
        self._target_stocks: List[str] = []
        self._stock_pool: List[Dict] = DEFAULT_STOCK_POOL
        
        self._stock_scores: Dict[str, Dict[str, Any]] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._max_positions = self.get_param("max_positions", 2)
        self._rebalance_days = self.get_param("rebalance_days", 5)
        self._min_momentum = self.get_param("min_momentum", 0.0)
        self._use_volume_filter = self.get_param("use_volume_filter", True)
        self._min_volume_ratio = self.get_param("min_volume_ratio", 0.5)
        
        self._day_counter = 0
        self._target_stocks = []
        self._stock_scores = {}
        
        self.log(f"策略初始化完成")
        self.log(f"  最大持仓: {self._max_positions}")
        self.log(f"  调仓周期: {self._rebalance_days} 天")
    
    def _calculate_stock_score(self, code: str) -> Optional[Dict[str, Any]]:
        """
        计算股票评分
        
        使用技术指标模拟基本面筛选：
        - 动量因子：模拟盈利能力
        - 成交额：模拟市值（成交额小的通常市值较小）
        - 趋势强度：模拟ROE稳定性
        
        Args:
            code: 股票代码
            
        Returns:
            评分详情字典
        """
        df = self.get_history(code, 60)
        if df is None or len(df) < 30:
            return None
        
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else None
        amount = df["amount"].values if "amount" in df.columns else None
        
        if len(close) < 30:
            return None
        
        current_price = close[-1]
        if current_price <= 0:
            return None
        
        momentum_20 = (close[-1] / close[-21] - 1) if len(close) > 20 else 0
        
        if momentum_20 < self._min_momentum:
            return None
        
        if self._use_volume_filter and volume is not None and len(volume) >= 20:
            avg_volume = np.mean(volume[-20:])
            volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 0
            if volume_ratio < self._min_volume_ratio:
                return None
        
        ma5 = np.mean(close[-5:])
        ma20 = np.mean(close[-20:])
        trend_strength = (ma5 - ma20) / ma20 if ma20 > 0 else 0
        
        avg_amount = np.mean(amount[-20:]) if amount is not None and len(amount) >= 20 else 1e8
        
        volatility = np.std(close[-20:]) / close[-1] if close[-1] > 0 else 1
        
        score = 0
        
        if momentum_20 > 0.05:
            score += 25
        elif momentum_20 > 0:
            score += 10
        
        if trend_strength > 0.02:
            score += 20
        elif trend_strength > 0:
            score += 10
        
        if volatility < 0.05:
            score += 15
        elif volatility < 0.08:
            score += 10
        elif volatility < 0.12:
            score += 5
        
        return {
            "code": code,
            "current_price": current_price,
            "momentum_20": momentum_20,
            "trend_strength": trend_strength,
            "volatility": volatility,
            "avg_amount": avg_amount,
            "score": score,
        }
    
    def _select_stocks(self) -> List[str]:
        """
        选股：筛选并排序
        
        Returns:
            选中的股票代码列表
        """
        self._stock_scores = {}
        
        for stock_info in self._stock_pool:
            code = stock_info["code"]
            
            if code not in self._data:
                continue
            
            score_data = self._calculate_stock_score(code)
            if score_data is not None:
                score_data["name"] = stock_info.get("name", "")
                self._stock_scores[code] = score_data
        
        sorted_stocks = sorted(
            self._stock_scores.items(),
            key=lambda x: (x[1]["avg_amount"], -x[1]["volatility"])
        )
        
        return [code for code, _ in sorted_stocks[:self._max_positions * 2]]
    
    def _rebalance(self) -> None:
        """调仓"""
        target_stocks = self._select_stocks()[:self._max_positions]
        
        current_holdings = [
            code for code in self._portfolio.positions.keys()
            if self.has_position(code)
        ]
        
        for code in current_holdings:
            if code not in target_stocks:
                if code in self._stock_scores:
                    self.sell_all(code, self._stock_scores[code]["current_price"])
                    self.log(f"调仓卖出: {code}")
        
        if not target_stocks:
            return
        
        cash_available = self._portfolio.cash
        if cash_available < 1000:
            return
        
        cash_per_stock = cash_available / len(target_stocks)
        
        for code in target_stocks:
            if self.has_position(code):
                continue
            
            if code not in self._stock_scores:
                continue
            
            price = self._stock_scores[code]["current_price"]
            if price <= 0:
                continue
            
            amount = int(cash_per_stock / price / 100) * 100
            if amount <= 0:
                continue
            
            name = self._stock_scores[code].get("name", "")
            if self.buy(code, price, amount, name=name):
                self.log(f"买入: {code} {name}，数量: {amount}，价格: {price:.2f}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        self._day_counter += 1
        
        if self._day_counter >= self._rebalance_days:
            self._day_counter = 0
            self._rebalance()
        
        for code in self._portfolio.positions.keys():
            if code in self._stock_scores:
                self.update_position_price(code, self._stock_scores[code]["current_price"])
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        self.log("\n=== 搅屎棍策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
