# 克隆自聚宽文章：https://www.joinquant.com/post/15002
# 标题：价值选股与RSRS择时
# 作者：K线放荡不羁
# 本地化版本：使用efinance数据源

'''
================================================================================
策略思路：
================================================================================
1. 选股：财务指标选股（PB、ROE）
   - PB（市净率）越低越好，代表股票估值越便宜
   - ROE（净资产收益率）越高越好，代表公司盈利能力强
   - 综合打分：PB排名 + ROE倒数排名，取综合得分最低的10只股票

2. 择时：RSRS择时（阻力支撑相对强度）
   - 基于最高价和最低价的线性回归计算斜率β
   - 斜率代表市场的阻力支撑强度
   - 使用标准化后的Z分数作为买卖信号
   - 买入阈值：zscore > 0.7
   - 卖出阈值：zscore < -0.7

3. 持仓：有开仓信号时持有10只股票，不满足时保持空仓
================================================================================
'''

import numpy as np
import pandas as pd
import statsmodels.api as sm
import efinance as ef
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
import os
import sys
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_report_generator import BacktestReportGenerator


def format_date_for_efinance(date_str: str) -> str:
    """
    将日期格式转换为efinance需要的格式
    
    efinance API需要的日期格式为 '20200101'，而不是 '2020-01-01'
    
    参数:
        date_str: 输入日期字符串，支持 'YYYY-MM-DD' 或 'YYYYMMDD' 格式
    
    返回:
        efinance格式的日期字符串 'YYYYMMDD'
    """
    if '-' in date_str:
        return date_str.replace('-', '')
    return date_str


class Context:
    """
    策略上下文类
    
    模拟聚宽平台的context对象，存储策略运行时的状态信息
    
    属性:
        current_dt: 当前回测时间点
        previous_date: 前一个交易日
        portfolio: 投资组合对象
    """
    def __init__(self):
        self.current_dt = None
        self.previous_date = None
        self.portfolio = Portfolio()


class Portfolio:
    """
    投资组合类
    
    管理账户的资金和持仓信息
    
    属性:
        positions: 持仓字典，key为股票代码，value为Position对象
        total_value: 账户总资产（现金 + 持仓市值）
        starting_cash: 初始资金
        cash: 可用现金
    """
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.total_value = 1000000.0
        self.starting_cash = 1000000.0
        self.cash = 1000000.0
    
    def update_positions_value(self, prices: Dict[str, float]):
        """
        更新持仓市值
        
        根据最新价格更新所有持仓的市值，并重新计算总资产
        
        参数:
            prices: 股票价格字典，key为股票代码，value为最新价格
        """
        total_position_value = 0
        for code, position in self.positions.items():
            if code in prices:
                position.update_value(prices[code])
                total_position_value += position.value
        self.total_value = self.cash + total_position_value


class Position:
    """
    持仓类
    
    记录单只股票的持仓信息
    
    属性:
        code: 股票代码
        amount: 持仓数量（股数）
        price: 当前价格
        value: 持仓市值
        avg_cost: 平均持仓成本
    """
    def __init__(self, code: str):
        self.code = code
        self.amount = 0
        self.price = 0.0
        self.value = 0.0
        self.avg_cost = 0.0
    
    def update_value(self, current_price: float):
        """
        更新持仓价值
        
        参数:
            current_price: 当前股票价格
        """
        self.price = current_price
        self.value = self.amount * current_price


class GlobalParams:
    """
    全局参数类
    
    模拟聚宽平台的g对象，存储策略的全局参数和状态
    
    属性:
        N: RSRS斜率计算的统计周期（天数），默认18
        M: RSRS标准化的样本长度，默认1100
        stock_num: 持仓股票数量，默认10
        security: 风险参考基准（沪深300指数代码），默认'000300'
        buy: 买入阈值，RSRS标准分大于此值时买入，默认0.7
        sell: 卖出阈值，RSRS标准分小于此值时卖出，默认-0.7
        ans: 存储历史斜率值列表
        ans_rightdev: 存储历史决定系数R²列表
        days: 策略运行天数计数器
        init: 首次运行标志
    """
    def __init__(self):
        self.N = 18
        self.M = 1100
        self.stock_num = 10
        self.security = '000300'
        self.buy = 0.7
        self.sell = -0.7
        self.ans: List[float] = []
        self.ans_rightdev: List[float] = []
        self.days = 0
        self.init = True


