#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
克隆自聚宽文章：https://www.joinquant.com/post/67282
标题："低回撤"才是硬道理，3年90倍最大回撤9%
作者：好运来临

优化版本说明：
- 结合RSRS择时指标优化回撤解锁条件
- 解锁条件改为：沪深300站上20日线 + MACD金叉 + RSRS标准分 > 0.7
- RSRS（阻力支撑相对强度）指标基于最高价和最低价的线性回归
- 分批解锁机制：解锁后先允许30%仓位，冷却期10天内不触发强空仓锁定

策略核心思想：
1. 选股：从沪深300成分股中，使用六因子打分系统筛选优质标的
   - 市值因子 (10分): 市值 > 100亿
   - 5日动量 (25分): 5日涨幅 > 5%
   - 20日动量 (20分): 20日涨幅 > 10%
   - 趋势强度 (25分): (MA5-MA20)/MA20 > 1%
   - 量比 (15分): 当日成交量/20日均量 > 1.5
   - 波动率 (5分): 20日波动率 < 8%

2. 择时：通过沪深300的趋势指标判断市场状态
   - 牛市：沪深300 > 20日线 × 1.03，加仓至95%
   - 熊市：沪深300 < 20日线 且 MACD死叉，减仓至60%

3. 风控：回撤超过10%触发锁定
   - 分批解锁：首次解锁允许30%仓位
   - 冷却期：解锁后10天内不触发强空仓锁定
   - 完全解锁：回撤降至5%以下时完全解锁

4. 止盈止损：
   - 止盈：盈利超过35%
   - 止损：亏损超过5%

运行方式：
    /usr/bin/python3 strategy1_大市值低回撤_本地优化.py
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import efinance as ef
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
import os
import sys
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_report_generator import BacktestReportGenerator


def format_date_for_efinance(date_str: str) -> str:
    """
    将日期格式转换为efinance需要的格式
    
    参数:
        date_str: 输入日期字符串，支持 'YYYY-MM-DD' 或 'YYYYMMDD' 格式
    
    返回:
        efinance格式的日期字符串 'YYYYMMDD'
    """
    if '-' in date_str:
        return date_str.replace('-', '')
    return date_str


class Position:
    """
    持仓类
    
    记录单只股票的持仓信息
    
    属性:
        code: 股票代码
        name: 股票名称
        amount: 持仓数量（股数）
        price: 当前价格
        value: 持仓市值
        avg_cost: 平均持仓成本
    """
    def __init__(self, code: str, name: str = ''):
        self.code = code
        self.name = name
        self.amount = 0
        self.price = 0.0
        self.value = 0.0
        self.avg_cost = 0.0
    
    def update_value(self, current_price: float):
        """更新持仓价值"""
        self.price = current_price
        self.value = self.amount * current_price
    
    @property
    def profit_ratio(self) -> float:
        """计算盈亏比例"""
        if self.avg_cost == 0:
            return 0
        return (self.price - self.avg_cost) / self.avg_cost


class Portfolio:
    """
    投资组合类
    
    管理账户的资金和持仓信息
    
    属性:
        positions: 持仓字典，key为股票代码，value为Position对象
        total_value: 账户总资产（现金 + 持仓市值）
        starting_cash: 初始资金
        cash: 可用现金
        max_total_value: 历史最大资产（用于计算回撤）
    """
    def __init__(self, starting_cash: float = 100000.0):
        self.positions: Dict[str, Position] = {}
        self.total_value = starting_cash
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.max_total_value = starting_cash
    
    def update_positions_value(self, prices: Dict[str, float]):
        """更新持仓市值"""
        total_position_value = 0
        for code, position in self.positions.items():
            if code in prices:
                position.update_value(prices[code])
                total_position_value += position.value
        self.total_value = self.cash + total_position_value
        if self.total_value > self.max_total_value:
            self.max_total_value = self.total_value
    
    @property
    def drawdown(self) -> float:
        """计算当前回撤比例"""
        if self.max_total_value == 0:
            return 0
        return (self.max_total_value - self.total_value) / self.max_total_value
    
    @property
    def position_count(self) -> int:
        """返回持仓数量"""
        return len([p for p in self.positions.values() if p.amount > 0])


