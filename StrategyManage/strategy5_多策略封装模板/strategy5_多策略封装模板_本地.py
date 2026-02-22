# 克隆自聚宽文章：https://www.joinquant.com/post/66658
# 标题：多策略组合5年440%
# 作者：鱼树
# 本地化版本：使用efinance数据源

"""
多策略模板 本地化版本
支持多策略组合运行，每个策略独立管理资金和持仓
"""

import numpy as np
import pandas as pd
import efinance as ef
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
import os
import sys
import math
import statsmodels.api as sm
import concurrent.futures
from functools import lru_cache
from tqdm import tqdm

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from backtest_report_generator import BacktestReportGenerator
except ImportError:
    BacktestReportGenerator = None

try:
    from multi_strategy_report_generator import MultiStrategyReportGenerator
except ImportError:
    MultiStrategyReportGenerator = None

try:
    from multi_strategy_pdf_report import MultiStrategyPDFReport
except ImportError:
    MultiStrategyPDFReport = None


def format_date_for_efinance(date_str: str) -> str:
    if '-' in date_str:
        return date_str.replace('-', '')
    return date_str


class Position:
    def __init__(self, code: str):
        self.code = code
        self.security = code
        self.amount = 0
        self.total_amount = 0
        self.price = 0.0
        self.value = 0.0
        self.avg_cost = 0.0
    
    def update_value(self, current_price: float):
        self.price = current_price
        self.value = self.total_amount * current_price


class SubPortfolio:
    def __init__(self, starting_cash: float = 0.0):
        self.starting_cash = starting_cash
        self.total_value = starting_cash
        self.cash = starting_cash
        self.available_cash = starting_cash
        self.positions: Dict[str, Position] = {}
    
    def update_positions_value(self, prices: Dict[str, float]):
        total_position_value = 0
        for code, position in self.positions.items():
            if code in prices:
                position.update_value(prices[code])
                total_position_value += position.value
        self.total_value = self.cash + total_position_value
        self.available_cash = self.cash


class Portfolio:
    def __init__(self, starting_cash: float = 1000000.0):
        self.starting_cash = starting_cash
        self.total_value = starting_cash
        self.cash = starting_cash
        self.positions: Dict[str, Position] = {}
        self.subportfolios: List[SubPortfolio] = []
    
    def update_total_value(self):
        self.total_value = sum(sp.total_value for sp in self.subportfolios)
        self.cash = sum(sp.cash for sp in self.subportfolios)


class Context:
    def __init__(self):
        self.current_dt = None
        self.previous_date = None
        self.portfolio = Portfolio()
        self.subportfolios = []


class GlobalParams:
    def __init__(self):
        self.STRATEGY_CONFIG = []
        self.strategys = []


