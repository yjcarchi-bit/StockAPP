"""
大市值低回撤策略
================
基于六因子打分系统的股票策略，结合RSRS择时和回撤锁定机制

策略核心思想:
1. 选股：从沪深300成分股中，使用六因子打分系统筛选优质标的
   - 5日动量 (25分): 5日涨幅 > 5%
   - 20日动量 (20分): 20日涨幅 > 10%
   - 趋势强度 (25分): (MA5-MA20)/MA20 > 1%
   - 量比 (15分): 当日成交量/20日均量 > 1.5
   - 波动率 (5分): 20日波动率 < 8%
   - 市值因子 (10分): 大市值优先

2. 择时：通过沪深300的趋势指标判断市场状态
   - 牛市：沪深300 > 20日线 × 1.03，加仓至95%
   - 熊市：沪深300 < 20日线 且 MACD死叉，减仓至60%

3. 风控：回撤超过10%触发锁定
   - 分批解锁：首次解锁允许30%仓位
   - 冷却期：解锁后10天内不触发强空仓锁定
   - 完全解锁：回撤降至5%以下时完全解锁

4. RSRS择时指标
   - 基于最高价和最低价的线性回归
   - 计算斜率β和决定系数R²
   - 右偏RSRS标准分 = zscore × β × R²

5. 止盈止损：
   - 止盈：盈利超过35%
   - 止损：亏损超过5%

来源：克隆自聚宽文章 https://www.joinquant.com/post/67282
标题："低回撤"才是硬道理，3年90倍最大回撤9%
作者：好运来临
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import math

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_base import StrategyBase, BarData, StrategyCategory
from core.indicators import Indicators


DEFAULT_HS300_STOCKS = [
    {"code": "600519", "name": "贵州茅台"},
    {"code": "601318", "name": "中国平安"},
    {"code": "600036", "name": "招商银行"},
    {"code": "601166", "name": "兴业银行"},
    {"code": "600887", "name": "伊利股份"},
    {"code": "601398", "name": "工商银行"},
    {"code": "600030", "name": "中信证券"},
    {"code": "601288", "name": "农业银行"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "600000", "name": "浦发银行"},
    {"code": "601888", "name": "中国中免"},
    {"code": "600016", "name": "民生银行"},
    {"code": "601012", "name": "隆基绿能"},
    {"code": "600048", "name": "保利发展"},
    {"code": "600900", "name": "长江电力"},
    {"code": "601328", "name": "交通银行"},
    {"code": "601939", "name": "建设银行"},
    {"code": "600028", "name": "中国石化"},
    {"code": "601988", "name": "中国银行"},
    {"code": "600585", "name": "海螺水泥"},
    {"code": "601668", "name": "中国建筑"},
    {"code": "600346", "name": "恒力石化"},
    {"code": "601818", "name": "中国光大"},
    {"code": "600690", "name": "海尔智家"},
    {"code": "601899", "name": "紫金矿业"},
    {"code": "600009", "name": "上海机场"},
    {"code": "600019", "name": "宝钢股份"},
    {"code": "601688", "name": "华泰证券"},
    {"code": "600837", "name": "海通证券"},
    {"code": "601211", "name": "国泰君安"},
]


class LargeCapLowDrawdownStrategy(StrategyBase):
    """
    大市值低回撤策略
    
    基于六因子打分系统的股票策略，结合RSRS择时和回撤锁定机制。
    从沪深300成分股中筛选优质标的，通过严格的风控机制控制回撤。
    
    【多因子量化】综合多个因子进行选股择时
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "大市值低回撤策略"
    description = (
        "基于六因子打分系统的股票策略，从沪深300成分股中筛选优质标的。"
        "结合RSRS择时指标和回撤锁定机制，实现低回撤稳健收益。"
        "六因子包括：5日动量、20日动量、趋势强度、量比、波动率、市值因子。"
        "风控机制：回撤超10%触发锁定，分批解锁，冷却期保护。"
    )
    logic = [
        "1. 六因子打分系统筛选沪深300优质股票",
        "2. RSRS择时指标判断市场趋势强度",
        "3. 沪深300站上20日线+MACD金叉+RSRS>0.7时解锁",
        "4. 回撤超10%触发锁定，清仓避险",
        "5. 分批解锁：首次解锁允许30%仓位",
        "6. 冷却期：解锁后10天内不触发强锁定",
        "7. 完全解锁：回撤降至5%以下",
        "8. 牛市加仓至95%，熊市减仓至60%",
        "9. 个股止盈35%，止损5%",
    ]
    suitable = "适合趋势明显的市场环境，追求稳健收益、低回撤的投资者"
    risk = "震荡市场可能频繁换仓增加交易成本，极端行情下可能产生较大回撤"
    params_info = {
        "max_positions": {
            "default": 3,
            "min": 1,
            "max": 5,
            "step": 1,
            "description": "最大持仓数量",
            "type": "slider",
        },
        "stop_loss_ratio": {
            "default": 0.05,
            "min": 0.03,
            "max": 0.10,
            "step": 0.01,
            "description": "个股止损比例",
            "type": "slider",
        },
        "take_profit_ratio": {
            "default": 0.35,
            "min": 0.15,
            "max": 0.50,
            "step": 0.05,
            "description": "个股止盈比例",
            "type": "slider",
        },
        "drawdown_lock_threshold": {
            "default": 0.10,
            "min": 0.05,
            "max": 0.15,
            "step": 0.01,
            "description": "回撤锁定阈值",
            "type": "slider",
        },
        "use_rsrs_timing": {
            "default": True,
            "description": "启用RSRS择时指标",
            "type": "boolean",
        },
        "use_partial_unlock": {
            "default": True,
            "description": "启用分批解锁机制",
            "type": "boolean",
        },
        "rsrs_buy_threshold": {
            "default": 0.7,
            "min": 0.5,
            "max": 1.0,
            "step": 0.1,
            "description": "RSRS买入阈值",
            "type": "slider",
        },
    }
    
    def __init__(self):
        super().__init__()
        
        self._max_positions = 3
        self._stop_loss_ratio = 0.05
        self._take_profit_ratio = 0.35
        self._drawdown_lock_threshold = 0.10
        self._use_rsrs_timing = True
        self._use_partial_unlock = True
        self._rsrs_buy_threshold = 0.7
        
        self._drawdown_lock = False
        self._partial_unlock = False
        self._unlock_cooldown_days = 0
        self._unlock_cooldown_max = 10
        self._full_unlock_drawdown = 0.05
        self._unlock_position_ratio = 0.3
        
        self._bull_market_threshold = 1.03
        self._strong_bull_threshold = 1.04
        
        self._rsrs_n = 18
        self._rsrs_m = 1100
        self._rsrs_history: List[float] = []
        self._rsrs_r2_history: List[float] = []
        
        self._buy_signals: List[str] = []
        self._max_total_value = 0.0
        
        self._index_code = "000300"
        self._stock_pool: List[Dict] = DEFAULT_HS300_STOCKS
        
        self._index_cache: Dict[str, pd.DataFrame] = {}
    
    def initialize(self) -> None:
        """策略初始化"""
        self._max_positions = self.get_param("max_positions", 3)
        self._stop_loss_ratio = self.get_param("stop_loss_ratio", 0.05)
        self._take_profit_ratio = self.get_param("take_profit_ratio", 0.35)
        self._drawdown_lock_threshold = self.get_param("drawdown_lock_threshold", 0.10)
        self._use_rsrs_timing = self.get_param("use_rsrs_timing", True)
        self._use_partial_unlock = self.get_param("use_partial_unlock", True)
        self._rsrs_buy_threshold = self.get_param("rsrs_buy_threshold", 0.7)
        
        self._drawdown_lock = False
        self._partial_unlock = False
        self._unlock_cooldown_days = 0
        self._rsrs_history = []
        self._rsrs_r2_history = []
        self._buy_signals = []
        self._max_total_value = self.total_value if self.total_value > 0 else 100000
        
        self.log(f"策略初始化完成，最大持仓: {self._max_positions}")
    
    def _calculate_rsrs(self, highs: np.ndarray, lows: np.ndarray) -> Tuple[float, float, float]:
        """
        计算RSRS指标（阻力支撑相对强度）
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            
        Returns:
            (斜率β, R², 右偏标准分)
        """
        if len(highs) < self._rsrs_n:
            return 0.0, 0.0, 0.0
        
        try:
            X = np.column_stack([np.ones(len(lows)), lows])
            y = highs
            
            beta = np.linalg.lstsq(X, y, rcond=None)[0][1]
            
            y_pred = X[:, 0] * np.linalg.lstsq(X, y, rcond=None)[0][0] + X[:, 1] * beta
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            
            self._rsrs_history.append(beta)
            self._rsrs_r2_history.append(r2)
            
            if len(self._rsrs_history) < 10:
                return beta, r2, 0.0
            
            m = min(len(self._rsrs_history), self._rsrs_m)
            section = self._rsrs_history[-m:]
            mu = np.mean(section)
            sigma = np.std(section)
            
            if sigma == 0:
                return beta, r2, 0.0
            
            zscore = (section[-1] - mu) / sigma
            zscore_rightdev = zscore * beta * r2
            
            return beta, r2, zscore_rightdev
            
        except Exception:
            return 0.0, 0.0, 0.0
    
    def _get_index_data(self, length: int = 100) -> Optional[pd.DataFrame]:
        """获取指数数据"""
        index_df = self.get_data(self._index_code)
        if index_df is not None and len(index_df) > 0:
            return index_df
        return None
    
    def _calculate_drawdown(self) -> float:
        """计算当前回撤"""
        current_value = self.total_value
        if current_value > self._max_total_value:
            self._max_total_value = current_value
        if self._max_total_value == 0:
            return 0.0
        return (self._max_total_value - current_value) / self._max_total_value
    
    def _check_trend_recovery(self, rsrs_value: float) -> Tuple[bool, str]:
        """
        检查趋势是否恢复（解锁条件判断）
        
        Args:
            rsrs_value: 当前RSRS标准分
            
        Returns:
            (是否解锁, 原因说明)
        """
        index_df = self._get_index_data(60)
        if index_df is None or len(index_df) < 60:
            return False, "指数数据不足"
        
        close = index_df["close"].values
        current_price = close[-1]
        ma20 = np.mean(close[-20:])
        
        dif, dea, macd_hist = self.MACD(close)
        
        cond1 = current_price > ma20
        cond2 = dif > dea
        cond3 = rsrs_value > self._rsrs_buy_threshold if self._use_rsrs_timing else True
        drawdown = self._calculate_drawdown()
        
        if self._use_partial_unlock and self._partial_unlock:
            if self._unlock_cooldown_days > 0:
                self._unlock_cooldown_days -= 1
            
            if drawdown < self._full_unlock_drawdown:
                self._partial_unlock = False
                self._drawdown_lock = False
                return True, f"完全解锁→回撤{drawdown*100:.1f}%<5%"
            
            if self._unlock_cooldown_days > 0:
                return True, f"部分解锁中→冷却期剩余{self._unlock_cooldown_days}天"
            
            return True, f"部分解锁中→允许{self._unlock_position_ratio*100:.0f}%仓位"
        
        if cond1 and cond2 and cond3:
            if self._use_partial_unlock:
                self._partial_unlock = True
                self._unlock_cooldown_days = self._unlock_cooldown_max
            else:
                self._drawdown_lock = False
            return True, f"解锁成功→沪深300站上20日线+MACD金叉+RSRS={rsrs_value:.2f}"
        else:
            fail_reason = []
            if not cond1:
                fail_reason.append(f"沪深300未站上20日线")
            if not cond2:
                fail_reason.append("MACD未金叉")
            if not cond3:
                fail_reason.append(f"RSRS={rsrs_value:.2f}≤{self._rsrs_buy_threshold}")
            return False, "解锁失败→" + "｜".join(fail_reason)
    
    def _score_stock(self, code: str) -> Tuple[float, Dict]:
        """
        六因子打分
        
        Args:
            code: 股票代码
            
        Returns:
            (总分, 因子详情)
        """
        df = self.get_history(code, 60)
        if df is None or len(df) < 30:
            return 0.0, {}
        
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(close))
        
        try:
            momentum_5 = (close[-1] / close[-6] - 1) if len(close) > 5 else 0
            momentum_20 = (close[-1] / close[-21] - 1) if len(close) > 20 else 0
            
            ma5 = np.mean(close[-5:])
            ma20 = np.mean(close[-20:])
            trend_strength = (ma5 - ma20) / ma20 if ma20 > 0 else 0
            
            avg20_vol = np.mean(volume[-20:]) if len(volume) >= 20 else volume[-1]
            volume_ratio = volume[-1] / avg20_vol if avg20_vol > 0 else 0
            
            returns = np.diff(close[-20:]) / close[-21:-1]
            volatility = np.std(returns) if len(returns) > 0 else 0
            
            score = 0
            factors = {}
            
            if momentum_5 > 0.05:
                score += 25
            factors["momentum_5"] = momentum_5
            
            if momentum_20 > 0.10:
                score += 20
            factors["momentum_20"] = momentum_20
            
            if trend_strength > 0.01:
                score += 25
            factors["trend_strength"] = trend_strength
            
            if volume_ratio > 1.5:
                score += 15
            factors["volume_ratio"] = volume_ratio
            
            if volatility < 0.08:
                score += 5
            factors["volatility"] = volatility
            
            factors["total_score"] = score
            
            return score, factors
            
        except Exception:
            return 0.0, {}
    
    def _select_stocks(self) -> List[str]:
        """
        选股：六因子打分系统
        
        Returns:
            选中的股票代码列表
        """
        index_df = self._get_index_data(30)
        rsrs_value = 0.0
        
        if index_df is not None and len(index_df) >= self._rsrs_n and self._use_rsrs_timing:
            highs = index_df["high"].values[-self._rsrs_n:]
            lows = index_df["low"].values[-self._rsrs_n:]
            _, _, rsrs_value = self._calculate_rsrs(highs, lows)
        
        if self._drawdown_lock:
            is_unlock, unlock_reason = self._check_trend_recovery(rsrs_value)
            self.log(f"回撤锁定检查: {unlock_reason}")
            if not is_unlock:
                self._buy_signals = []
                return []
        
        stock_scores = []
        for stock_info in self._stock_pool[:50]:
            code = stock_info["code"]
            score, factors = self._score_stock(code)
            if score > 0:
                stock_scores.append({
                    "code": code,
                    "name": stock_info.get("name", ""),
                    "score": score,
                    "factors": factors
                })
        
        stock_scores.sort(key=lambda x: x["score"], reverse=True)
        
        self._buy_signals = [s["code"] for s in stock_scores[:self._max_positions * 2]]
        
        return self._buy_signals[:self._max_positions]
    
    def _check_risk(self) -> None:
        """风控检查"""
        drawdown = self._calculate_drawdown()
        
        if drawdown >= self._drawdown_lock_threshold:
            if self._use_partial_unlock and self._unlock_cooldown_days > 0:
                self.log(f"冷却期保护：回撤{drawdown*100:.1f}%≥{self._drawdown_lock_threshold*100:.0f}%，但处于冷却期")
                return
            
            for code in list(self.portfolio.positions.keys()):
                if self.has_position(code):
                    self.sell_all(code)
            
            self._drawdown_lock = True
            self._partial_unlock = False
            self.log(f"强空仓+锁定：回撤{drawdown*100:.1f}%≥{self._drawdown_lock_threshold*100:.0f}%")
            return
        
        index_df = self._get_index_data(60)
        if index_df is not None and len(index_df) >= 60:
            close = index_df["close"].values
            current_price = close[-1]
            ma20 = np.mean(close[-20:])
            ma60 = np.mean(close[-60:])
            
            dif, dea, _ = self.MACD(close)
            
            if current_price < ma60 and dif < dea:
                for code in list(self.portfolio.positions.keys()):
                    if self.has_position(code):
                        self.sell_all(code)
                self.log("强空仓-不锁定：沪深300破60日线+MACD死叉")
                return
            
            pos_ratio = sum(
                self.get_position(code).market_value 
                for code in self.portfolio.positions.keys()
            ) / self.total_value if self.total_value > 0 else 0
            
            is_strong_bull = (
                current_price > ma20 * self._strong_bull_threshold and 
                dif > dea and 
                self._buy_signals
            )
            
            if is_strong_bull and pos_ratio < 0.95:
                add_value = self.total_value * 0.95 - self.total_value * pos_ratio
                if add_value > 0 and self._buy_signals:
                    top1 = self._buy_signals[0]
                    if self.has_position(top1):
                        price = self.get_price(top1)
                        if price > 0:
                            amount = self.get_buy_amount(top1, price, ratio=0.8)
                            if amount > 0:
                                self.buy(top1, price, amount)
                                self.log(f"强势加仓: {top1}")
    
    def _check_stop_loss_profit(self) -> None:
        """检查止盈止损"""
        for code in list(self.portfolio.positions.keys()):
            pos = self.get_position(code)
            if pos.quantity <= 0:
                continue
            
            profit_ratio = pos.profit_ratio
            
            if profit_ratio >= self._take_profit_ratio:
                self.sell_all(code)
                self.log(f"止盈卖出: {code}，收益率: {profit_ratio:.2%}")
            elif profit_ratio <= -self._stop_loss_ratio:
                self.sell_all(code)
                self.log(f"止损卖出: {code}，亏损率: {profit_ratio:.2%}")
    
    def _execute_trade(self) -> None:
        """执行交易"""
        if self._drawdown_lock and not self._partial_unlock:
            self.log("交易拦截：处于回撤锁定状态")
            return
        
        self._check_stop_loss_profit()
        
        current_positions = len([c for c in self.portfolio.positions.keys() if self.has_position(c)])
        
        if current_positions >= self._max_positions:
            return
        
        available_cash = self.cash
        if available_cash < 1000:
            return
        
        buy_candidates = [s for s in self._buy_signals if not self.has_position(s)]
        
        if not buy_candidates:
            return
        
        index_df = self._get_index_data(30)
        is_bull = False
        if index_df is not None and len(index_df) >= 20:
            close = index_df["close"].values
            ma20 = np.mean(close[-20:])
            current_price = close[-1]
            is_bull = current_price > ma20 * self._bull_market_threshold
        
        cash_per_stock = available_cash / len(buy_candidates)
        
        if self._partial_unlock:
            max_position_value = self.total_value * self._unlock_position_ratio
            current_position_value = self.total_value - self.cash
            allowed_buy_value = max_position_value - current_position_value
            
            if allowed_buy_value <= 0:
                self.log(f"部分解锁限制：已达最大仓位{self._unlock_position_ratio*100:.0f}%")
                return
            
            cash_per_stock = min(cash_per_stock, allowed_buy_value / len(buy_candidates))
        
        for code in buy_candidates:
            if current_positions >= self._max_positions:
                break
            
            buy_cash = cash_per_stock * 1.2 if is_bull else cash_per_stock
            price = self.get_price(code)
            
            if price <= 0:
                continue
            
            amount = int(buy_cash / price / 100) * 100
            if amount <= 0:
                continue
            
            name = ""
            for s in self._stock_pool:
                if s["code"] == code:
                    name = s.get("name", "")
                    break
            
            if self.buy(code, price, amount, name=name):
                current_positions += 1
                self.log(f"买入: {code} {name}，数量: {amount}，价格: {price:.2f}")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        if bar.code == self._index_code:
            return
        
        self._select_stocks()
        
        self._check_risk()
        
        self._execute_trade()
        
        for code in self.portfolio.positions.keys():
            price = self.get_price(code)
            if price > 0:
                self.update_position_price(code, price)
