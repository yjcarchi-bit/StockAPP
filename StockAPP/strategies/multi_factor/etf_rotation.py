"""
ETF轮动策略
===========
基于动量因子的ETF轮动策略（完整版）

策略逻辑:
1. 计算各ETF的加权线性回归斜率和R²值
2. 多重过滤条件：短期动量、MA、RSI、MACD、成交量、布林带
3. 近期大跌排除机制，避免接飞刀
4. 综合评分 = 年化收益率 × R²
5. 持有得分最高的N只ETF
6. ATR动态止损 + 固定比例止损双重保护
7. 触发止损则切换至防御性ETF（货币基金）
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


ETF_POOL_BASIC = [
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "511220", "name": "城投债ETF", "type": "债券"},
]

ETF_POOL_FULL = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "159980", "name": "有色ETF", "type": "商品"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "501018", "name": "南方原油LOF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513500", "name": "标普500ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "513080", "name": "法国ETF", "type": "海外"},
    {"code": "159920", "name": "恒生ETF", "type": "海外"},
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    {"code": "510500", "name": "中证500ETF", "type": "宽基"},
    {"code": "510050", "name": "上证50ETF", "type": "宽基"},
    {"code": "510210", "name": "上证指数ETF", "type": "宽基"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "588080", "name": "科创板50ETF", "type": "宽基"},
    {"code": "159995", "name": "芯片ETF", "type": "行业"},
    {"code": "513050", "name": "中概互联ETF", "type": "行业"},
    {"code": "159852", "name": "半导体ETF", "type": "行业"},
    {"code": "159845", "name": "新能源ETF", "type": "行业"},
    {"code": "515030", "name": "新能源车ETF", "type": "行业"},
    {"code": "159806", "name": "光伏ETF", "type": "行业"},
    {"code": "516160", "name": "新能源ETF", "type": "行业"},
    {"code": "159928", "name": "消费ETF", "type": "行业"},
    {"code": "512670", "name": "国防军工ETF", "type": "行业"},
    {"code": "511010", "name": "国债ETF", "type": "债券"},
    {"code": "511880", "name": "银华日利", "type": "货币"},
]


class ETFRotationStrategy(StrategyBase):
    """
    ETF轮动策略（完整版）
    
    基于动量因子的ETF轮动策略。在多个ETF之间进行比较和选择，持有动量最强的ETF。
    支持多重过滤条件和动态止损机制。
    
    【多因子量化】综合多个因子进行选股择时
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "ETF轮动策略"
    description = (
        "基于动量因子的ETF轮动策略。通过加权线性回归计算各ETF的斜率和R²值来评估动量质量，"
        "支持MA、RSI、MACD、成交量、布林带等多重过滤条件，"
        "具备近期大跌排除机制和ATR跟踪止损功能。"
        "该策略利用统计学方法量化趋势强度，选择趋势最明确、动量最强的ETF进行持有。"
    )
    logic = [
        "1. 计算每个ETF的加权线性回归斜率（近期权重更高）",
        "2. 斜率代表动量方向，正值表示上涨趋势，负值表示下跌趋势",
        "3. 计算R²值评估趋势的稳定性和可靠性",
        "4. 多重过滤：短期动量、MA、RSI、MACD、成交量、布林带",
        "5. 近期大跌排除：近3日有单日跌幅超阈值则排除",
        "6. 综合得分 = 年化收益率 × R²，兼顾收益和稳定性",
        "7. 选择得分最高的ETF持有，定期调仓",
        "8. ATR跟踪止损 + 固定比例止损双重保护",
        "9. 防御ETF豁免部分过滤和止损条件",
        "10. 当所有ETF动量均为负时，切换至货币基金避险",
    ]
    suitable = "适合趋势明显、波动较大的市场环境，能够有效捕捉板块轮动机会"
    risk = "震荡市场可能频繁换仓增加交易成本，趋势反转时可能产生较大回撤"
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
            "max": 5,
            "step": 1,
            "description": "持仓数量，同时持有的ETF数量",
            "type": "slider",
        },
        "stop_loss": {
            "default": 0.05,
            "min": 0.03,
            "max": 0.15,
            "step": 0.01,
            "description": "止损比例，触发止损的跌幅阈值",
            "type": "slider",
        },
        "use_short_momentum": {
            "default": True,
            "description": "启用短期动量过滤",
            "type": "boolean",
        },
        "use_ma_filter": {
            "default": False,
            "description": "启用MA均线过滤",
            "type": "boolean",
        },
        "use_rsi_filter": {
            "default": False,
            "description": "启用RSI过滤",
            "type": "boolean",
        },
        "use_atr_stop": {
            "default": True,
            "description": "启用ATR动态止损",
            "type": "boolean",
        },
        "atr_trailing_stop": {
            "default": False,
            "description": "使用ATR跟踪止损（否则为固定止损）",
            "type": "boolean",
        },
    }
    
    def __init__(
        self,
        lookback_days: int = 25,
        holdings_num: int = 1,
        stop_loss: float = 0.05,
        min_score_threshold: float = 0.0,
        max_score_threshold: float = 6.0,
        defensive_etf: str = "511880",
        use_short_momentum: bool = True,
        short_lookback_days: int = 12,
        short_momentum_threshold: float = 0.0,
        use_atr_stop_loss: bool = True,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        atr_trailing_stop: bool = False,
        atr_exclude_defensive: bool = True,
        use_ma_filter: bool = False,
        ma_short_period: int = 5,
        ma_long_period: int = 25,
        ma_filter_condition: str = "above",
        use_rsi_filter: bool = False,
        rsi_period: int = 6,
        rsi_lookback_days: int = 1,
        rsi_threshold: float = 95,
        use_macd_filter: bool = False,
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
        use_volume_filter: bool = False,
        volume_lookback_days: int = 7,
        volume_threshold: float = 2.0,
        use_bollinger_filter: bool = False,
        bollinger_period: int = 20,
        bollinger_std: float = 2.0,
        bollinger_lookback_days: int = 3,
        loss_threshold: float = 0.97,
        min_money: float = 5000,
    ):
        super().__init__()
        
        self.lookback_days = lookback_days
        self.holdings_num = holdings_num
        self.stop_loss = stop_loss
        self.min_score_threshold = min_score_threshold
        self.max_score_threshold = max_score_threshold
        self.defensive_etf = defensive_etf
        
        self.use_short_momentum = use_short_momentum
        self.short_lookback_days = short_lookback_days
        self.short_momentum_threshold = short_momentum_threshold
        
        self.use_atr_stop_loss = use_atr_stop_loss
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.atr_trailing_stop = atr_trailing_stop
        self.atr_exclude_defensive = atr_exclude_defensive
        
        self.use_ma_filter = use_ma_filter
        self.ma_short_period = ma_short_period
        self.ma_long_period = ma_long_period
        self.ma_filter_condition = ma_filter_condition
        
        self.use_rsi_filter = use_rsi_filter
        self.rsi_period = rsi_period
        self.rsi_lookback_days = rsi_lookback_days
        self.rsi_threshold = rsi_threshold
        
        self.use_macd_filter = use_macd_filter
        self.macd_fast_period = macd_fast_period
        self.macd_slow_period = macd_slow_period
        self.macd_signal_period = macd_signal_period
        
        self.use_volume_filter = use_volume_filter
        self.volume_lookback_days = volume_lookback_days
        self.volume_threshold = volume_threshold
        
        self.use_bollinger_filter = use_bollinger_filter
        self.bollinger_period = bollinger_period
        self.bollinger_std = bollinger_std
        self.bollinger_lookback_days = bollinger_lookback_days
        
        self.loss_threshold = loss_threshold
        self.min_money = min_money
        
        self.position_highs: Dict[str, float] = {}
        self.position_stop_prices: Dict[str, float] = {}
        self.etf_scores: Dict[str, Dict[str, Any]] = {}
        self.etf_metrics: Dict[str, Dict[str, Any]] = {}
    
    def initialize(self) -> None:
        """初始化策略"""
        self.log(f"初始化ETF轮动策略（完整版）")
        self.log(f"  回看天数: {self.lookback_days}")
        self.log(f"  持仓数量: {self.holdings_num}")
        self.log(f"  止损比例: {self.stop_loss}")
        self.log(f"  短期动量过滤: {self.use_short_momentum}")
        self.log(f"  MA过滤: {self.use_ma_filter}")
        self.log(f"  RSI过滤: {self.use_rsi_filter}")
        self.log(f"  ATR止损: {self.use_atr_stop_loss} (跟踪: {self.atr_trailing_stop})")
    
    def on_bar(self, bar: BarData) -> None:
        """K线回调"""
        if self._data is None:
            return
        
        self._calculate_all_metrics()
        
        self._check_stop_loss()
        
        target_etfs = self._select_target_etfs()
        
        self._rebalance(target_etfs, bar)
    
    def _calculate_all_metrics(self) -> None:
        """计算所有ETF的指标"""
        self.etf_metrics = {}
        self.etf_scores = {}
        
        for code in self._data.keys():
            metrics = self._calculate_single_metrics(code)
            if metrics is not None:
                self.etf_metrics[code] = metrics
                self.etf_scores[code] = {
                    "code": code,
                    "current_price": metrics["current_price"],
                    "annualized_return": metrics["annualized_return"],
                    "r_squared": metrics["r_squared"],
                    "score": metrics["score"],
                    "short_return": metrics["short_return"],
                    "atr": metrics["atr"],
                    "pass_all_filters": metrics["pass_all_filters"],
                }
    
    def _calculate_single_metrics(self, code: str) -> Optional[Dict[str, Any]]:
        """计算单个ETF的所有指标"""
        lookback = max(
            self.lookback_days, 
            self.short_lookback_days,
            self.ma_long_period,
            self.rsi_period + self.rsi_lookback_days,
            self.macd_slow_period + self.macd_signal_period,
            self.bollinger_period + self.bollinger_lookback_days,
        ) + 30
        
        df = self.get_history(code, lookback)
        
        if df.empty or len(df) < lookback:
            return None
        
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values if "volume" in df.columns else None
        
        current_price = closes[-1]
        if current_price <= 0:
            return None
        
        filter_results = {}
        
        if self.use_short_momentum and len(closes) > self.short_lookback_days:
            short_return = closes[-1] / closes[-(self.short_lookback_days + 1)] - 1
            filter_results["short_momentum_pass"] = short_return >= self.short_momentum_threshold
            filter_results["short_return"] = short_return
        else:
            filter_results["short_momentum_pass"] = True
            filter_results["short_return"] = 0
        
        if self.use_ma_filter and len(closes) >= self.ma_long_period:
            ma_short = np.mean(closes[-self.ma_short_period:])
            ma_long = np.mean(closes[-self.ma_long_period:])
            if self.ma_filter_condition == "above":
                filter_results["ma_pass"] = ma_short >= ma_long
            else:
                filter_results["ma_pass"] = ma_short <= ma_long
            filter_results["ma_short"] = ma_short
            filter_results["ma_long"] = ma_long
        else:
            filter_results["ma_pass"] = True
        
        if self.use_rsi_filter and len(closes) >= self.rsi_period + self.rsi_lookback_days:
            rsi_values = Indicators.RSI(closes, self.rsi_period)
            if len(rsi_values) >= self.rsi_lookback_days:
                recent_rsi = rsi_values[-self.rsi_lookback_days:]
                rsi_ever_above = np.any(recent_rsi > self.rsi_threshold)
                current_below_ma5 = current_price < np.mean(closes[-5:]) if len(closes) >= 5 else False
                filter_results["rsi_pass"] = not (rsi_ever_above and current_below_ma5)
                filter_results["max_rsi"] = np.max(recent_rsi)
            else:
                filter_results["rsi_pass"] = True
        else:
            filter_results["rsi_pass"] = True
        
        if self.use_macd_filter and len(closes) >= self.macd_slow_period + self.macd_signal_period:
            dif, dea, macd_hist = Indicators.MACD(
                closes, self.macd_fast_period, self.macd_slow_period, self.macd_signal_period
            )
            if len(dif) > 0 and len(dea) > 0:
                filter_results["macd_pass"] = dif[-1] > dea[-1]
                filter_results["dif"] = dif[-1]
                filter_results["dea"] = dea[-1]
            else:
                filter_results["macd_pass"] = True
        else:
            filter_results["macd_pass"] = True
        
        if self.use_volume_filter and volumes is not None and len(volumes) >= self.volume_lookback_days:
            recent_volume = volumes[-1]
            avg_volume = np.mean(volumes[-(self.volume_lookback_days + 1):-1])
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
            filter_results["volume_pass"] = volume_ratio <= self.volume_threshold
            filter_results["volume_ratio"] = volume_ratio
        else:
            filter_results["volume_pass"] = True
        
        if self.use_bollinger_filter and len(closes) >= self.bollinger_period:
            upper, middle, lower = Indicators.BOLL(closes, self.bollinger_period, self.bollinger_std)
            if len(upper) >= self.bollinger_lookback_days:
                recent_upper = upper[-self.bollinger_lookback_days:]
                recent_closes = closes[-self.bollinger_lookback_days:]
                breakthrough = any(recent_closes[i] > recent_upper[i] for i in range(len(recent_closes)))
                ma5 = np.mean(closes[-5:]) if len(closes) >= 5 else current_price
                filter_results["bollinger_pass"] = not (breakthrough and current_price < ma5)
            else:
                filter_results["bollinger_pass"] = True
        else:
            filter_results["bollinger_pass"] = True
        
        recent_days = min(self.lookback_days, len(closes) - 1)
        if recent_days >= 10:
            recent_closes = closes[-(recent_days + 1):]
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
            except Exception:
                annualized_return = 0
                r_squared = 0
                score = 0
            
            if len(closes) >= 4:
                day1_ratio = closes[-1] / closes[-2]
                day2_ratio = closes[-2] / closes[-3]
                day3_ratio = closes[-3] / closes[-4]
                
                if min(day1_ratio, day2_ratio, day3_ratio) < self.loss_threshold:
                    score = 0
                    filter_results["recent_drop_excluded"] = True
                    self.log(f"⚠️ {code} 近3日有单日跌幅超{((1-self.loss_threshold)*100):.0f}%，已排除")
        else:
            annualized_return = 0
            r_squared = 0
            score = 0
        
        atr = 0
        if self.use_atr_stop_loss and len(highs) > self.atr_period:
            atr_values = Indicators.ATR(highs, lows, closes, self.atr_period)
            atr = atr_values[-1] if len(atr_values) > 0 else 0
        
        short_return = filter_results.get("short_return", 0)
        
        pass_all_filters = all([
            filter_results.get("short_momentum_pass", True),
            filter_results.get("ma_pass", True),
            filter_results.get("rsi_pass", True),
            filter_results.get("macd_pass", True),
            filter_results.get("volume_pass", True),
            filter_results.get("bollinger_pass", True),
        ])
        
        return {
            "code": code,
            "current_price": current_price,
            "annualized_return": annualized_return,
            "r_squared": r_squared,
            "score": score,
            "short_return": short_return,
            "atr": atr,
            "pass_all_filters": pass_all_filters,
            "filter_results": filter_results,
            "highs": highs,
            "lows": lows,
            "closes": closes,
        }
    
    def _check_stop_loss(self) -> None:
        """检查止损"""
        for code in list(self._portfolio.positions.keys()):
            pos = self._portfolio.get_position(code)
            
            if pos.is_empty or code not in self.etf_scores:
                continue
            
            score_data = self.etf_scores[code]
            current_price = score_data["current_price"]
            
            if code not in self.position_highs:
                self.position_highs[code] = current_price
            else:
                self.position_highs[code] = max(self.position_highs[code], current_price)
            
            if current_price < pos.cost_price * (1 - self.stop_loss):
                self.sell_all(code, current_price)
                self.log(f"🚨 固定止损卖出 {code}，亏损: {((current_price/pos.cost_price - 1)*100):.2f}%")
                self._clear_position_tracking(code)
                continue
            
            if self.use_atr_stop_loss and score_data["atr"] > 0:
                if self.atr_exclude_defensive and code == self.defensive_etf:
                    continue
                
                if self.atr_trailing_stop:
                    atr_stop = self.position_highs[code] - self.atr_multiplier * score_data["atr"]
                else:
                    atr_stop = pos.cost_price - self.atr_multiplier * score_data["atr"]
                
                self.position_stop_prices[code] = atr_stop
                
                if current_price < atr_stop:
                    self.sell_all(code, current_price)
                    stop_type = "跟踪" if self.atr_trailing_stop else "固定"
                    self.log(f"🚨 ATR{stop_type}止损卖出 {code}，ATR: {score_data['atr']:.3f}")
                    self._clear_position_tracking(code)
    
    def _clear_position_tracking(self, code: str) -> None:
        """清除持仓跟踪数据"""
        if code in self.position_highs:
            del self.position_highs[code]
        if code in self.position_stop_prices:
            del self.position_stop_prices[code]
    
    def _select_target_etfs(self) -> List[str]:
        """选择目标ETF列表"""
        valid_scores = []
        
        for code, score_data in self.etf_scores.items():
            if score_data["score"] <= 0:
                continue
            
            if score_data["score"] >= self.max_score_threshold:
                continue
            
            metrics = self.etf_metrics.get(code)
            if metrics and not metrics.get("pass_all_filters", True):
                continue
            
            if score_data["score"] >= self.min_score_threshold:
                valid_scores.append((code, score_data["score"]))
        
        if not valid_scores:
            if self.defensive_etf in self._data:
                return [self.defensive_etf]
            return []
        
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [code for code, _ in valid_scores[:self.holdings_num]]
    
    def _rebalance(self, target_etfs: List[str], bar: BarData) -> None:
        """调仓"""
        current_holdings = [code for code in self._portfolio.positions.keys() 
                          if not self._portfolio.get_position(code).is_empty]
        
        for code in current_holdings:
            if code not in target_etfs:
                if code in self.etf_scores:
                    self.sell_all(code, self.etf_scores[code]["current_price"])
                    self._clear_position_tracking(code)
        
        if not target_etfs:
            return
        
        total_value = self._portfolio.total_value
        cash_available = self._portfolio.cash
        
        position_value = total_value / len(target_etfs) if target_etfs else 0
        
        for code in target_etfs:
            if code not in self.etf_scores:
                continue
            
            current_pos = self._portfolio.get_position(code)
            current_value = current_pos.quantity * self.etf_scores[code]["current_price"] if not current_pos.is_empty else 0
            
            if not current_pos.is_empty and abs(current_value - position_value) / total_value < 0.05:
                continue
            
            if not current_pos.is_empty:
                self.sell_all(code, self.etf_scores[code]["current_price"])
                self._clear_position_tracking(code)
            
            price = self.etf_scores[code]["current_price"]
            shares = int(position_value / price / 100) * 100
            
            if shares >= 100 and price * shares <= cash_available:
                self.buy(code, price, shares)
                self.position_highs[code] = price
                cash_available -= price * shares
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        self.log("\n=== ETF轮动策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        self.log(f"交易次数: {len([t for t in self._portfolio.trade_history if t['action'] == 'sell'])}")