class DataManager:
    def __init__(self):
        self.stock_cache: Dict[str, pd.DataFrame] = {}
        self.index_cache: Dict[str, pd.DataFrame] = {}
        self.financial_cache: Dict[str, pd.DataFrame] = {}
        self.all_stocks_cache: List[str] = []
        self.etf_cache: Dict[str, pd.DataFrame] = {}
        self.industry_cache: Dict[str, List[str]] = {}
        self.trade_days_cache: List[str] = []
        self.st_stock_cache: Dict[str, bool] = {}
        self.stock_name_cache: Dict[str, str] = {}
        self.max_workers = 10
    
    def get_trade_days(self, start_date: str, end_date: str, index_code: str = '000300') -> List[str]:
        cache_key = f"{start_date}_{end_date}_{index_code}"
        if cache_key in self.trade_days_cache:
            return self.trade_days_cache
        
        try:
            beg = format_date_for_efinance(start_date)
            end = format_date_for_efinance(end_date)
            df = ef.stock.get_quote_history(index_code, beg=beg, end=end, klt=101, fqt=1)
            if df is not None and len(df) > 0:
                days = df['日期'].tolist()
                self.trade_days_cache = days
                return days
        except Exception as e:
            print(f"获取交易日历失败: {e}")
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        delta = timedelta(days=1)
        current = start
        all_days = []
        while current <= end:
            if current.weekday() < 5:
                all_days.append(current.strftime('%Y-%m-%d'))
            current += delta
        return all_days
    
    def get_stock_data(self, code: str, start_date: str = None, end_date: str = None, 
                       days: int = 100) -> Optional[pd.DataFrame]:
        cache_key = f"{code}_{start_date}_{end_date}_{days}"
        if cache_key in self.stock_cache:
            return self.stock_cache[cache_key]
        
        try:
            stock_code = code.split('.')[0] if '.' in code else code
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            beg = format_date_for_efinance(start_date)
            end = format_date_for_efinance(end_date)
            
            df = ef.stock.get_quote_history(stock_code, beg=beg, end=end, klt=101, fqt=1)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume',
                    '成交额': 'amount', '振幅': 'amplitude',
                    '涨跌幅': 'change_pct', '涨跌额': 'change_amt', '换手率': 'turnover'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df['code'] = code
                self.stock_cache[cache_key] = df
                return df
        except Exception as e:
            pass
        return None
    
    def get_etf_data(self, code: str, start_date: str = None, end_date: str = None,
                     days: int = 100) -> Optional[pd.DataFrame]:
        return self.get_stock_data(code, start_date, end_date, days)
    
    def get_all_stocks(self) -> List[str]:
        if len(self.all_stocks_cache) > 0:
            return self.all_stocks_cache
        
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and len(df) > 0:
                codes = df['股票代码'].tolist()
                codes = [c for c in codes if c.startswith(('6', '0', '3')) and not c.startswith('68')]
                self.all_stocks_cache = codes
                return codes
        except Exception as e:
            print(f"获取股票列表失败: {e}")
        return []
    
    def get_current_price(self, code: str, date: str) -> Optional[float]:
        stock_data = self.get_stock_data(code, end_date=date, days=30)
        if stock_data is not None:
            date_dt = pd.to_datetime(date)
            if date_dt in stock_data.index:
                return stock_data.loc[date_dt, 'close']
            else:
                nearest = stock_data.index[stock_data.index <= date_dt]
                if len(nearest) > 0:
                    return stock_data.loc[nearest[-1], 'close']
        return None
    
    def get_prices(self, codes: List[str], date: str, fields: List[str] = None) -> pd.DataFrame:
        results = []
        for code in codes:
            data = self.get_stock_data(code, end_date=date, days=5)
            if data is not None and len(data) > 0:
                date_dt = pd.to_datetime(date)
                if date_dt in data.index:
                    row = data.loc[date_dt].to_dict()
                    row['code'] = code
                    results.append(row)
                else:
                    nearest = data.index[data.index <= date_dt]
                    if len(nearest) > 0:
                        row = data.loc[nearest[-1]].to_dict()
                        row['code'] = code
                        results.append(row)
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def _get_single_financial_data(self, code: str) -> Optional[Dict]:
        try:
            series = ef.stock.get_base_info(code)
            if series is not None and len(series) > 0:
                row = {'code': code}
                row['market_cap'] = series.get('总市值', 0)
                row['circulating_market_cap'] = series.get('流通市值', 0)
                row['pe_ratio'] = series.get('市盈率(动)', 0)
                row['pb_ratio'] = series.get('市净率', 0)
                row['ps_ratio'] = series.get('市销率', 0)
                row['pcf_ratio'] = series.get('市现率', 0)
                row['roe'] = series.get('ROE', 0)
                row['net_profit'] = series.get('净利润', 0)
                row['net_profit_rate'] = series.get('净利率', 0)
                name = str(series.get('股票名称', ''))
                self.stock_name_cache[code] = name
                self.st_stock_cache[code] = 'ST' in name or '*' in name or '退' in name
                return row
        except Exception:
            pass
        return None
    
    def get_financial_data(self, codes: List[str]) -> pd.DataFrame:
        cache_key = '_'.join(sorted(codes[:10]))
        if cache_key in self.financial_cache:
            return self.financial_cache[cache_key]
        
        result_data = []
        total = len(codes)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._get_single_financial_data, code): code for code in codes}
            for future in tqdm(concurrent.futures.as_completed(futures), total=total, desc="获取财务数据", unit="只"):
                try:
                    result = future.result()
                    if result is not None:
                        result_data.append(result)
                except Exception:
                    continue
        
        df = pd.DataFrame(result_data)
        self.financial_cache[cache_key] = df
        return df
    
    def get_index_stocks(self, index_code: str, date: str = None) -> List[str]:
        index_code_clean = index_code.split('.')[0] if '.' in index_code else index_code
        cache_key = f"{index_code_clean}_{date}"
        if cache_key in self.industry_cache:
            return self.industry_cache[cache_key]
        
        try:
            if index_code_clean == '000300':
                df = ef.stock.get_constituent_stocks('000300', date=date.replace('-', '') if date else None)
                if df is not None and len(df) > 0:
                    codes = df['股票代码'].tolist() if '股票代码' in df.columns else []
                    self.industry_cache[cache_key] = codes
                    return codes
            elif index_code_clean == '399101':
                df = ef.stock.get_constituent_stocks('399101', date=date.replace('-', '') if date else None)
                if df is not None and len(df) > 0:
                    codes = df['股票代码'].tolist() if '股票代码' in df.columns else []
                    self.industry_cache[cache_key] = codes
                    return codes
            elif index_code_clean == '000985':
                df = ef.stock.get_constituent_stocks('000985', date=date.replace('-', '') if date else None)
                if df is not None and len(df) > 0:
                    codes = df['股票代码'].tolist() if '股票代码' in df.columns else []
                    self.industry_cache[cache_key] = codes
                    return codes
        except Exception as e:
            pass
        
        all_stocks = self.get_all_stocks()
        return all_stocks[:100]
    
    def is_st_stock(self, code: str, date: str = None) -> bool:
        if code in self.st_stock_cache:
            return self.st_stock_cache[code]
        
        if code in self.stock_name_cache:
            name = self.stock_name_cache[code]
            result = 'ST' in name or '*' in name or '退' in name
            self.st_stock_cache[code] = result
            return result
        
        try:
            series = ef.stock.get_base_info(code)
            if series is not None:
                name = str(series.get('股票名称', ''))
                self.stock_name_cache[code] = name
                result = 'ST' in name or '*' in name or '退' in name
                self.st_stock_cache[code] = result
                return result
        except Exception:
            pass
        self.st_stock_cache[code] = False
        return False
    
    def is_paused(self, code: str, date: str) -> bool:
        data = self.get_stock_data(code, end_date=date, days=10)
        if data is None or len(data) == 0:
            return True
        date_dt = pd.to_datetime(date)
        return date_dt not in data.index
    
    def get_limit_prices(self, code: str, date: str) -> Tuple[float, float]:
        data = self.get_stock_data(code, end_date=date, days=5)
        if data is not None and len(data) > 0:
            date_dt = pd.to_datetime(date)
            if date_dt in data.index:
                close = data.loc[date_dt, 'close']
                change_pct = data.loc[date_dt, 'change_pct']
                if pd.notna(change_pct):
                    high_limit = close / (1 + change_pct/100) * 1.1
                    low_limit = close / (1 + change_pct/100) * 0.9
                    return high_limit, low_limit
        return 0.0, 0.0