class LocalBacktestStrategy:
    """
    本地回测策略类
    
    实现完整的本地回测框架，包括：
    - 数据获取（通过efinance）
    - RSRS择时信号计算
    - 价值选股逻辑
    - 交易模拟
    - 回测结果统计和输出
    
    使用示例:
        strategy = LocalBacktestStrategy(
            start_date='2020-01-01',
            end_date='2024-12-31',
            initial_cash=1000000.0
        )
        strategy.run_backtest()
    """
    
    def __init__(self, start_date: str = '2015-01-01', end_date: str = None, 
                 initial_cash: float = 1000000.0):
        """
        初始化回测策略
        
        参数:
            start_date: 回测开始日期，格式 'YYYY-MM-DD'
            end_date: 回测结束日期，格式 'YYYY-MM-DD'，默认为当前日期
            initial_cash: 初始资金，默认100万
        """
        self.context = Context()
        self.context.portfolio.starting_cash = initial_cash
        self.context.portfolio.cash = initial_cash
        self.context.portfolio.total_value = initial_cash
        self.g = GlobalParams()
        
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        
        self.trade_days: List[str] = []
        self.index_data: pd.DataFrame = None
        self.stock_pool_cache: Dict[str, pd.DataFrame] = {}
        self.financial_data_cache: Dict[str, pd.DataFrame] = {}
        self.all_stocks_cache: List[str] = []
        self.all_financial_df: pd.DataFrame = None
        
        self.trade_records: List[Dict] = []
        self.daily_values: List[Dict] = []
        
        self.commission_rate = 0.0003
        self.stamp_tax_rate = 0.001
        self.min_commission = 5.0
    
    def get_trade_days(self) -> List[str]:
        """
        获取交易日列表
        
        通过获取指数的历史行情数据来提取交易日列表
        如果获取失败，则使用简单的工作日作为替代
        
        返回:
            交易日日期列表
        """
        print("正在获取交易日历...")
        try:
            beg = format_date_for_efinance(self.start_date)
            end = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history(self.g.security, 
                                            beg=beg, 
                                            end=end,
                                            klt=101,
                                            fqt=1)
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
    
    def get_index_data(self, start_date: str = '2005-01-05') -> pd.DataFrame:
        """
        获取指数历史数据
        
        获取沪深300指数的历史行情数据，用于RSRS指标计算
        需要从较早日期开始获取，以便初始化RSRS指标
        
        参数:
            start_date: 数据开始日期，默认从2005年开始
        
        返回:
            指数历史数据DataFrame，包含开盘价、收盘价、最高价、最低价等
        """
        print(f"正在获取指数 {self.g.security} 数据...")
        try:
            beg = format_date_for_efinance(start_date)
            end = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history(self.g.security, 
                                            beg=beg,
                                            end=end,
                                            klt=101,
                                            fqt=1)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'change_pct',
                    '涨跌额': 'change_amt',
                    '换手率': 'turnover'
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
        这样可以确保回测开始时有足够的历史数据进行标准化
        
        RSRS指标计算原理:
        1. 对过去N天的最高价和最低价进行线性回归
        2. 回归方程: High = α + β × Low
        3. 斜率β代表市场的阻力支撑强度
        4. R²代表回归的拟合优度
        """
        print("正在初始化RSRS指标...")
        if self.index_data is None or len(self.index_data) == 0:
            print("指数数据为空，无法初始化RSRS")
            return
        
        start_idx = self.trade_days[0] if self.trade_days else self.start_date
        init_data = self.index_data[self.index_data.index < pd.to_datetime(start_idx)]
        
        if len(init_data) < self.g.N:
            init_data = self.index_data
        
        highs = init_data['high'].values
        lows = init_data['low'].values
        
        self.g.ans = []
        self.g.ans_rightdev = []
        
        for i in range(self.g.N, len(highs)):
            data_high = highs[i-self.g.N+1:i+1]
            data_low = lows[i-self.g.N+1:i+1]
            X = sm.add_constant(data_low)
            model = sm.OLS(data_high, X)
            results = model.fit()
            self.g.ans.append(results.params[1])
            self.g.ans_rightdev.append(results.rsquared)
        
        print(f"RSRS初始化完成，共计算 {len(self.g.ans)} 个斜率值")
    
    def get_stock_data(self, code: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        从efinance获取指定股票的历史行情数据
        使用缓存机制避免重复获取
        
        参数:
            code: 股票代码
            days: 需要获取的天数
        
        返回:
            股票历史数据DataFrame，如果获取失败返回None
        """
        if code in self.stock_pool_cache:
            return self.stock_pool_cache[code]
        
        try:
            stock_code = code if code.startswith(('6', '0', '3')) else code
            beg_date = (datetime.strptime(self.start_date, '%Y-%m-%d') - 
                       timedelta(days=days*2)).strftime('%Y%m%d')
            end_date = format_date_for_efinance(self.end_date)
            
            df = ef.stock.get_quote_history(stock_code, 
                                            beg=beg_date,
                                            end=end_date,
                                            klt=101,
                                            fqt=1)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'change_pct',
                    '涨跌额': 'change_amt',
                    '换手率': 'turnover'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                self.stock_pool_cache[code] = df
                return df
        except Exception as e:
            pass
        return None
    
    def get_financial_data(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票财务数据
        
        批量获取股票的财务指标数据（PB、ROE）
        用于价值选股策略
        
        参数:
            codes: 股票代码列表
        
        返回:
            财务数据DataFrame，包含code、pb_ratio、roe列
        """
        print(f"正在获取 {len(codes)} 只股票的财务数据...")
        result_data = []
        
        for i, code in enumerate(codes):
            if i % 50 == 0:
                print(f"进度: {i}/{len(codes)}")
            try:
                series = ef.stock.get_base_info(code)
                if series is not None and len(series) > 0:
                    pb = series.get('市净率', None)
                    roe = series.get('ROE', None)
                    
                    if pb is not None and roe is not None:
                        try:
                            pb_val = float(pb)
                            roe_val = float(roe) / 100 if roe > 1 else float(roe)
                            result_data.append({
                                'code': code,
                                'pb_ratio': pb_val,
                                'roe': roe_val
                            })
                        except:
                            pass
            except Exception as e:
                continue
        
        return pd.DataFrame(result_data)
    
    def get_all_stocks(self) -> List[str]:
        """
        获取全市场股票列表
        
        从efinance获取当前A股市场所有股票的代码
        过滤掉科创板（68开头）和北交所股票
        使用缓存避免重复获取
        
        返回:
            股票代码列表
        """
        if len(self.all_stocks_cache) > 0:
            return self.all_stocks_cache
        
        print("正在获取股票列表...")
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and len(df) > 0:
                codes = df['股票代码'].tolist()
                codes = [c for c in codes if c.startswith(('6', '0', '3')) and not c.startswith('68')]
                self.all_stocks_cache = codes
                print(f"获取到 {len(codes)} 只股票")
                return codes
        except Exception as e:
            print(f"获取股票列表失败: {e}")
        return []
    
    def calculate_rsrs(self, current_date: str) -> float:
        """
        计算RSRS指标
        
        RSRS（阻力支撑相对强度）指标计算步骤:
        1. 取最近N天的最高价和最低价
        2. 进行线性回归: High = α + β × Low
        3. 计算斜率β和决定系数R²
        4. 对斜率进行M天窗口的标准化
        5. 计算右偏RSRS标准分 = zscore × β × R²
        
        参数:
            current_date: 当前日期
        
        返回:
            右偏RSRS标准分
        """
        if self.index_data is None:
            return 0.0
        
        current_dt = pd.to_datetime(current_date)
        idx_data = self.index_data[self.index_data.index <= current_dt]
        
        if len(idx_data) < self.g.N:
            return 0.0
        
        highs = idx_data['high'].values[-self.g.N:]
        lows = idx_data['low'].values[-self.g.N:]
        
        X = sm.add_constant(lows)
        model = sm.OLS(highs, X)
        beta = model.fit().params[1]
        r2 = model.fit().rsquared
        
        self.g.ans.append(beta)
        self.g.ans_rightdev.append(r2)
        
        if len(self.g.ans) < self.g.M:
            return 0.0
        
        section = self.g.ans[-self.g.M:]
        mu = np.mean(section)
        sigma = np.std(section)
        
        if sigma == 0:
            return 0.0
        
        zscore = (section[-1] - mu) / sigma
        zscore_rightdev = zscore * beta * r2
        
        return zscore_rightdev
    
    def select_stocks(self, current_date: str) -> List[str]:
        """
        选股逻辑
        
        基于价值投资理念进行选股:
        1. 获取股票池和财务数据
        2. 筛选PB>0且ROE>0的股票
        3. 计算综合得分 = PB排名 + ROE倒数排名
        4. 选择得分最低的N只股票
        
        参数:
            current_date: 当前日期
        
        返回:
            选中的股票代码列表
        """
        print(f"  正在选股...")
        
        if self.all_financial_df is None:
            all_stocks = self.get_all_stocks()
            
            if len(all_stocks) == 0:
                return []
            
            sample_stocks = all_stocks[:500] if len(all_stocks) > 500 else all_stocks
            
            self.all_financial_df = self.get_financial_data(sample_stocks)
        
        if self.all_financial_df.empty:
            return []
        
        financial_df = self.all_financial_df[(self.all_financial_df['roe'] > 0) & (self.all_financial_df['pb_ratio'] > 0)]
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df.sort_values('pb_ratio')
        financial_df['1/roe'] = 1 / financial_df['roe']
        financial_df['pb_rank'] = financial_df['pb_ratio'].rank()
        financial_df['roe_rank'] = financial_df['1/roe'].rank()
        financial_df['point'] = financial_df['pb_rank'] + financial_df['roe_rank']
        
        financial_df = financial_df.sort_values('point')
        selected = financial_df.head(self.g.stock_num)['code'].tolist()
        
        print(f"  选出 {len(selected)} 只股票: {selected[:5]}...")
        return selected
    
    def get_current_price(self, code: str, date: str) -> Optional[float]:
        """
        获取指定日期的股票价格
        
        查找指定日期的收盘价，如果当天没有数据则取最近的有效价格
        
        参数:
            code: 股票代码
            date: 日期
        
        返回:
            股票收盘价，如果获取失败返回None
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
    
    def calculate_commission(self, amount: float, price: float, is_buy: bool) -> float:
        """
        计算交易费用
        
        费用包括:
        - 佣金：万分之三，最低5元
        - 印花税：千分之一（仅卖出时收取）
        
        参数:
            amount: 交易数量（股数）
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
    
    def order_target_value(self, code: str, target_value: float, date: str):
        """
        按目标价值下单
        
        调整持仓至目标市值，自动计算买卖数量
        买入时考虑手续费，卖出时考虑手续费和印花税
        
        参数:
            code: 股票代码
            target_value: 目标持仓市值
            date: 交易日期
        """
        current_price = self.get_current_price(code, date)
        if current_price is None or current_price <= 0:
            return
        
        if code in self.context.portfolio.positions:
            current_position = self.context.portfolio.positions[code]
            current_value = current_position.amount * current_price
        else:
            current_value = 0
        
        if abs(target_value - current_value) < 100:
            return
        
        if target_value > current_value:
            buy_value = target_value - current_value
            if buy_value > self.context.portfolio.cash:
                buy_value = self.context.portfolio.cash
            
            amount = int(buy_value / current_price / 100) * 100
            if amount <= 0:
                return
            
            commission = self.calculate_commission(amount, current_price, is_buy=True)
            total_cost = amount * current_price + commission
            
            if total_cost > self.context.portfolio.cash:
                amount = int((self.context.portfolio.cash - self.min_commission) / current_price / 100) * 100
                if amount <= 0:
                    return
                total_cost = amount * current_price + self.calculate_commission(amount, current_price, is_buy=True)
            
            self.context.portfolio.cash -= total_cost
            
            if code not in self.context.portfolio.positions:
                self.context.portfolio.positions[code] = Position(code)
            
            pos = self.context.portfolio.positions[code]
            total_amount = pos.amount + amount
            if total_amount > 0:
                pos.avg_cost = (pos.avg_cost * pos.amount + current_price * amount) / total_amount
            pos.amount = total_amount
            pos.price = current_price
            pos.value = pos.amount * current_price
            
            self.trade_records.append({
                'date': date,
                'code': code,
                'action': 'buy',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission
            })
        
        elif target_value < current_value:
            if code not in self.context.portfolio.positions:
                return
            
            pos = self.context.portfolio.positions[code]
            sell_value = current_value - target_value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                return
            
            if amount > pos.amount:
                amount = pos.amount
            
            commission = self.calculate_commission(amount, current_price, is_buy=False)
            revenue = amount * current_price - commission
            
            self.context.portfolio.cash += revenue
            pos.amount -= amount
            pos.price = current_price
            pos.value = pos.amount * current_price
            
            if pos.amount <= 0:
                del self.context.portfolio.positions[code]
            
            self.trade_records.append({
                'date': date,
                'code': code,
                'action': 'sell',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission
            })
    
    def order_target(self, code: str, target_amount: int, date: str):
        """
        按目标数量下单
        
        调整持仓至目标数量
        当目标数量为0时，清空该股票持仓
        
        参数:
            code: 股票代码
            target_amount: 目标持仓数量（股数）
            date: 交易日期
        """
        if target_amount == 0:
            if code in self.context.portfolio.positions:
                pos = self.context.portfolio.positions[code]
                current_price = self.get_current_price(code, date)
                if current_price and pos.amount > 0:
                    commission = self.calculate_commission(pos.amount, current_price, is_buy=False)
                    revenue = pos.amount * current_price - commission
                    self.context.portfolio.cash += revenue
                    
                    self.trade_records.append({
                        'date': date,
                        'code': code,
                        'action': 'sell',
                        'price': current_price,
                        'amount': pos.amount,
                        'value': pos.amount * current_price,
                        'commission': commission
                    })
                    
                del self.context.portfolio.positions[code]
        else:
            current_price = self.get_current_price(code, date)
            if current_price:
                self.order_target_value(code, target_amount * current_price, date)
    
    def trade_func(self, date: str):
        """
        交易逻辑
        
        执行选股并调整持仓:
        1. 调用select_stocks获取目标股票池
        2. 卖出不在目标池中的股票
        3. 平均分配资金买入目标股票
        
        参数:
            date: 交易日期
        """
        selected_stocks = self.select_stocks(date)
        
        if len(selected_stocks) == 0:
            return
        
        cash_per_stock = self.context.portfolio.total_value / len(selected_stocks)
        
        hold_stocks = list(self.context.portfolio.positions.keys())
        
        for s in hold_stocks:
            if s not in selected_stocks:
                self.order_target(s, 0, date)
        
        for s in selected_stocks:
            self.order_target_value(s, cash_per_stock, date)
    
    def update_portfolio_value(self, date: str):
        """
        更新投资组合价值
        
        根据最新价格更新所有持仓的市值和总资产
        
        参数:
            date: 当前日期
        """
        prices = {}
        for code in self.context.portfolio.positions.keys():
            price = self.get_current_price(code, date)
            if price:
                prices[code] = price
        
        self.context.portfolio.update_positions_value(prices)
    
    def run_backtest(self):
        """
        运行回测
        
        执行完整的回测流程:
        1. 获取交易日历和指数数据
        2. 初始化RSRS指标
        3. 逐日遍历，计算RSRS信号并执行交易
        4. 输出回测结果
        """
        print("=" * 60)
        print("开始运行回测...")
        print(f"回测区间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: {self.context.portfolio.starting_cash:,.2f}")
        print("=" * 60)
        
        self.get_trade_days()
        
        if len(self.trade_days) == 0:
            print("无法获取交易日，退出回测")
            return
        
        self.get_index_data()
        self.init_rsrs()
        
        print("\n开始逐日回测...")
        
        for i, date in enumerate(self.trade_days):
            self.context.current_dt = pd.to_datetime(date)
            self.context.previous_date = self.trade_days[i-1] if i > 0 else date
            
            self.g.days += 1
            
            if self.g.days % 50 == 0:
                print(f"回测进度: {date} ({self.g.days}/{len(self.trade_days)})")
            
            rsrs_value = self.calculate_rsrs(date)
            
            if rsrs_value > self.g.buy:
                self.trade_func(date)
            elif rsrs_value < self.g.sell and len(self.context.portfolio.positions) > 0:
                for s in list(self.context.portfolio.positions.keys()):
                    self.order_target(s, 0, date)
            
            self.update_portfolio_value(date)
            
            self.daily_values.append({
                'date': date,
                'total_value': self.context.portfolio.total_value,
                'cash': self.context.portfolio.cash,
                'position_value': self.context.portfolio.total_value - self.context.portfolio.cash,
                'position_count': len(self.context.portfolio.positions),
                'rsrs': rsrs_value
            })
        
        self.print_results()
        self.save_results()
    
    def print_results(self):
        """
        打印回测结果
        
        计算并输出回测的各项指标:
        - 总收益率
        - 年化收益率
        - 年化波动率
        - 夏普比率
        - 最大回撤
        - 交易统计
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
        
        max_value = df['total_value'].expanding().max()
        drawdown = (df['total_value'] - max_value) / max_value
        max_drawdown = drawdown.min()
        
        print(f"初始资金: {start_value:,.2f}")
        print(f"最终资金: {end_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annual_return * 100:.2f}%")
        print(f"年化波动率: {annual_volatility * 100:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"最大回撤: {max_drawdown * 100:.2f}%")
        print(f"交易次数: {len(self.trade_records)}")
        
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
                strategy_name='价值选股与RSRS择时策略',
                daily_values=self.daily_values,
                trade_records=self.trade_records,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_cash=self.context.portfolio.starting_cash
            )
            generator.generate_html_report(output_path)
        except Exception as e:
            print(f"生成报告失败: {e}")
    
    def save_results(self):
        """
        保存回测结果
        
        将每日净值和交易记录保存为CSV文件
        """
        if len(self.daily_values) > 0:
            df = pd.DataFrame(self.daily_values)
            df.to_csv('backtest_daily_values.csv', index=False, encoding='utf-8-sig')
            print(f"\n每日净值已保存至: backtest_daily_values.csv")
        
        if len(self.trade_records) > 0:
            df = pd.DataFrame(self.trade_records)
            df.to_csv('backtest_trade_records.csv', index=False, encoding='utf-8-sig')
            print(f"交易记录已保存至: backtest_trade_records.csv")


def main():
    """
    主函数
    
    创建策略实例并运行回测，最后生成交互式HTML报告
    """
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
    
    strategy = LocalBacktestStrategy(
        start_date=start_date,
        end_date=end_date,
        initial_cash=1000000.0
    )
    
    strategy.run_backtest()
    strategy.generate_report()


if __name__ == '__main__':
    main()