class Config:
    """
    策略配置类
    
    存储策略运行所需的所有参数配置
    """
    max_positions: int = 3
    stop_loss_ratio: float = 0.05
    take_profit_ratio: float = 0.35
    bull_market_threshold: float = 1.03
    strong_bull_threshold: float = 1.04
    empty_drawdown: float = 0.10
    bull_add_ratio: float = 1.2
    stock_pool_limit: int = 100
    drawdown_lock: bool = False
    buy_signals: List[str] = []
    
    rsrs_n: int = 18
    rsrs_m: int = 1100
    rsrs_buy_threshold: float = 0.7
    rsrs_sell_threshold: float = -0.7
    
    partial_unlock: bool = False
    unlock_position_ratio: float = 0.3
    unlock_cooldown_days: int = 0
    unlock_cooldown_max: int = 10
    full_unlock_drawdown: float = 0.05


class LocalBacktestStrategyOptimized:
    """
    本地回测策略优化版
    
    结合RSRS择时指标优化回撤解锁条件，实现分批解锁机制
    
    主要改进：
    1. 引入RSRS指标计算
    2. 解锁条件增加RSRS标准分 > 0.7
    3. 分批解锁：首次解锁允许30%仓位
    4. 冷却期：解锁后10天内不触发强空仓锁定
    5. 完全解锁：回撤降至5%以下时完全解锁
    
    使用示例:
        strategy = LocalBacktestStrategyOptimized(
            start_date='2024-01-01',
            end_date='2024-12-31',
            initial_cash=100000.0
        )
        strategy.run_backtest()
    """
    
    def __init__(self, start_date: str = None, end_date: str = None, 
                 initial_cash: float = 100000.0):
        """
        初始化回测策略
        
        参数:
            start_date: 回测开始日期，格式 'YYYY-MM-DD'，默认为两年前
            end_date: 回测结束日期，格式 'YYYY-MM-DD'，默认为当前日期
            initial_cash: 初始资金，默认10万元
        """
        self.portfolio = Portfolio(initial_cash)
        self.config = Config()
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_dt = datetime.now() - timedelta(days=730)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        self.start_date = start_date
        self.end_date = end_date
        
        self.trade_days: List[str] = []
        self.index_data: pd.DataFrame = None
        self.stock_data_cache: Dict[str, pd.DataFrame] = {}
        self.hs300_stocks: List[Dict] = []
        
        self.trade_records: List[Dict] = []
        self.daily_values: List[Dict] = []
        
        self.commission_rate = 0.0003
        self.stamp_tax_rate = 0.001
        self.min_commission = 5.0
        
        self.rsrs_ans: List[float] = []
        self.rsrs_ans_r2: List[float] = []
    
    def get_trade_days(self) -> List[str]:
        """
        获取交易日列表
        
        返回:
            交易日日期列表
        """
        print("正在获取交易日历...")
        try:
            beg = format_date_for_efinance(self.start_date)
            end = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history('000300', beg=beg, end=end, klt=101, fqt=1)
            if df is not None and len(df) > 0:
                self.trade_days = df['日期'].tolist()
                print(f"获取到 {len(self.trade_days)} 个交易日")
                return self.trade_days
        except Exception as e:
            print(f"获取交易日历失败: {e}")
        
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        delta = timedelta(days=1)
        current = start
        all_days = []
        while current <= end:
            if current.weekday() < 5:
                all_days.append(current.strftime('%Y-%m-%d'))
            current += delta
        self.trade_days = all_days
        return self.trade_days
    
    def get_index_data(self) -> pd.DataFrame:
        """
        获取沪深300指数历史数据
        
        返回:
            指数历史数据DataFrame
        """
        print("正在获取沪深300指数数据...")
        try:
            start_dt = datetime.strptime(self.start_date, '%Y-%m-%d') - timedelta(days=1500)
            beg = format_date_for_efinance(start_dt.strftime('%Y-%m-%d'))
            end = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history('000300', beg=beg, end=end, klt=101, fqt=1)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                self.index_data = df
                print(f"获取到 {len(df)} 条指数数据")
                return df
        except Exception as e:
            print(f"获取指数数据失败: {e}")
        return pd.DataFrame()
    
    def init_rsrs(self):
        """
        初始化RSRS指标
        
        在回测开始前，预先计算历史RSRS斜率值
        确保回测开始时有足够的历史数据进行标准化
        """
        print("正在初始化RSRS指标...")
        if self.index_data is None or len(self.index_data) == 0:
            print("指数数据为空，无法初始化RSRS")
            return
        
        start_idx = self.trade_days[0] if self.trade_days else self.start_date
        init_data = self.index_data[self.index_data.index < pd.to_datetime(start_idx)]
        
        if len(init_data) < self.config.rsrs_n:
            init_data = self.index_data
        
        highs = init_data['high'].values
        lows = init_data['low'].values
        
        self.rsrs_ans = []
        self.rsrs_ans_r2 = []
        
        for i in range(self.config.rsrs_n, len(highs)):
            data_high = highs[i-self.config.rsrs_n+1:i+1]
            data_low = lows[i-self.config.rsrs_n+1:i+1]
            X = sm.add_constant(data_low)
            model = sm.OLS(data_high, X)
            results = model.fit()
            self.rsrs_ans.append(results.params[1])
            self.rsrs_ans_r2.append(results.rsquared)
        
        print(f"RSRS初始化完成，共计算 {len(self.rsrs_ans)} 个斜率值")
    
    def calculate_rsrs(self, date: str) -> float:
        """
        计算RSRS指标（右偏标准分）
        
        RSRS（阻力支撑相对强度）指标计算步骤:
        1. 取最近N天的最高价和最低价
        2. 进行线性回归: High = α + β × Low
        3. 计算斜率β和决定系数R²
        4. 对斜率进行M天窗口的标准化
        5. 计算右偏RSRS标准分 = zscore × β × R²
        
        参数:
            date: 当前日期
        
        返回:
            右偏RSRS标准分
        """
        if self.index_data is None:
            return 0.0
        
        date_dt = pd.to_datetime(date)
        idx_data = self.index_data[self.index_data.index <= date_dt]
        
        if len(idx_data) < self.config.rsrs_n:
            return 0.0
        
        highs = idx_data['high'].values[-self.config.rsrs_n:]
        lows = idx_data['low'].values[-self.config.rsrs_n:]
        
        X = sm.add_constant(lows)
        model = sm.OLS(highs, X)
        results = model.fit()
        beta = results.params[1]
        r2 = results.rsquared
        
        self.rsrs_ans.append(beta)
        self.rsrs_ans_r2.append(r2)
        
        if len(self.rsrs_ans) < self.config.rsrs_m:
            m = len(self.rsrs_ans)
        else:
            m = self.config.rsrs_m
        
        section = self.rsrs_ans[-m:]
        mu = np.mean(section)
        sigma = np.std(section)
        
        if sigma == 0:
            return 0.0
        
        zscore = (section[-1] - mu) / sigma
        zscore_rightdev = zscore * beta * r2
        
        return zscore_rightdev
    
    def get_hs300_stocks(self) -> List[Dict]:
        """
        获取沪深300成分股列表
        
        返回:
            股票列表，每个元素为 {'code': 代码, 'name': 名称}
        """
        print("正在获取沪深300成分股...")
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and len(df) > 0:
                codes = df['股票代码'].tolist()[:100]
                names = df['股票名称'].tolist()[:100]
                self.hs300_stocks = [{'code': str(c).zfill(6), 'name': str(n)} 
                                     for c, n in zip(codes, names)]
                print(f"获取到 {len(self.hs300_stocks)} 只股票")
                return self.hs300_stocks
        except Exception as e:
            print(f"获取股票列表失败: {e}")
        
        hs300_codes = ['600519', '601318', '600036', '601166', '600887', '601398', 
                       '600030', '601288', '600276', '600000', '601888', '600016',
                       '601012', '600048', '600900', '601328', '601939', '600028',
                       '601988', '600585', '601668', '600346', '601818', '600690']
        hs300_names = ['贵州茅台', '中国平安', '招商银行', '兴业银行', '伊利股份', '工商银行',
                       '中信证券', '农业银行', '恒瑞医药', '浦发银行', '中国中免', '民生银行',
                       '隆基绿能', '保利发展', '长江电力', '交通银行', '建设银行', '中国石化',
                       '中国银行', '海螺水泥', '中国建筑', '恒力石化', '中国光大', '海尔智家']
        self.hs300_stocks = [{'code': c, 'name': n} for c, n in zip(hs300_codes, hs300_names)]
        return self.hs300_stocks
    
    def get_stock_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        参数:
            code: 股票代码
            days: 需要获取的天数
        
        返回:
            股票历史数据DataFrame
        """
        if code in self.stock_data_cache:
            return self.stock_data_cache[code]
        
        try:
            start_dt = datetime.strptime(self.start_date, '%Y-%m-%d') - timedelta(days=days*2)
            beg = format_date_for_efinance(start_dt.strftime('%Y-%m-%d'))
            end = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history(code, beg=beg, end=end, klt=101, fqt=1)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                self.stock_data_cache[code] = df
                return df
        except Exception as e:
            pass
        return None
    
    def get_price_on_date(self, code: str, date: str) -> Optional[float]:
        """
        获取指定日期的股票价格
        
        参数:
            code: 股票代码
            date: 日期
        
        返回:
            股票收盘价
        """
        stock_data = self.get_stock_data(code)
        if stock_data is not None:
            date_dt = pd.to_datetime(date)
            if date_dt in stock_data.index:
                return stock_data.loc[date_dt, 'close']
            else:
                nearest = stock_data.index[stock_data.index <= date_dt]
                if len(nearest) > 0:
                    return stock_data.loc[nearest[-1], 'close']
        return None
    
    def calculate_macd(self, close: pd.Series, fastperiod: int = 12, 
                       slowperiod: int = 26, signalperiod: int = 9) -> Tuple[float, float, float]:
        """
        计算MACD指标
        
        参数:
            close: 收盘价序列
            fastperiod: 快线周期
            slowperiod: 慢线周期
            signalperiod: 信号线周期
        
        返回:
            Tuple[float, float, float]: (DIF, DEA, MACD)
        """
        ema_fast = close.ewm(span=fastperiod, adjust=False).mean()
        ema_slow = close.ewm(span=slowperiod, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signalperiod, adjust=False).mean()
        macd = 2 * (dif - dea)
        return dif.iloc[-1], dea.iloc[-1], macd.iloc[-1]
    
    def calculate_rsi(self, close: pd.Series, n: int = 14) -> float:
        """
        计算RSI指标
        
        参数:
            close: 收盘价序列
            n: 计算周期
        
        返回:
            float: RSI值
        """
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
        loss = loss.replace(0, np.finfo(float).eps)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.replace([np.inf, -np.inf], 100)
        return rsi.iloc[-1] if not rsi.empty else 50
    
    def check_trend_recovery(self, date: str, rsrs_value: float) -> Tuple[bool, str]:
        """
        检查趋势是否恢复（解锁条件判断）- 分批解锁版
        
        解锁条件（需同时满足）：
            1. 沪深300站上20日均线
            2. MACD金叉（DIF > DEA）
            3. RSRS标准分 > 0.7
        
        分批解锁机制：
            - 首次解锁：进入部分解锁状态，允许30%仓位
            - 冷却期：解锁后10天内不会再次触发强空仓锁定
            - 完全解锁：回撤降至5%以下时完全解锁
        
        参数:
            date: 当前日期
            rsrs_value: 当前RSRS标准分
        
        返回:
            Tuple[bool, str]: (是否解锁, 原因说明)
        """
        if self.index_data is None or len(self.index_data) == 0:
            return False, "指数数据为空"
        
        date_dt = pd.to_datetime(date)
        idx_data = self.index_data[self.index_data.index <= date_dt]
        
        if len(idx_data) < 60:
            return False, "数据不足60天"
        
        close = idx_data['close']
        b_current = close.iloc[-1]
        b_ma20 = close.rolling(20).mean().iloc[-1]
        b_macd = self.calculate_macd(close)
        drawdown = self.portfolio.drawdown
        
        cond1 = b_current > b_ma20
        cond2 = b_macd[0] > b_macd[1]
        cond3 = rsrs_value > self.config.rsrs_buy_threshold
        
        if self.config.partial_unlock:
            if self.config.unlock_cooldown_days > 0:
                self.config.unlock_cooldown_days -= 1
            
            if drawdown < self.config.full_unlock_drawdown:
                self.config.partial_unlock = False
                self.config.drawdown_lock = False
                return True, f"完全解锁→回撤{drawdown*100:.1f}%<5%"
            
            if self.config.unlock_cooldown_days > 0:
                return True, f"部分解锁中→冷却期剩余{self.config.unlock_cooldown_days}天"
            
            return True, f"部分解锁中→允许{self.config.unlock_position_ratio*100:.0f}%仓位"
        
        if cond1 and cond2 and cond3:
            self.config.partial_unlock = True
            self.config.unlock_cooldown_days = self.config.unlock_cooldown_max
            return True, f"分批解锁启动→沪深300站上20日线+MACD金叉+RSRS={rsrs_value:.2f}>0.7"
        else:
            fail_reason = []
            if not cond1:
                fail_reason.append(f"沪深300未站上20日线({b_current:.2f}<{b_ma20:.2f})")
            if not cond2:
                fail_reason.append("MACD未金叉")
            if not cond3:
                fail_reason.append(f"RSRS={rsrs_value:.2f}≤0.7")
            return False, "解锁失败→" + "｜".join(fail_reason)
    
    def select_stocks(self, date: str) -> List[str]:
        """
        选股函数
        
        六因子打分系统：
            1. 市值因子 (10分): 市值 > 100亿
            2. 5日动量 (25分): 5日涨幅 > 5%
            3. 20日动量 (20分): 20日涨幅 > 10%
            4. 趋势强度 (25分): (MA5-MA20)/MA20 > 1%
            5. 量比 (15分): 当日成交量/20日均量 > 1.5
            6. 波动率 (5分): 20日波动率 < 8%
        
        参数:
            date: 当前日期
        
        返回:
            List[str]: 买入信号股票代码列表
        """
        rsrs_value = self.calculate_rsrs(date)
        
        if self.config.drawdown_lock:
            is_unlock, unlock_reason = self.check_trend_recovery(date, rsrs_value)
            print(f"  【回撤锁定检查】{unlock_reason}")
            if is_unlock:
                if self.config.partial_unlock:
                    pass
                else:
                    self.config.drawdown_lock = False
            else:
                self.config.buy_signals = []
                return []
        
        if not self.hs300_stocks:
            self.get_hs300_stocks()
        
        stock_data = []
        select_stocks = self.hs300_stocks[:self.config.stock_pool_limit]
        
        for stock_info in select_stocks:
            code = stock_info['code']
            name = stock_info.get('name', '')
            
            hist = self.get_stock_data(code, 60)
            if hist is None or len(hist) < 60:
                continue
            
            date_dt = pd.to_datetime(date)
            hist_to_date = hist[hist.index <= date_dt]
            
            if len(hist_to_date) < 60:
                continue
            
            close = hist_to_date['close']
            volume = hist_to_date['volume']
            
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            momentum_5 = close.iloc[-1] / close.iloc[-6] - 1
            momentum_20 = close.iloc[-1] / close.iloc[-21] - 1
            trend_strength = (ma5 - ma20) / ma20
            volatility = close.rolling(20).std().iloc[-1] / close.iloc[-1]
            avg20_vol = volume.rolling(20).mean().iloc[-1]
            volume_ratio = volume.iloc[-1] / avg20_vol if avg20_vol != 0 else 0
            
            score = 0
            if momentum_5 > 0.05: score += 25
            if momentum_20 > 0.10: score += 20
            if trend_strength > 0.01: score += 25
            if volume_ratio > 1.5: score += 15
            if volatility < 0.08: score += 5
            
            stock_data.append({
                'code': code,
                'name': name,
                'score': score
            })
        
        if stock_data:
            stock_data.sort(key=lambda x: x['score'], reverse=True)
            signals = [s['code'] for s in stock_data[:self.config.max_positions * 2]]
            self.config.buy_signals = signals[:self.config.max_positions]
        else:
            self.config.buy_signals = [s['code'] for s in self.hs300_stocks[:self.config.max_positions]]
        
        return self.config.buy_signals
    
    def calculate_commission(self, amount: float, price: float, is_buy: bool) -> float:
        """
        计算交易费用
        
        参数:
            amount: 交易数量
            price: 交易价格
            is_buy: 是否为买入
        
        返回:
            总交易费用
        """
        trade_value = amount * price
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        if not is_buy:
            stamp_tax = trade_value * self.stamp_tax_rate
            return commission + stamp_tax
        
        return commission
    
    def order_target(self, code: str, target_amount: int, date: str, name: str = ''):
        """
        按目标数量下单
        
        参数:
            code: 股票代码
            target_amount: 目标持仓数量
            date: 交易日期
            name: 股票名称
        """
        current_price = self.get_price_on_date(code, date)
        if current_price is None or current_price <= 0:
            return
        
        current_amount = 0
        if code in self.portfolio.positions:
            current_amount = self.portfolio.positions[code].amount
        
        if target_amount == current_amount:
            return
        
        if target_amount > current_amount:
            buy_amount = target_amount - current_amount
            commission = self.calculate_commission(buy_amount, current_price, is_buy=True)
            total_cost = buy_amount * current_price + commission
            
            if total_cost > self.portfolio.cash:
                buy_amount = int((self.portfolio.cash - self.min_commission) / current_price / 100) * 100
                if buy_amount <= 0:
                    return
                commission = self.calculate_commission(buy_amount, current_price, is_buy=True)
                total_cost = buy_amount * current_price + commission
            
            self.portfolio.cash -= total_cost
            
            if code not in self.portfolio.positions:
                self.portfolio.positions[code] = Position(code, name)
            
            pos = self.portfolio.positions[code]
            total_amount = pos.amount + buy_amount
            if total_amount > 0:
                pos.avg_cost = (pos.avg_cost * pos.amount + current_price * buy_amount) / total_amount
            pos.amount = total_amount
            pos.price = current_price
            pos.value = pos.amount * current_price
            pos.name = name
            
            self.trade_records.append({
                'date': date,
                'code': code,
                'name': name,
                'action': 'buy',
                'price': current_price,
                'amount': buy_amount,
                'value': buy_amount * current_price,
                'commission': commission
            })
        
        elif target_amount < current_amount:
            if code not in self.portfolio.positions:
                return
            
            pos = self.portfolio.positions[code]
            sell_amount = current_amount - target_amount
            
            if sell_amount > pos.amount:
                sell_amount = pos.amount
            
            commission = self.calculate_commission(sell_amount, current_price, is_buy=False)
            revenue = sell_amount * current_price - commission
            
            self.portfolio.cash += revenue
            pos.amount -= sell_amount
            pos.price = current_price
            pos.value = pos.amount * current_price
            
            if pos.amount <= 0:
                del self.portfolio.positions[code]
            
            self.trade_records.append({
                'date': date,
                'code': code,
                'name': name,
                'action': 'sell',
                'price': current_price,
                'amount': sell_amount,
                'value': sell_amount * current_price,
                'commission': commission
            })
    
    def execute_trade(self, date: str):
        """
        执行交易
        
        参数:
            date: 交易日期
        """
        if self.config.drawdown_lock and not self.config.partial_unlock:
            print(f"  【交易拦截】处于回撤锁定状态")
            return
        
        current_pos_count = self.portfolio.position_count
        available_cash = self.portfolio.cash
        buy_candidates = [s for s in self.config.buy_signals 
                         if s not in self.portfolio.positions or 
                         self.portfolio.positions[s].amount == 0]
        
        for code in list(self.portfolio.positions.keys()):
            pos = self.portfolio.positions[code]
            if pos.amount <= 0:
                continue
            
            profit_ratio = pos.profit_ratio
            
            if profit_ratio >= self.config.take_profit_ratio or profit_ratio <= -self.config.stop_loss_ratio:
                self.order_target(code, 0, date, pos.name)
                print(f"  【止盈/止损】卖出{code}，收益率：{profit_ratio:.2%}")
                current_pos_count -= 1
                buy_candidates.append(code)
        
        if current_pos_count >= self.config.max_positions:
            return
        
        if available_cash < 500:
            return
        
        if not buy_candidates:
            return
        
        is_bull = False
        if self.index_data is not None:
            date_dt = pd.to_datetime(date)
            idx_data = self.index_data[self.index_data.index <= date_dt]
            if len(idx_data) >= 20:
                close = idx_data['close']
                b_ma20 = close.rolling(20).mean().iloc[-1]
                b_current = close.iloc[-1]
                is_bull = b_current > b_ma20 * self.config.bull_market_threshold
        
        cash_per_stock = available_cash / len(buy_candidates)
        
        if self.config.partial_unlock:
            max_position_value = self.portfolio.total_value * self.config.unlock_position_ratio
            current_position_value = self.portfolio.total_value - self.portfolio.cash
            allowed_buy_value = max_position_value - current_position_value
            
            if allowed_buy_value <= 0:
                print(f"  【部分解锁限制】已达最大仓位{self.config.unlock_position_ratio*100:.0f}%")
                return
            
            cash_per_stock = min(cash_per_stock, allowed_buy_value / len(buy_candidates))
        
        for code in buy_candidates:
            if current_pos_count >= self.config.max_positions:
                break
            
            buy_cash = cash_per_stock * self.config.bull_add_ratio if is_bull else cash_per_stock
            price = self.get_price_on_date(code, date)
            
            if price is None:
                continue
            
            min_cash = price * 100
            if buy_cash < min_cash:
                continue
            
            amount = int(buy_cash / price / 100) * 100
            if amount <= 0:
                continue
            
            name = ''
            for s in self.hs300_stocks:
                if s['code'] == code:
                    name = s.get('name', '')
                    break
            
            self.order_target(code, self.portfolio.positions.get(code, Position(code)).amount + amount, date, name)
            current_pos_count += 1
    
    def check_risk(self, date: str):
        """
        风控检查
        
        参数:
            date: 当前日期
        """
        total_value = self.portfolio.total_value
        if total_value <= 0:
            return
        
        pos_ratio = sum(p.value for p in self.portfolio.positions.values()) / total_value
        drawdown = self.portfolio.drawdown
        
        if self.index_data is None:
            return
        
        date_dt = pd.to_datetime(date)
        idx_data = self.index_data[self.index_data.index <= date_dt]
        
        if len(idx_data) < 60:
            return
        
        close = idx_data['close']
        volume = idx_data['volume']
        b_current = close.iloc[-1]
        b_ma20 = close.rolling(20).mean().iloc[-1]
        b_ma60 = close.rolling(60).mean().iloc[-1]
        b_macd = self.calculate_macd(close)
        b_rsi = self.calculate_rsi(close)
        b_vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        
        is_strong_bull = (b_current > b_ma20 * self.config.strong_bull_threshold and 
                        b_macd[0] > b_macd[1] and b_rsi < 80 and b_vol_ratio > 1.2)
        is_bear = b_current < b_ma20 and b_macd[0] < b_macd[1]
        
        if drawdown >= self.config.empty_drawdown:
            if self.config.partial_unlock and self.config.unlock_cooldown_days > 0:
                print(f"  【冷却期保护】回撤{drawdown*100:.1f}%≥10%，但处于冷却期")
            else:
                for code in list(self.portfolio.positions.keys()):
                    pos = self.portfolio.positions[code]
                    if pos.amount > 0:
                        self.order_target(code, 0, date, pos.name)
                self.config.drawdown_lock = True
                self.config.partial_unlock = False
                print(f"  【强空仓+锁定】回撤{drawdown*100:.1f}%≥10%")
                return
        
        elif b_current < b_ma60 and b_macd[0] < b_macd[1]:
            for code in list(self.portfolio.positions.keys()):
                pos = self.portfolio.positions[code]
                if pos.amount > 0:
                    self.order_target(code, 0, date, pos.name)
            print("  【强空仓-不锁定】沪深300破60日线+MACD死叉")
            return
        
        if is_strong_bull and pos_ratio < 0.95 and self.config.buy_signals:
            add_amount = total_value * 0.95 - sum(p.value for p in self.portfolio.positions.values())
            if add_amount > 0 and self.config.buy_signals:
                top1 = self.config.buy_signals[0]
                if top1 in self.portfolio.positions and self.portfolio.positions[top1].amount > 0:
                    price = self.get_price_on_date(top1, date)
                    if price:
                        add_shares = int(add_amount * 0.8 / price / 100) * 100
                        if add_shares > 0:
                            pos = self.portfolio.positions[top1]
                            self.order_target(top1, pos.amount + add_shares, date, pos.name)
                            print(f"  【强势加仓】{top1}")
        
        if is_bear and pos_ratio > 0.6:
            reduce_amount = sum(p.value for p in self.portfolio.positions.values()) - total_value * 0.6
            if reduce_amount > 0:
                low_score = [s for s in self.portfolio.positions.keys() 
                           if s not in self.config.buy_signals]
                if not low_score:
                    low_score = list(self.portfolio.positions.keys())[-1:]
                
                for code in low_score:
                    if code in self.portfolio.positions:
                        pos = self.portfolio.positions[code]
                        if pos.amount > 0:
                            price = self.get_price_on_date(code, date)
                            if price:
                                reduce_shares = int(reduce_amount / price / 100) * 100
                                if reduce_shares > 0:
                                    new_amount = max(0, pos.amount - reduce_shares)
                                    self.order_target(code, new_amount, date, pos.name)
                                    print(f"  【熊市减仓】{code}")
    
    def update_portfolio_value(self, date: str):
        """
        更新投资组合价值
        
        参数:
            date: 当前日期
        """
        prices = {}
        for code in self.portfolio.positions.keys():
            price = self.get_price_on_date(code, date)
            if price:
                prices[code] = price
        
        self.portfolio.update_positions_value(prices)
    
    def run_backtest(self):
        """
        运行回测
        
        执行完整的回测流程
        """
        print("=" * 60)
        print("大市值低回撤策略 - 分批解锁版")
        print("=" * 60)
        print(f"回测区间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: {self.portfolio.starting_cash:,.2f}")
        print("=" * 60)
        
        self.get_trade_days()
        if len(self.trade_days) == 0:
            print("无法获取交易日，退出回测")
            return
        
        self.get_index_data()
        self.init_rsrs()
        self.get_hs300_stocks()
        
        print("\n开始逐日回测...")
        
        for i, date in enumerate(self.trade_days):
            if (i + 1) % 20 == 0:
                print(f"回测进度: {date} ({i+1}/{len(self.trade_days)})")
            
            rsrs_value = self.calculate_rsrs(date)
            
            self.select_stocks(date)
            
            self.execute_trade(date)
            
            self.check_risk(date)
            
            self.update_portfolio_value(date)
            
            self.daily_values.append({
                'date': date,
                'total_value': self.portfolio.total_value,
                'cash': self.portfolio.cash,
                'position_value': self.portfolio.total_value - self.portfolio.cash,
                'position_count': self.portfolio.position_count,
                'drawdown': self.portfolio.drawdown,
                'drawdown_lock': self.config.drawdown_lock,
                'partial_unlock': self.config.partial_unlock,
                'unlock_cooldown': self.config.unlock_cooldown_days,
                'buy_signals': ','.join(self.config.buy_signals),
                'rsrs': rsrs_value
            })
        
        self.print_results()
        self.save_results()
        self.generate_report()
    
    def print_results(self):
        """
        打印回测结果
        """
        print("\n" + "=" * 60)
        print("回测结果汇总")
        print("=" * 60)
        
        if len(self.daily_values) == 0:
            print("无回测数据")
            return
        
        df = pd.DataFrame(self.daily_values)
        
        start_value = df['total_value'].iloc[0]
        end_value = df['total_value'].iloc[-1]
        total_return = (end_value - start_value) / start_value * 100
        
        df['daily_return'] = df['total_value'].pct_change()
        annual_return = (1 + df['daily_return'].mean()) ** 252 - 1
        annual_volatility = df['daily_return'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        max_drawdown = df['drawdown'].max()
        
        print(f"初始资金: {start_value:,.2f}")
        print(f"最终资金: {end_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annual_return * 100:.2f}%")
        print(f"年化波动率: {annual_volatility * 100:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"最大回撤: {max_drawdown * 100:.2f}%")
        print(f"交易次数: {len(self.trade_records)}")
        
        partial_unlock_days = df['partial_unlock'].sum()
        print(f"部分解锁天数: {partial_unlock_days}")
        
        if len(self.trade_records) > 0:
            trades_df = pd.DataFrame(self.trade_records)
            buy_trades = trades_df[trades_df['action'] == 'buy']
            sell_trades = trades_df[trades_df['action'] == 'sell']
            print(f"买入次数: {len(buy_trades)}")
            print(f"卖出次数: {len(sell_trades)}")
            print(f"总手续费: {trades_df['commission'].sum():,.2f}")
    
    def generate_report(self, output_path: str = None):
        """
        生成交互式HTML报告
        
        参数:
            output_path: 报告输出路径
        """
        if len(self.daily_values) == 0:
            print("无回测数据，无法生成报告")
            return
        
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, 'backtest_report.html')
        
        try:
            generator = BacktestReportGenerator(
                strategy_name='大市值低回撤策略(分批解锁版)',
                daily_values=self.daily_values,
                trade_records=self.trade_records,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_cash=self.portfolio.starting_cash
            )
            generator.generate_html_report(output_path)
        except Exception as e:
            print(f"生成报告失败: {e}")
    
    def save_results(self):
        """
        保存回测结果
        """
        if len(self.daily_values) > 0:
            df = pd.DataFrame(self.daily_values)
            df.to_csv('backtest_daily_values_optimized.csv', index=False, encoding='utf-8-sig')
            print(f"\n每日净值已保存至: backtest_daily_values_optimized.csv")
        
        if len(self.trade_records) > 0:
            df = pd.DataFrame(self.trade_records)
            df.to_csv('backtest_trade_records_optimized.csv', index=False, encoding='utf-8-sig')
            print(f"交易记录已保存至: backtest_trade_records_optimized.csv")


def main():
    """
    主函数
    
    创建策略实例并运行30天的回测
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    strategy = LocalBacktestStrategyOptimized(
        start_date=start_date,
        end_date=end_date,
        initial_cash=100000.0
    )
    
    strategy.run_backtest()


if __name__ == '__main__':
    main()