g = GlobalParams()


class Strategy:
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None
        self.data_manager = data_manager
        self.trade_records = []
    
    def record_daily_value(self, context: Context):
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        new_data = {'date': context.current_dt.strftime('%Y-%m-%d'), 'total_value': subportfolio.total_value}
        self.portfolio_value = pd.concat([self.portfolio_value, pd.DataFrame([new_data])], ignore_index=True)
        if self.starting_cash is None:
            self.starting_cash = subportfolio.total_value
    
    def order_target_value(self, code: str, value: float, context: Context, date: str):
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        current_price = self.data_manager.get_current_price(code, date)
        
        if current_price is None or current_price <= 0:
            return None
        
        if code in subportfolio.positions:
            current_position = subportfolio.positions[code]
            current_value = current_position.total_amount * current_price
        else:
            current_value = 0
        
        if abs(value - current_value) < 100:
            return None
        
        if value > current_value:
            buy_value = value - current_value
            if buy_value > subportfolio.cash:
                buy_value = subportfolio.cash
            
            amount = int(buy_value / current_price / 100) * 100
            if amount <= 0:
                return None
            
            commission = max(amount * current_price * 0.0003, 5)
            total_cost = amount * current_price + commission
            
            if total_cost > subportfolio.cash:
                amount = int((subportfolio.cash - 5) / current_price / 100) * 100
                if amount <= 0:
                    return None
                total_cost = amount * current_price + max(amount * current_price * 0.0003, 5)
            
            subportfolio.cash -= total_cost
            
            if code not in subportfolio.positions:
                subportfolio.positions[code] = Position(code)
            
            pos = subportfolio.positions[code]
            total_amount = pos.total_amount + amount
            if total_amount > 0:
                pos.avg_cost = (pos.avg_cost * pos.total_amount + current_price * amount) / total_amount
            pos.total_amount = total_amount
            pos.amount = total_amount
            pos.price = current_price
            pos.value = pos.total_amount * current_price
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '买入',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission
            })
            
            return {'code': code, 'action': 'buy', 'amount': amount, 'price': current_price}
        
        elif value < current_value:
            if code not in subportfolio.positions:
                return None
            
            pos = subportfolio.positions[code]
            sell_value = current_value - value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                return None
            
            if amount > pos.total_amount:
                amount = pos.total_amount
            
            commission = max(amount * current_price * 0.0003, 5)
            stamp_tax = amount * current_price * 0.001
            revenue = amount * current_price - commission - stamp_tax
            
            subportfolio.cash += revenue
            pos.total_amount -= amount
            pos.amount = pos.total_amount
            pos.price = current_price
            pos.value = pos.total_amount * current_price
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '卖出',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission + stamp_tax
            })
            
            if pos.total_amount <= 0:
                del subportfolio.positions[code]
            
            return {'code': code, 'action': 'sell', 'amount': amount, 'price': current_price}
        
        return None
    
    def order_value(self, code: str, value: float, context: Context, date: str):
        return self.order_target_value(code, value, context, date)
    
    def order_target(self, code: str, amount: int, context: Context, date: str):
        if amount == 0:
            return self.order_target_value(code, 0, context, date)
        else:
            current_price = self.data_manager.get_current_price(code, date)
            if current_price:
                return self.order_target_value(code, amount * current_price, context, date)
        return None


class Cash(Strategy):
    def initialize(self, context: Context):
        self.target = "511880"
        pass


class PNFTPtCRITR(Strategy):
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        super().__init__(subportfolio_index, name, data_manager)
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
        self.factor_list = ['pb_ratio', 'roe', 'market_cap']
    
    def initialize(self, context: Context):
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
    
    def prepare_stock_list(self, context: Context, date: str):
        self.hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())
        
        if self.hold_list:
            df = self.data_manager.get_prices(self.hold_list, date)
            if not df.empty:
                self.yesterday_HL_list = []
            else:
                self.yesterday_HL_list = []
        else:
            self.yesterday_HL_list = []
    
    def get_stock_list(self, context: Context, date: str) -> List[str]:
        all_stocks = self.data_manager.get_all_stocks()
        all_stocks = self.filter_new_stock(context, all_stocks, date)
        all_stocks = self.filter_kcbj_stock(all_stocks)
        all_stocks = self.filter_st_stock(all_stocks, date)
        
        if len(all_stocks) == 0:
            return []
        
        sample_stocks = all_stocks[:200] if len(all_stocks) > 200 else all_stocks
        
        financial_df = self.data_manager.get_financial_data(sample_stocks)
        if financial_df.empty:
            return []
        
        financial_df = financial_df[(financial_df['net_profit'] > 0) & (financial_df['pb_ratio'] > 0)]
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df.sort_values('circulating_market_cap')
        final_list = financial_df.head(self.stock_num * 3)['code'].tolist()
        
        return final_list
    
    def weekly_adjustment(self, context: Context, date: str):
        target_list = self.get_stock_list(context, date)
        target_list = self.filter_paused_stock(target_list, date)
        target_list = target_list[:min(self.stock_num, len(target_list))]
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        for stock in list(self.hold_list):
            if stock not in subportfolio.positions:
                continue
            if stock not in target_list and stock not in self.yesterday_HL_list:
                self.order_target_value(stock, 0, context, date)
        
        position_count = len([p for p in subportfolio.positions.values() if p.total_amount > 0])
        target_num = len(target_list)
        
        if target_num > position_count:
            value = subportfolio.cash / (target_num - position_count) if (target_num - position_count) > 0 else 0
            for stock in target_list:
                pos = subportfolio.positions.get(stock)
                total_amount = pos.total_amount if pos is not None else 0
                if total_amount == 0:
                    self.order_target_value(stock, value, context, date)
                    if len([p for p in subportfolio.positions.values() if p.total_amount > 0]) == target_num:
                        break
    
    def check_limit_up(self, context: Context, date: str):
        pass
    
    def filter_paused_stock(self, stock_list: List[str], date: str) -> List[str]:
        return [s for s in stock_list if not self.data_manager.is_paused(s, date)]
    
    def filter_st_stock(self, stock_list: List[str], date: str) -> List[str]:
        result = []
        for s in tqdm(stock_list, desc="过滤ST股票", unit="只", leave=False):
            if not self.data_manager.is_st_stock(s, date):
                result.append(s)
        return result
    
    def filter_kcbj_stock(self, stock_list: List[str]) -> List[str]:
        out = []
        for stock in stock_list:
            stock_clean = stock.split('.')[0] if '.' in stock else stock
            if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
                continue
            out.append(stock)
        return out
    
    def filter_new_stock(self, context: Context, stock_list: List[str], date: str) -> List[str]:
        out = []
        new_stock_days = 200
        min_data_days = 180
        
        def check_stock_data(stock: str) -> Tuple[str, bool]:
            try:
                data = self.data_manager.get_stock_data(stock, end_date=date, days=new_stock_days)
                if data is not None and len(data) > min_data_days:
                    return (stock, True)
            except Exception:
                pass
            return (stock, False)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.data_manager.max_workers) as executor:
            futures = {executor.submit(check_stock_data, stock): stock for stock in stock_list}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="过滤新股", unit="只", leave=False):
                try:
                    stock, is_valid = future.result()
                    if is_valid:
                        out.append(stock)
                except Exception:
                    continue
        
        return out


class FMS_Strategy(Strategy):
    SW1 = {
        '801010': '农林牧渔', '801020': '采掘', '801030': '化工',
        '801040': '钢铁', '801050': '有色金属', '801060': '建筑建材',
        '801070': '机械设备', '801080': '电子', '801090': '交运设备',
        '801100': '信息设备', '801110': '家用电器', '801120': '食品饮料',
        '801130': '纺织服装', '801140': '轻工制造', '801150': '医药生物',
        '801160': '公用事业', '801170': '交通运输', '801180': '房地产',
        '801190': '金融服务', '801200': '商业贸易', '801210': '休闲服务',
        '801220': '信息服务', '801230': '综合', '801710': '建筑材料',
        '801720': '建筑装饰', '801730': '电气设备', '801740': '国防军工',
        '801750': '计算机', '801760': '传媒', '801770': '通信',
        '801780': '银行', '801790': '非银金融', '801880': '汽车',
        '801890': '机械设备', '801950': '煤炭', '801960': '石油石化',
        '801970': '环保', '801980': '美容护理'
    }
    
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        super().__init__(subportfolio_index, name, data_manager)
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
        self.num = 1
    
    def initialize(self, context: Context):
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
        self.num = 1
    
    def prepare_stock_list(self, context: Context, date: str):
        self.hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())
        self.yesterday_HL_list = []
    
    def get_stock_list(self, context: Context, date: str) -> List[str]:
        all_stocks = self.data_manager.get_all_stocks()
        all_stocks = self.filter_kcbj_stock(all_stocks)
        all_stocks = self.filter_st_stock(all_stocks, date)
        all_stocks = self.filter_new_stock(context, all_stocks, date)
        
        if len(all_stocks) == 0:
            return []
        
        sample_stocks = all_stocks[:100] if len(all_stocks) > 100 else all_stocks
        
        financial_df = self.data_manager.get_financial_data(sample_stocks)
        if financial_df.empty:
            return []
        
        financial_df = financial_df[
            (financial_df['roe'] > 0.15) & 
            (financial_df['net_profit'] > 0)
        ]
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df.sort_values('market_cap')
        final_list = financial_df.head(self.stock_num)['code'].tolist()
        
        return final_list
    
    def weekly_adjustment(self, context: Context, date: str):
        target_list = self.get_stock_list(context, date)
        target_list = self.filter_paused_stock(target_list, date)
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        for stock in list(self.hold_list):
            if stock not in subportfolio.positions:
                continue
            if stock not in target_list:
                self.order_target_value(stock, 0, context, date)
        
        position_count = len([p for p in subportfolio.positions.values() if p.total_amount > 0])
        target_num = len(target_list)
        
        if target_num > position_count and target_num > 0:
            value = subportfolio.cash / (target_num - position_count)
            for stock in target_list:
                pos = subportfolio.positions.get(stock)
                if pos is None or pos.total_amount == 0:
                    self.order_target_value(stock, value, context, date)
    
    def check_limit_up(self, context: Context, date: str):
        pass
    
    def filter_paused_stock(self, stock_list: List[str], date: str) -> List[str]:
        return [s for s in stock_list if not self.data_manager.is_paused(s, date)]
    
    def filter_st_stock(self, stock_list: List[str], date: str) -> List[str]:
        result = []
        for s in tqdm(stock_list, desc="过滤ST股票", unit="只", leave=False):
            if not self.data_manager.is_st_stock(s, date):
                result.append(s)
        return result
    
    def filter_kcbj_stock(self, stock_list: List[str]) -> List[str]:
        out = []
        for stock in stock_list:
            stock_clean = stock.split('.')[0] if '.' in stock else stock
            if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
                continue
            out.append(stock)
        return out
    
    def filter_new_stock(self, context: Context, stock_list: List[str], date: str) -> List[str]:
        out = []
        new_stock_days = 200
        min_data_days = 180
        
        def check_stock_data(stock: str) -> Tuple[str, bool]:
            try:
                data = self.data_manager.get_stock_data(stock, end_date=date, days=new_stock_days)
                if data is not None and len(data) > min_data_days:
                    return (stock, True)
            except Exception:
                pass
            return (stock, False)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.data_manager.max_workers) as executor:
            futures = {executor.submit(check_stock_data, stock): stock for stock in stock_list}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="过滤新股", unit="只", leave=False):
                try:
                    stock, is_valid = future.result()
                    if is_valid:
                        out.append(stock)
                except Exception:
                    continue
        
        return out


class Steal_Dog_Strategy(Strategy):
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        super().__init__(subportfolio_index, name, data_manager)
        self.ETF_POOL = ['518880', '513100', '159915']
        self.stock_num = 2
        self.strategy_type = '跑路'
        self.counterattack_days = 5
        self.momentum_days = 5
        self.days_counter = 0
        self.firsttrade = 0
        self.hold_list = []
        self.yesterday_HL_list = []
    
    def initialize(self, context: Context):
        self.ETF_POOL = ['518880', '513100', '159915']
        self.stock_num = 2
        self.strategy_type = '跑路'
        self.counterattack_days = 5
        self.momentum_days = 5
        self.days_counter = 0
        self.firsttrade = 0
        self.hold_list = []
        self.yesterday_HL_list = []
    
    def prepare_stock_list(self, context: Context, date: str):
        self.hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())
        self.yesterday_HL_list = []
    
    def calculate_momentum(self, etf: str, date: str, days: int = 25) -> float:
        data = self.data_manager.get_etf_data(etf, end_date=date, days=days + 10)
        if data is None or len(data) < days:
            return -9999.0
        
        close_prices = data['close'].values[-days:]
        y = np.log(close_prices)
        x = np.arange(len(y))
        weights = np.linspace(1, 2, len(y))
        
        try:
            slope, intercept = np.polyfit(x, y, 1, w=weights)
            annualized_return = math.exp(slope * 250) - 1
            residuals = y - (slope * x + intercept)
            r_squared = 1 - (np.sum(weights * residuals ** 2) / np.sum(weights * (y - np.mean(y)) ** 2))
            return annualized_return * r_squared
        except Exception:
            return -9999.0
    
    def get_top_momentum_etf(self, date: str) -> str:
        scores = {}
        for etf in self.ETF_POOL:
            score = self.calculate_momentum(etf, date)
            scores[etf] = score
        
        if not scores:
            return self.ETF_POOL[0]
        return max(scores, key=scores.get)
    
    def trade(self, context: Context, date: str):
        target_etf = self.get_top_momentum_etf(date)
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        for stock in list(subportfolio.positions.keys()):
            if stock != target_etf:
                self.order_target_value(stock, 0, context, date)
        
        if subportfolio.cash > 10000:
            self.order_target_value(target_etf, subportfolio.cash, context, date)
    
    def stop_loss(self, context: Context, date: str):
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        for stock in list(subportfolio.positions.keys()):
            if stock not in self.ETF_POOL:
                pos = subportfolio.positions[stock]
                if pos.price < pos.avg_cost * 0.92:
                    print(f"[{self.name}] 止损卖出 {stock}")
                    self.order_target_value(stock, 0, context, date)
    
    def filter_stocks(self, stock_list: List[str], date: str) -> List[str]:
        stock_list = [s for s in stock_list if not self.data_manager.is_paused(s, date)]
        stock_list = [s for s in stock_list if not self.data_manager.is_st_stock(s, date)]
        stock_list = self.filter_kcbj_stock(stock_list)
        return stock_list
    
    def filter_kcbj_stock(self, stock_list: List[str]) -> List[str]:
        out = []
        for stock in stock_list:
            stock_clean = stock.split('.')[0] if '.' in stock else stock
            if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
                continue
            out.append(stock)
        return out


class ETF_Rotation_Strategy(Strategy):
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        super().__init__(subportfolio_index, name, data_manager)
        self.etf_pool = [
            "513100", "513520", "513030",
            "518880", "161226", "159985",
            "511090", "159525", "513130",
            "159915", "159628"
        ]
        self.m_days = 25
    
    def initialize(self, context: Context):
        pass
    
    def calculate_momentum(self, etf: str, date: str) -> float:
        data = self.data_manager.get_etf_data(etf, end_date=date, days=self.m_days + 10)
        if data is None or len(data) < self.m_days:
            return -9999.0
        
        close_prices = data['close'].values[-self.m_days:]
        y = np.log(close_prices)
        x = np.arange(len(y))
        weights = np.linspace(1, 2, len(y))
        
        try:
            slope, intercept = np.polyfit(x, y, 1, w=weights)
            annualized_return = math.exp(slope * 250) - 1
            residuals = y - (slope * x + intercept)
            r_squared = 1 - (np.sum(weights * residuals ** 2) / np.sum(weights * (y - np.mean(y)) ** 2))
            return annualized_return * r_squared
        except Exception:
            return -9999.0
    
    def get_rank(self, date: str) -> List[str]:
        score_list = []
        for etf in self.etf_pool:
            score = self.calculate_momentum(etf, date)
            score_list.append((etf, score))
        
        df = pd.DataFrame(score_list, columns=['etf', 'score'])
        df = df.sort_values('score', ascending=False)
        df = df[(df['score'] > 0) & (df['score'] <= 5)]
        
        return df['etf'].tolist()
    
    def trade(self, context: Context, date: str):
        target_list = self.get_rank(date)[:1]
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        hold_list = list(subportfolio.positions.keys())
        for etf in hold_list:
            if etf not in target_list:
                self.order_target_value(etf, 0, context, date)
        
        hold_list = list(subportfolio.positions.keys())
        if len(hold_list) < 1 and len(target_list) > 0:
            target_etf = target_list[0]
            value = subportfolio.cash
            self.order_target_value(target_etf, value, context, date)


class MultiStrategyBacktest:
    def __init__(self, start_date: str = '2022-01-01', end_date: str = None, 
                 initial_cash: float = 1000000.0):
        self.context = Context()
        self.g = GlobalParams()
        self.data_manager = DataManager()
        
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.initial_cash = initial_cash
        
        self.trade_days: List[str] = []
        self.daily_values: List[Dict] = []
        self.trade_records: List[Dict] = []
        
        self.STRATEGY_CONFIG = [
            {
                "name": "搅屎棍",
                "class": FMS_Strategy,
                "pct": 0.43,
            },
            {
                "name": "偷鸡摸狗",
                "class": Steal_Dog_Strategy,
                "pct": 0.22,
            },
            {
                "name": "ETF轮动",
                "class": ETF_Rotation_Strategy,
                "pct": 0.35,
            },
        ]
    
    def initialize(self):
        print("=" * 60)
        print("初始化多策略回测框架")
        print("=" * 60)
        
        print("正在获取交易日历...")
        self.trade_days = self.data_manager.get_trade_days(self.start_date, self.end_date)
        print(f"获取到 {len(self.trade_days)} 个交易日")
        
        total_pct = sum(s["pct"] for s in self.STRATEGY_CONFIG)
        if abs(total_pct - 1.0) > 0.001:
            print(f"警告: 策略配置比例总和为 {total_pct}，调整为1.0")
        
        self.context.portfolio = Portfolio(self.initial_cash)
        
        self.g.strategys = []
        for i, config in enumerate(self.STRATEGY_CONFIG):
            if config["pct"] == 0:
                continue
            
            subportfolio_cash = self.initial_cash * config["pct"]
            subportfolio = SubPortfolio(subportfolio_cash)
            self.context.portfolio.subportfolios.append(subportfolio)
            
            strategy = config["class"](i, config["name"], self.data_manager)
            strategy.initialize(self.context)
            self.g.strategys.append(strategy)
            
            print(f"初始化策略: {config['name']}, 资金: {subportfolio_cash:,.2f} ({config['pct']*100:.0f}%)")
    
    def preload_data(self, preload_stocks: int = 200):
        print("\n" + "=" * 60)
        print("预加载数据...")
        print("=" * 60)
        
        all_stocks = self.data_manager.get_all_stocks()
        print(f"获取到 {len(all_stocks)} 只股票")
        
        stocks_to_preload = all_stocks[:preload_stocks]
        end_date = self.end_date
        
        def preload_stock_data(stock: str) -> bool:
            try:
                self.data_manager.get_stock_data(stock, end_date=end_date, days=250)
                return True
            except Exception:
                return False
        
        print(f"预加载前 {preload_stocks} 只股票数据...")
        success_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.data_manager.max_workers) as executor:
            futures = {executor.submit(preload_stock_data, stock): stock for stock in stocks_to_preload}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="预加载股票数据", unit="只"):
                try:
                    if future.result():
                        success_count += 1
                except Exception:
                    continue
        
        print(f"预加载完成: {success_count}/{preload_stocks} 只股票")
        
        print("预加载ETF数据...")
        etf_pool = ['518880', '513100', '159915', '159628', '161226', '159985', '159525', '511090']
        for etf in tqdm(etf_pool, desc="预加载ETF数据", unit="只"):
            try:
                self.data_manager.get_etf_data(etf, end_date=end_date, days=100)
            except Exception:
                continue
        print("ETF数据预加载完成")
    
    def run_backtest(self, preload: bool = True):
        self.initialize()
        
        if preload:
            self.preload_data(preload_stocks=200)
        
        print("\n" + "=" * 60)
        print("开始运行回测...")
        print(f"回测区间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print("=" * 60)
        
        for i, date in enumerate(tqdm(self.trade_days, desc="回测进度", unit="天")):
            self.context.current_dt = pd.to_datetime(date)
            self.context.previous_date = self.trade_days[i-1] if i > 0 else date
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'prepare_stock_list'):
                    try:
                        strategy.prepare_stock_list(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] prepare_stock_list 错误: {e}")
            
            if i % 5 == 0:
                for strategy in self.g.strategys:
                    if hasattr(strategy, 'weekly_adjustment'):
                        try:
                            strategy.weekly_adjustment(self.context, date)
                        except Exception as e:
                            print(f"\n[{strategy.name}] weekly_adjustment 错误: {e}")
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'trade'):
                    try:
                        strategy.trade(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] trade 错误: {e}")
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'stop_loss'):
                    try:
                        strategy.stop_loss(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] stop_loss 错误: {e}")
            
            for strategy in self.g.strategys:
                subportfolio = self.context.portfolio.subportfolios[strategy.subportfolio_index]
                prices = {}
                for code in list(subportfolio.positions.keys()):
                    price = self.data_manager.get_current_price(code, date)
                    if price:
                        prices[code] = price
                subportfolio.update_positions_value(prices)
            
            for strategy in self.g.strategys:
                try:
                    strategy.record_daily_value(self.context)
                except Exception as e:
                    pass
            
            self.context.portfolio.update_total_value()
            
            self.daily_values.append({
                'date': date,
                'total_value': self.context.portfolio.total_value,
                'cash': self.context.portfolio.cash,
            })
        
        self.print_results()
        self.save_results()
    
    def _print_trade_summary(self, all_trades: List[Dict]):
        print("\n" + "=" * 60)
        print("交易记录汇总")
        print("=" * 60)
        
        trades_by_strategy = {}
        for trade in all_trades:
            strategy = trade.get('strategy', '未知')
            if strategy not in trades_by_strategy:
                trades_by_strategy[strategy] = []
            trades_by_strategy[strategy].append(trade)
        
        for strategy_name, trades in trades_by_strategy.items():
            print(f"\n【{strategy_name}】策略交易记录:")
            print("-" * 50)
            
            buy_count = sum(1 for t in trades if t.get('action') == '买入')
            sell_count = sum(1 for t in trades if t.get('action') == '卖出')
            total_buy_value = sum(t.get('value', 0) for t in trades if t.get('action') == '买入')
            total_sell_value = sum(t.get('value', 0) for t in trades if t.get('action') == '卖出')
            
            print(f"  买入次数: {buy_count} 次, 卖出次数: {sell_count} 次")
            print(f"  买入金额: {total_buy_value:,.2f} 元")
            print(f"  卖出金额: {total_sell_value:,.2f} 元")
            
            print("\n  详细交易:")
            for trade in trades:
                date = trade.get('date', '')
                code = trade.get('code', '')
                action = trade.get('action', '')
                price = trade.get('price', 0)
                amount = trade.get('amount', 0)
                value = trade.get('value', 0)
                print(f"    {date} | {action} {code} | 价格: {price:.2f} | 数量: {amount} | 金额: {value:,.2f}")

    def print_results(self):
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
        
        print("\n各策略表现:")
        for strategy in self.g.strategys:
            if strategy.starting_cash and strategy.starting_cash > 0:
                final_value = self.context.portfolio.subportfolios[strategy.subportfolio_index].total_value
                returns = (final_value / strategy.starting_cash - 1) * 100
                print(f"  [{strategy.name}]: 收益率 {returns:.2f}%")
    
    def save_results(self):
        if len(self.daily_values) > 0:
            df = pd.DataFrame(self.daily_values)
            output_path = os.path.join(os.path.dirname(__file__), 'backtest_daily_values.csv')
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"\n每日净值已保存至: {output_path}")
        
        all_trades = []
        for strategy in self.g.strategys:
            if hasattr(strategy, 'trade_records'):
                for trade in strategy.trade_records:
                    trade_copy = trade.copy()
                    trade_copy['strategy'] = strategy.name
                    all_trades.append(trade_copy)
        
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            trades_path = os.path.join(os.path.dirname(__file__), 'trade_records.csv')
            trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
            print(f"交易记录已保存至: {trades_path}")
            self._print_trade_summary(all_trades)
        
        strategy_values = {}
        for strategy in self.g.strategys:
            if hasattr(strategy, 'portfolio_value') and len(strategy.portfolio_value) > 0:
                strategy_values[strategy.name] = strategy.portfolio_value
        
        if MultiStrategyPDFReport is not None:
            pdf_path = os.path.join(os.path.dirname(__file__), 'backtest_report.pdf')
            try:
                pdf_generator = MultiStrategyPDFReport(
                    strategy_name='多策略组合',
                    daily_values=self.daily_values,
                    strategy_values=strategy_values,
                    strategy_configs=self.STRATEGY_CONFIG,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    initial_cash=self.initial_cash
                )
                pdf_generator.generate_pdf_report(pdf_path)
            except Exception as e:
                print(f"生成PDF报告失败: {e}")
        
        if MultiStrategyReportGenerator is not None:
            report_path = os.path.join(os.path.dirname(__file__), 'multi_strategy_report.html')
            try:
                generator = MultiStrategyReportGenerator(
                    strategy_name='多策略组合',
                    daily_values=self.daily_values,
                    strategy_values=strategy_values,
                    strategy_configs=self.STRATEGY_CONFIG,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    initial_cash=self.initial_cash
                )
                generator.generate_html_report(report_path)
            except Exception as e:
                print(f"生成HTML报告失败: {e}")


def main():
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    backtest = MultiStrategyBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_cash=1000000.0
    )
    
    backtest.run_backtest()


if __name__ == '__main__':
    main()
