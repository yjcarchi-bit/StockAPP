# 克隆自聚宽文章：https://www.joinquant.com/post/63661
# 标题：三马v10.2 测试框架
# 作者：Cibo
# 本地化版本：使用efinance数据源

"""
Cibo 三驾马车优化版 - 本地化版本
策略1：小市值策略
策略2：ETF反弹策略 (只能测试 23.9月后, 2000etf上市时间为23.9)
策略3：ETF轮动策略
策略4：白马攻防 v2.0

本地化说明：
- 使用efinance替代jqdata作为数据源
- 使用akshare-proxy-patch解决东方财富API连接问题（可选）
- 使用本地回测框架替代聚宽平台
- 保持原有策略逻辑不变
"""

try:
    import akshare_proxy_patch
    akshare_proxy_patch.install_patch("101.201.173.125", "20260227DWVU", 30)
    USE_PROXY_PATCH = True
except ImportError:
    USE_PROXY_PATCH = False
    print("⚠️ akshare-proxy-patch未安装，将使用备用数据源")

import datetime
import math
import numpy as np
import pandas as pd
from datetime import timedelta
from typing import List, Dict, Optional, Tuple
import warnings
import os
import sys
import concurrent.futures
from functools import lru_cache
from tqdm import tqdm
import requests
import json
import re

try:
    import efinance as ef
    USE_EFINANCE = True
except ImportError:
    USE_EFINANCE = False
    print("⚠️ efinance未安装，将使用新浪/腾讯API")

# 检测额度是否用完
def check_efinance_available():
    if not USE_EFINANCE:
        return False
    try:
        df = ef.stock.get_quote_history('000001', beg='20250220', end='20250227', klt=101, fqt=1)
        return df is not None and len(df) > 0
    except:
        return False

EFINANCE_AVAILABLE = check_efinance_available()
if not EFINANCE_AVAILABLE and USE_EFINANCE:
    print("⚠️ efinance额度已用完或不可用，将使用备用数据源")

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
        self.init_time = None
    
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
        self.positions = {}
        for sp in self.subportfolios:
            self.positions.update(sp.positions)


class Context:
    def __init__(self):
        self.current_dt = None
        self.previous_date = None
        self.portfolio = Portfolio()
        self.subportfolios = []


class GlobalParams:
    def __init__(self):
        self.portfolio_value_proportion = [0.5, 0, 0.5, 0]
        self.starting_cash = 1000000.0
        self.stock_strategy = {}
        self.strategy_holdings = {1: [], 2: [], 3: [], 4: []}
        self.strategy_starting_cash = {}
        self.strategy_value_data = {}
        self.strategy_value = {}
        self.strategy_ETF_2000_proportion = 0
        self.strategy_ETF_2000_proportion_reset = None
        
        self.trading_signal = False
        self.huanshou_check = False
        self.xsz_version = "v3"
        self.enable_dynamic_stock_num = True
        self.xsz_stock_num = 5
        self.yesterday_HL_list = []
        self.target_list = []
        self.xsz_buy_etf = "512800"
        self.run_stoploss = True
        self.stoploss_strategy = 3
        self.stoploss_limit = 0.09
        self.stoploss_market = 0.05
        self.DBL_control = True
        self.dbl = []
        self.check_dbl_days = 10
        self.check_after_no_buy = False
        self.no_buy_stocks = {}
        self.no_buy_after_day = 3
        self.check_defense = False
        self.industries = ["组20"]
        self.defense_signal = None
        self.cnt_defense_signal = []
        self.cnt_bank_signal = []
        self.history_defense_date_list = []
        
        self.limit_days = 2
        self.n_days = 5
        self.holding_days = 0
        self.buy_list = []
        self.etf_pool_2 = ['159536', '159629', '159922', '159919', '159783']
        
        self.etf_pool_3 = [
            "510180", "513030", "513100", "513520",
            "510410", "518880", "501018", "159985", "511090",
            "159915", "588120", "512480", "159851", "513020", "159637",
            "513630", "510050"
        ]
        self.select_etf = None
        self.buy_etf = None
        self.m_days = 25
        self.m_score = 5
        self.enable_stop_loss_by_cur_day = True
        self.stoploss_limit_by_cur_day = -0.03
        
        self.check_out_lists = []
        self.market_temperature = "warm"
        self.stock_num_2 = 5
        self.roe = 10
        self.roa = 6


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
        self.stock_info_cache: Dict[str, Dict] = {}
        self.max_workers = 10
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
    
    def _get_market_code(self, code: str) -> str:
        code = code.split('.')[0] if '.' in code else code
        code = code.strip()
        if code.startswith('sh') or code.startswith('sz'):
            return code
        if code.startswith('6') or code.startswith('51') or code.startswith('58'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3') or code.startswith('15') or code.startswith('16'):
            return f"sz{code}"
        else:
            return f"sh{code}"
    
    def get_trade_days(self, start_date: str, end_date: str, index_code: str = '000300') -> List[str]:
        cache_key = f"{start_date}_{end_date}_{index_code}"
        if cache_key in self.trade_days_cache:
            return self.trade_days_cache
        
        # 尝试使用efinance
        if EFINANCE_AVAILABLE:
            try:
                beg = format_date_for_efinance(start_date)
                end = format_date_for_efinance(end_date)
                df = ef.stock.get_quote_history(index_code, beg=beg, end=end, klt=101, fqt=1)
                if df is not None and len(df) > 0:
                    days = df['日期'].tolist()
                    self.trade_days_cache = days
                    return days
            except Exception as e:
                print(f"efinance获取交易日历失败: {e}")
        
        # 备用：使用新浪API
        try:
            market_code = self._get_market_code(index_code)
            url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
            params = {'symbol': market_code, 'scale': '240', 'ma': 'no', 'datalen': '500'}
            response = self._session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data:
                    days = [item['day'] for item in data]
                    start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                    filtered_days = [d for d in days if start_dt <= datetime.datetime.strptime(d, '%Y-%m-%d') <= end_dt]
                    self.trade_days_cache = filtered_days
                    return filtered_days
        except Exception as e:
            print(f"新浪API获取交易日历失败: {e}")
        
        # 最后备用：生成工作日
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
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
        stock_code = code.split('.')[0] if '.' in code else code
        cache_key = f"{stock_code}_{start_date}_{end_date}_{days}"
        if cache_key in self.stock_cache:
            return self.stock_cache[cache_key]
        
        # 尝试使用efinance
        if EFINANCE_AVAILABLE:
            try:
                if end_date is None:
                    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
                if start_date is None:
                    start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days*2)).strftime('%Y-%m-%d')
                
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
        
        # 备用：使用新浪API
        try:
            market_code = self._get_market_code(stock_code)
            url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
            params = {'symbol': market_code, 'scale': '240', 'ma': 'no', 'datalen': str(min(days * 2, 500))}
            
            response = self._session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    df = df.rename(columns={'day': 'date', 'open': 'open', 'close': 'close',
                                            'high': 'high', 'low': 'low', 'volume': 'volume'})
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                    for col in ['open', 'close', 'high', 'low', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    df['code'] = code
                    df['amount'] = df['close'] * df['volume']
                    df['change_pct'] = df['close'].pct_change() * 100
                    
                    if start_date:
                        start_dt = pd.to_datetime(start_date)
                        df = df[df.index >= start_dt]
                    if end_date:
                        end_dt = pd.to_datetime(end_date)
                        df = df[df.index <= end_dt]
                    
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
        
        # 尝试使用efinance
        if EFINANCE_AVAILABLE:
            try:
                df = ef.stock.get_realtime_quotes()
                if df is not None and len(df) > 0:
                    codes = df['股票代码'].tolist()
                    codes = [c for c in codes if c.startswith(('6', '0', '3')) and not c.startswith('68')]
                    self.all_stocks_cache = codes
                    return codes
            except Exception as e:
                print(f"efinance获取股票列表失败: {e}")
        
        # 备用：返回默认股票列表
        default_stocks = ['000001', '000002', '000063', '000333', '000651',
                         '000725', '000858', '002415', '002594', '600000',
                         '600036', '600519', '600887', '601318', '601398',
                         '601288', '601166', '600276', '600030', '601888']
        self.all_stocks_cache = default_stocks
        return default_stocks
    
    def get_current_price(self, code: str, date: str) -> Optional[float]:
        stock_data = self.get_stock_data(code, end_date=date, days=30)
        if stock_data is not None and len(stock_data) > 0:
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
        # 尝试使用efinance
        if USE_EFINANCE:
            try:
                series = ef.stock.get_base_info(code)
                if series is not None and len(series) > 0:
                    row = {'code': code}
                    row['market_cap'] = series.get('总市值', 0)
                    row['circulating_market_cap'] = series.get('流通市值', 0)
                    row['pe_ratio'] = series.get('市盈率(动)', 0)
                    row['pb_ratio'] = series.get('市净率', 0)
                    row['roe'] = float(series.get('ROE', 0) or 0)
                    row['net_profit'] = series.get('净利润', 0)
                    row['operating_revenue'] = series.get('营业收入', 0)
                    name = str(series.get('股票名称', ''))
                    self.stock_name_cache[code] = name
                    self.st_stock_cache[code] = 'ST' in name or '*' in name or '退' in name
                    self.stock_info_cache[code] = row
                    return row
            except Exception:
                pass
        
        # 备用：使用新浪行情接口获取基本信息
        try:
            market_code = self._get_market_code(code)
            url = f"https://hq.sinajs.cn/list={market_code}"
            response = self._session.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text
                if 'hq_str_' in content:
                    match = re.search(r'="([^"]*)"', content)
                    if match:
                        parts = match.group(1).split(',')
                        if len(parts) >= 35:
                            name = parts[0]
                            close = float(parts[3]) if parts[3] else 0
                            self.stock_name_cache[code] = name
                            self.st_stock_cache[code] = 'ST' in name or '*' in name or '退' in name
                            row = {
                                'code': code,
                                'name': name,
                                'close': close,
                                'market_cap': 0,
                                'circulating_market_cap': 0,
                                'roe': 0,
                                'net_profit': 0,
                                'operating_revenue': 0
                            }
                            self.stock_info_cache[code] = row
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
        
        # 尝试使用efinance
        if USE_EFINANCE:
            try:
                if index_code_clean in ['000300', '399101', '000985']:
                    df = ef.stock.get_constituent_stocks(index_code_clean, date=date.replace('-', '') if date else None)
                    if df is not None and len(df) > 0:
                        codes = df['股票代码'].tolist() if '股票代码' in df.columns else []
                        self.industry_cache[cache_key] = codes
                        return codes
            except Exception:
                pass
        
        # 备用：返回所有股票
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
        
        self._get_single_financial_data(code)
        return self.st_stock_cache.get(code, False)
    
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
    
    def get_stock_info(self, code: str) -> Dict:
        if code in self.stock_info_cache:
            return self.stock_info_cache[code]
        
        self._get_single_financial_data(code)
        return self.stock_info_cache.get(code, {})
    
    def get_stock_name(self, code: str) -> str:
        if code in self.stock_name_cache:
            return self.stock_name_cache[code]
        
        info = self.get_stock_info(code)
        name = info.get('股票名称', info.get('name', code))
        self.stock_name_cache[code] = name
        return name


class MarketBreadthDefense:
    
    def get_current_price(self, code: str, date: str) -> Optional[float]:
        stock_data = self.get_stock_data(code, end_date=date, days=30)
        if stock_data is not None and len(stock_data) > 0:
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
            market_code = self._get_market_code(code)
            url = f"https://hq.sinajs.cn/list={market_code}"
            response = self._session.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text
                if 'hq_str_' in content:
                    match = re.search(r'="([^"]*)"', content)
                    if match:
                        parts = match.group(1).split(',')
                        if len(parts) >= 35:
                            name = parts[0]
                            close = float(parts[3]) if parts[3] else 0
                            self.stock_name_cache[code] = name
                            self.st_stock_cache[code] = 'ST' in name or '*' in name or '退' in name
                            
                            row = {
                                'code': code,
                                'name': name,
                                'close': close,
                                'market_cap': 0,
                                'circulating_market_cap': 0,
                                'pe_ratio': 0,
                                'pb_ratio': 0,
                                'roe': 0,
                                'net_profit': 0,
                                'operating_revenue': 0
                            }
                            self.stock_info_cache[code] = row
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
        
        all_stocks = self.get_all_stocks()
        self.industry_cache[cache_key] = all_stocks[:200]
        return all_stocks[:200]
    
    def is_st_stock(self, code: str, date: str = None) -> bool:
        if code in self.st_stock_cache:
            return self.st_stock_cache[code]
        
        if code in self.stock_name_cache:
            name = self.stock_name_cache[code]
            result = 'ST' in name or '*' in name or '退' in name
            self.st_stock_cache[code] = result
            return result
        
        self._get_single_financial_data(code)
        return self.st_stock_cache.get(code, False)
    
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
    
    def get_stock_info(self, code: str) -> Dict:
        if code in self.stock_info_cache:
            return self.stock_info_cache[code]
        
        self._get_single_financial_data(code)
        return self.stock_info_cache.get(code, {})
    
    def get_stock_name(self, code: str) -> str:
        if code in self.stock_name_cache:
            return self.stock_name_cache[code]
        
        info = self.get_stock_info(code)
        name = info.get('name', code)
        self.stock_name_cache[code] = name
        return name


g = GlobalParams()


class MarketBreadthDefense:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.check_defense = False
        self.defense_signal = False
        self.defense_group = "组20"
        self.cnt_defense_signal = []
        self.cnt_bank_signal = []
        self.history_defense_date_list = []
        self._cache = {}
    
    def get_market_breadth(self, date: str, ma_days: int = 20, sample_size: int = 500) -> Tuple[pd.Series, pd.DataFrame]:
        cache_key = f"breadth_{date}_{ma_days}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        all_stocks = self.data_manager.get_all_stocks()
        sample_stocks = all_stocks[:sample_size] if len(all_stocks) > sample_size else all_stocks
        
        required_days = ma_days + 10
        price_data = {}
        volume_data = {}
        
        for stock in tqdm(sample_stocks, desc=f"获取市场宽度数据({date})", leave=False):
            data = self.data_manager.get_stock_data(stock, end_date=date, days=required_days)
            if data is not None and len(data) >= ma_days:
                price_data[stock] = data['close']
                volume_data[stock] = data.get('volume', data.get('amount', pd.Series()))
        
        if not price_data:
            return pd.Series(), pd.DataFrame()
        
        price_df = pd.DataFrame(price_data)
        ma = price_df.rolling(window=ma_days).mean()
        above_ma = price_df > ma
        
        volume_df = pd.DataFrame(volume_data)
        recent_volume = volume_df.tail(20)
        avg_volume = recent_volume.mean()
        
        avg_volume_df = pd.DataFrame({'code': avg_volume.index, 'avg_volume': avg_volume.values})
        avg_volume_df = avg_volume_df.dropna()
        avg_volume_df = avg_volume_df.sort_values('avg_volume', ascending=False)
        
        try:
            avg_volume_df['volume_group'] = pd.qcut(
                avg_volume_df['avg_volume'], 20, 
                labels=[f'组{i + 1}' for i in range(20)],
                duplicates='drop'
            )
        except Exception:
            n_groups = min(20, len(avg_volume_df))
            avg_volume_df['volume_group'] = pd.cut(
                avg_volume_df['avg_volume'], n_groups,
                labels=[f'组{i + 1}' for i in range(n_groups)]
            )
        
        volume_groups = {group: group_df['code'].tolist() 
                        for group, group_df in avg_volume_df.groupby('volume_group')}
        
        group_scores = pd.DataFrame(index=price_df.index)
        for group, stocks in volume_groups.items():
            valid_stocks = list(set(above_ma.columns) & set(stocks))
            if valid_stocks:
                group_scores[group] = 100 * above_ma[valid_stocks].sum(axis=1) / len(valid_stocks)
        
        recent_group_data = group_scores[-3:].mean()
        sorted_ma_data = recent_group_data.sort_values(ascending=False)
        
        pct_changes = price_df.pct_change()
        recent_pct = pct_changes.tail(3)
        
        result = pd.DataFrame({
            'up_ratio': recent_pct.apply(lambda x: (x > 0).mean(), axis=1).values,
            'down_over': recent_pct.apply(lambda x: (x <= -0.0985).sum(), axis=1).values
        })
        
        self._cache[cache_key] = (sorted_ma_data, result)
        return sorted_ma_data, result
    
    def calculate_trend_indicators(self, date: str, index_code: str = '399101') -> Tuple[bool, List[bool]]:
        high_lookback = 60
        high_proximity = 0.95
        check_days = 2
        
        data = self.data_manager.get_stock_data(index_code, end_date=date, days=high_lookback + 10)
        if data is None or len(data) < high_lookback:
            return False, [False] * (check_days + 1)
        
        past_is_high_list = []
        
        for i in range(-check_days, 0):
            valid_data = data.iloc[:i][-high_lookback:]
            if len(valid_data) < high_lookback:
                past_is_high_list.append(False)
                continue
            
            current_day_price = valid_data['close'].iloc[-1]
            day_max_high = valid_data['high'].max()
            day_close_to_high = current_day_price >= (day_max_high * high_proximity)
            past_is_high_list.append(day_close_to_high)
        
        current_data = data[-high_lookback:]
        current_price = current_data['close'].iloc[-1]
        max_high = current_data['high'].max()
        close_to_high = current_price >= (max_high * high_proximity)
        past_is_high_list.append(close_to_high)
        
        is_high = any(past_is_high_list)
        return is_high, past_is_high_list
    
    def check_defense_trigger(self, date: str) -> bool:
        if not self.check_defense:
            return False
        
        if self.defense_signal:
            sorted_ma_data, result = self.get_market_breadth(date, 20)
            if sorted_ma_data.empty:
                return self.defense_signal
            
            up_ratio = result['up_ratio'].mean()
            avg_score = sorted_ma_data.get('组1', 50)
            
            defense_in_top = self.defense_group in sorted_ma_data.index[:3]
            bank_exit_signal = not defense_in_top
            
            self.defense_signal = not bank_exit_signal
            print(f"组20防御: {self.defense_signal} 组1宽度:{avg_score:.1f} 涨跌比:{up_ratio:.2f}")
        else:
            is_high, past_is_high_list = self.calculate_trend_indicators(date)
            
            if is_high:
                sorted_ma_data, result = self.get_market_breadth(date, 20)
                if sorted_ma_data.empty:
                    return False
                
                defense_in_top = self.defense_group in sorted_ma_data.index[:2]
                
                other_groups = [g for g in sorted_ma_data.index if g != self.defense_group]
                avg_score = sorted_ma_data[other_groups].mean() if other_groups else 50
                
                up_ratio = result['up_ratio'].mean()
                
                above_average = avg_score < 60
                above_ratio = up_ratio < 0.5
                
                is_bank_defense = defense_in_top and above_average and above_ratio
                self.defense_signal = is_bank_defense
                
                if is_bank_defense:
                    self.cnt_bank_signal.append(True)
                
                print(f"组20防御: {is_bank_defense} 高位:{is_high}{past_is_high_list} "
                      f"组1宽度:{avg_score:.1f} 涨跌比:{up_ratio:.2f}")
            else:
                self.defense_signal = False
                print(f"触发防御: {self.defense_signal} 高位:{is_high}{past_is_high_list}")
        
        return self.defense_signal


class SmallCapStrategy:
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.data_manager = data_manager
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None
        self.trade_records = []
        
        self.trading_signal = False
        self.huanshou_check = False
        self.xsz_version = "v3"
        self.enable_dynamic_stock_num = True
        self.xsz_stock_num = 5
        self.yesterday_HL_list = []
        self.target_list = []
        self.xsz_buy_etf = "512800"
        self.run_stoploss = True
        self.stoploss_strategy = 3
        self.stoploss_limit = 0.09
        self.stoploss_market = 0.05
        self.DBL_control = True
        self.dbl = []
        self.check_dbl_days = 10
        self.hold_list = []
        self.market_defense = None
        self.enable_market_defense = False
    
    def initialize(self, context: Context):
        self.trading_signal = False
        self.huanshou_check = False
        self.xsz_version = "v3"
        self.enable_dynamic_stock_num = True
        self.xsz_stock_num = 5
        self.yesterday_HL_list = []
        self.target_list = []
        self.xsz_buy_etf = "512800"
        self.run_stoploss = True
        self.stoploss_strategy = 3
        self.stoploss_limit = 0.09
        self.stoploss_market = 0.05
        self.DBL_control = True
        self.dbl = []
        self.check_dbl_days = 10
        self.hold_list = []
        
        if self.enable_market_defense:
            self.market_defense = MarketBreadthDefense(self.data_manager)
            self.market_defense.check_defense = True
    
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
            pos.init_time = date
            
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
            
            print(f"🚚🚚🚚 {self.format_stock_code(code)} 买价{current_price:<7.2f} 买量{amount:<7} 价值{amount * current_price:.2f}")
            return {'code': code, 'action': 'buy', 'amount': amount, 'price': current_price}
        
        elif value < current_value:
            if code not in subportfolio.positions:
                return None
            
            pos = subportfolio.positions[code]
            sell_value = current_value - value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                amount = pos.total_amount
            
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
            
            pnl = (current_price - pos.avg_cost) * amount
            pnl_pct = (current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '卖出',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission + stamp_tax,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            print(f"🚛🚛🚛 {self.format_stock_code(code)} 卖价{current_price:<7.2f} 成本{pos.avg_cost:<7.2f} 卖量{amount:<7} 盈亏{pnl:.2f}({pnl_pct:.2f}%)")
            
            if pos.total_amount <= 0:
                del subportfolio.positions[code]
            
            return {'code': code, 'action': 'sell', 'amount': amount, 'price': current_price}
        
        return None
    
    def format_stock_code(self, stock_code: str) -> str:
        try:
            name = self.data_manager.get_stock_name(stock_code)
            return f"{stock_code[:6]}({name})"
        except Exception:
            return f"{stock_code[:6]}"
    
    def filter_stocks(self, stock_list: List[str], date: str) -> List[str]:
        result = []
        for stock in stock_list:
            if self.data_manager.is_paused(stock, date):
                continue
            if self.data_manager.is_st_stock(stock, date):
                continue
            
            stock_clean = stock.split('.')[0] if '.' in stock else stock
            if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
                continue
            
            data = self.data_manager.get_stock_data(stock, end_date=date, days=400)
            if data is None or len(data) < 375:
                continue
            
            result.append(stock)
        return result
    
    def get_stock_list_v1(self, context: Context, date: str) -> List[str]:
        print(f"\n🔍 小市值v1选股中...")
        all_stocks = self.data_manager.get_index_stocks('399101', date)
        all_stocks = self.filter_stocks(all_stocks, date)
        print(f"  📊 筛选后股票数: {len(all_stocks)}")
        
        if len(all_stocks) == 0:
            return []
        
        sample_stocks = all_stocks[:200] if len(all_stocks) > 200 else all_stocks
        print(f"  📊 获取财务数据: {len(sample_stocks)} 只...")
        financial_df = self.data_manager.get_financial_data(sample_stocks)
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df[financial_df['circulating_market_cap'] > 0]
        financial_df = financial_df.sort_values('circulating_market_cap')
        
        initial_list = financial_df.head(50)['code'].tolist()
        
        final_list = initial_list[:self.xsz_stock_num]
        print(f'  ✅ 选出的股票: {[self.format_stock_code(s) for s in final_list]}')
        return final_list
    
    def get_stock_list_v2(self, context: Context, date: str) -> List[str]:
        print(f"\n🔍 小市值v2选股中...")
        all_stocks = self.data_manager.get_index_stocks('399101', date)
        all_stocks = self.filter_stocks(all_stocks, date)
        print(f"  📊 筛选后股票数: {len(all_stocks)}")
        
        if len(all_stocks) == 0:
            return []
        
        sample_stocks = all_stocks[:200] if len(all_stocks) > 200 else all_stocks
        print(f"  📊 获取财务数据: {len(sample_stocks)} 只...")
        financial_df = self.data_manager.get_financial_data(sample_stocks)
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df[
            (financial_df['market_cap'] >= 5) & 
            (financial_df['market_cap'] <= 50) &
            (financial_df['net_profit'] > 0) &
            (financial_df['roe'] > 0.15)
        ]
        print(f"  📊 财务筛选后: {len(financial_df)} 只")
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df.sort_values('market_cap')
        final_list = financial_df.head(self.xsz_stock_num)['code'].tolist()
        print(f'  ✅ 选出的股票: {[self.format_stock_code(s) for s in final_list]}')
        
        return final_list
    
    def get_stock_list_v3(self, context: Context, date: str) -> List[str]:
        print(f"\n🔍 小市值v3选股中...")
        all_stocks = self.data_manager.get_index_stocks('399101', date)
        all_stocks = self.filter_stocks(all_stocks, date)
        print(f"  📊 筛选后股票数: {len(all_stocks)}")
        
        if len(all_stocks) == 0:
            return []
        
        sample_stocks = all_stocks[:200] if len(all_stocks) > 200 else all_stocks
        print(f"  📊 获取财务数据: {len(sample_stocks)} 只...")
        financial_df = self.data_manager.get_financial_data(sample_stocks)
        
        if financial_df.empty:
            return []
        
        financial_df = financial_df[
            (financial_df['market_cap'] >= 10) & 
            (financial_df['market_cap'] <= 100) &
            (financial_df['net_profit'] > 2000000) &
            (financial_df['roe'] > 0) &
            (financial_df['operating_revenue'] > 1e8)
        ]
        print(f"  📊 财务筛选后: {len(financial_df)} 只")
        
        if financial_df.empty:
            print('  ⚠️ 无适合股票，买入ETF')
            return [self.xsz_buy_etf]
        
        financial_df = financial_df.sort_values('market_cap')
        final_list = financial_df.head(self.xsz_stock_num * 3)['code'].tolist()
        
        price_filtered = []
        for stock in final_list:
            price = self.data_manager.get_current_price(stock, date)
            if price and price <= 50:
                price_filtered.append(stock)
        
        print(f"  📊 价格筛选后(≤50元): {len(price_filtered)} 只")
        result = price_filtered[:self.xsz_stock_num]
        print(f'  ✅ 选出的股票: {[self.format_stock_code(s) for s in result]}')
        return result
    
    def prepare(self, context: Context, date: str):
        self.trading_signal = False if context.current_dt.month in [1, 4] else True
        self.yesterday_HL_list = []
        self.hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())
    
    def sell(self, context: Context, date: str):
        print("-" * 45 + f"{str(context.current_dt.date())}" + "-" * 45)
        self.target_list = []
        
        if self.DBL_control:
            if len(self.dbl) < 10:
                for i in range(9, -1, -1):
                    self.check_dbl(context, date, end_days=0 - i)
        
        if self.DBL_control and 1 in self.dbl[-self.check_dbl_days:]:
            print(f"近{self.check_dbl_days}日检测到大盘顶背离，暂停调仓以控制风险")
            return
        
        if self.enable_market_defense and self.market_defense:
            defense_triggered = self.market_defense.check_defense_trigger(date)
            if defense_triggered:
                print("⚠️⚠️⚠️ 成交额宽度防御触发，清仓小市值持仓")
                subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
                for stock in list(subportfolio.positions.keys()):
                    if stock != self.xsz_buy_etf:
                        self.order_target_value(stock, 0, context, date)
                return
        
        month = context.current_dt.month
        if month in [1, 4]:
            self.trading_signal = False
        if not self.trading_signal:
            return
        
        if self.enable_dynamic_stock_num:
            ma_para = 10
            index_df = self.data_manager.get_stock_data('399101', end_date=date, days=ma_para * 2)
            if index_df is not None and len(index_df) >= ma_para:
                index_df['ma'] = index_df['close'].rolling(window=ma_para).mean()
                last_row = index_df.iloc[-1]
                diff = last_row['close'] - last_row['ma']
                self.xsz_stock_num = 3 if diff >= 500 else \
                    3 if 200 <= diff < 500 else \
                    4 if -200 <= diff < 200 else \
                    5 if -500 <= diff < -200 else 6
        
        version_map = {
            "v1": self.get_stock_list_v1,
            "v2": self.get_stock_list_v2,
            "v3": self.get_stock_list_v3,
        }
        self.target_list = version_map[self.xsz_version](context, date)[:self.xsz_stock_num]
        print(f'小市值 {self.xsz_version} 目标持股数: {self.xsz_stock_num} 目标持仓: {self.target_list}')
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        sell_list = [s for s in self.hold_list if s not in self.target_list and s not in self.yesterday_HL_list]
        
        for stock in sell_list:
            self.order_target_value(stock, 0, context, date)
    
    def buy(self, context: Context, date: str):
        if not self.trading_signal:
            subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
            if self.xsz_buy_etf not in subportfolio.positions:
                print("小市值清仓时期, 买入ETF")
                self.order_target_value(self.xsz_buy_etf, subportfolio.cash, context, date)
            return
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        current_value = sum(pos.value for pos in subportfolio.positions.values())
        available_cash = max(0, subportfolio.cash)
        
        buy_list = [s for s in self.target_list if s not in self.hold_list]
        if buy_list and available_cash > 0:
            cash_per_stock = available_cash / len(buy_list)
            for stock in buy_list:
                self.order_target_value(stock, cash_per_stock, context, date)
    
    def stop_loss(self, context: Context, date: str):
        if not self.run_stoploss:
            return
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        if self.stoploss_strategy in [1, 3]:
            for code, pos in list(subportfolio.positions.items()):
                price = pos.price
                avg_cost = pos.avg_cost
                
                if price >= avg_cost * 2:
                    print(f"🤑🤑🤑 收益100%止盈,卖出 {self.format_stock_code(code)}")
                    self.order_target_value(code, 0, context, date)
                elif price < avg_cost * (1 - self.stoploss_limit):
                    print(f"🤬🤬🤬 收益止损,卖出 {self.format_stock_code(code)}")
                    self.order_target_value(code, 0, context, date)
    
    def check_dbl(self, context: Context, date: str, market_index: str = '399101', end_days: int = 0):
        try:
            data = self.data_manager.get_stock_data(market_index, end_date=date, days=250)
            if data is None or len(data) < 200:
                return
            
            close = data['close']
            fast, slow, sign = 12, 26, 9
            
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            dif = ema_fast - ema_slow
            dea = dif.ewm(span=sign, adjust=False).mean()
            macd = (dif - dea) * 2
            
            df = pd.DataFrame({
                'close': close,
                'dif': dif,
                'dea': dea,
                'macd': macd
            })
            
            mask = (df['macd'] < 0) & (df['macd'].shift(1) >= 0)
            if mask.sum() < 2:
                self.dbl.append(0)
                return
            
            key2, key1 = mask[mask].index[-2], mask[mask].index[-1]
            
            price_cond = df.close[key2] < df.close[key1]
            dif_cond = df.dif[key2] > df.dif[key1] > 0
            macd_cond = df.macd.iloc[-2] > 0 > df.macd.iloc[-1]
            
            if len(df['dif']) > 20:
                recent_avg = df['dif'].iloc[-10:].mean()
                prev_avg = df['dif'].iloc[-20:-10].mean()
                trend_cond = recent_avg < prev_avg
            else:
                trend_cond = False
            
            if price_cond and dif_cond and macd_cond and trend_cond:
                self.dbl.append(1)
                print(f"⚠️⚠️⚠️ 检测到{market_index}顶背离信号")
            else:
                self.dbl.append(0)
        except Exception as e:
            self.dbl.append(0)
    
    def check_limit_up(self, context: Context, date: str):
        pass
    
    def close_account(self, context: Context, date: str):
        if not self.trading_signal:
            subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
            for stock in list(subportfolio.positions.keys()):
                if stock != self.xsz_buy_etf:
                    print(f"🤕🤕🤕 进入清仓期间 卖出 {self.format_stock_code(stock)}")
                    self.order_target_value(stock, 0, context, date)


class ETFReboundStrategy:
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.data_manager = data_manager
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None
        self.trade_records = []
        
        self.limit_days = 2
        self.n_days = 5
        self.buy_list = []
        self.etf_pool_2 = ['159536', '159629', '159922', '159919', '159783']
    
    def initialize(self, context: Context):
        self.limit_days = 2
        self.n_days = 5
        self.buy_list = []
    
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
            pos.init_time = date
            
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
            
            print(f"🚚🚚🚚 {code} 买价{current_price:<7.2f} 买量{amount:<7} 价值{amount * current_price:.2f}")
            return {'code': code, 'action': 'buy', 'amount': amount, 'price': current_price}
        
        elif value < current_value:
            if code not in subportfolio.positions:
                return None
            
            pos = subportfolio.positions[code]
            sell_value = current_value - value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                amount = pos.total_amount
            
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
            
            pnl = (current_price - pos.avg_cost) * amount
            pnl_pct = (current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '卖出',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission + stamp_tax,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            print(f"🚛🚛🚛 {code} 卖价{current_price:<7.2f} 成本{pos.avg_cost:<7.2f} 卖量{amount:<7} 盈亏{pnl:.2f}({pnl_pct:.2f}%)")
            
            if pos.total_amount <= 0:
                del subportfolio.positions[code]
            
            return {'code': code, 'action': 'sell', 'amount': amount, 'price': current_price}
        
        return None
    
    def sell(self, context: Context, date: str):
        cur_date = str(context.current_dt.date())
        if cur_date <= "2023-10-01":
            return
        
        self.buy_list = []
        sell_list = []
        
        for etf in self.etf_pool_2:
            data = self.data_manager.get_etf_data(etf, end_date=date, days=5)
            if data is None or len(data) < 4:
                continue
            
            pre_high_max = data['high'].iloc[-4:-1].max()
            yestoday_close = data['close'].iloc[-1]
            
            today_open = data['open'].iloc[-1]
            today_close = data['close'].iloc[-1]
            
            if today_open / pre_high_max < 0.98 and today_close / today_open > 1.01:
                self.buy_list.append(etf)
            
            if today_close < yestoday_close:
                sell_list.append(etf)
        
        if self.buy_list:
            self.buy_list.sort(key=lambda x: self.etf_pool_2.index(x))
            selected_etf = self.buy_list[0]
            self.buy_list = [selected_etf]
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        for etf in list(subportfolio.positions.keys()):
            if etf in sell_list or etf not in self.buy_list:
                self.order_target_value(etf, 0, context, date)
        
        if not self.buy_list:
            print(f"策略2今日无反弹可购买选项")
    
    def buy(self, context: Context, date: str):
        cur_date = str(context.current_dt.date())
        if cur_date <= "2023-10-01":
            return
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        buy_list = [s for s in self.buy_list if s not in subportfolio.positions]
        if buy_list:
            for etf in buy_list:
                print(f"符合策略2买入条件：{etf}")
                self.order_target_value(etf, subportfolio.cash, context, date)


class ETFRotationStrategy:
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.data_manager = data_manager
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None
        self.trade_records = []
        
        self.etf_pool_3 = [
            "510180", "513030", "513100", "513520",
            "510410", "518880", "501018", "159985", "511090",
            "159915", "588120", "512480", "159851", "513020", "159637",
            "513630", "510050"
        ]
        self.select_etf = None
        self.buy_etf = None
        self.m_days = 25
        self.m_score = 5
        self.enable_stop_loss_by_cur_day = True
        self.stoploss_limit_by_cur_day = -0.03
    
    def initialize(self, context: Context):
        self.select_etf = None
        self.buy_etf = None
    
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
            pos.init_time = date
            
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
            
            print(f"🚚🚚🚚 {code} 买价{current_price:<7.2f} 买量{amount:<7} 价值{amount * current_price:.2f}")
            return {'code': code, 'action': 'buy', 'amount': amount, 'price': current_price}
        
        elif value < current_value:
            if code not in subportfolio.positions:
                return None
            
            pos = subportfolio.positions[code]
            sell_value = current_value - value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                amount = pos.total_amount
            
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
            
            pnl = (current_price - pos.avg_cost) * amount
            pnl_pct = (current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '卖出',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission + stamp_tax,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            print(f"🚛🚛🚛 {code} 卖价{current_price:<7.2f} 成本{pos.avg_cost:<7.2f} 卖量{amount:<7} 盈亏{pnl:.2f}({pnl_pct:.2f}%)")
            
            if pos.total_amount <= 0:
                del subportfolio.positions[code]
            
            return {'code': code, 'action': 'sell', 'amount': amount, 'price': current_price}
        
        return None
    
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
    
    def _get_rsrs_slope(self, etf: str, date: str, days: int = 18) -> Optional[float]:
        try:
            data = self.data_manager.get_etf_data(etf, end_date=date, days=days)
            if data is None or len(data) < days:
                return None
            slope = np.polyfit(data['low'].values, data['high'].values, 1)[0]
            return slope
        except Exception as e:
            print(f"计算{etf} RSRS斜率失败: {e}")
            return None
    
    def _get_rsrs_beta(self, etf: str, date: str, lookback_days: int = 250, window: int = 20) -> Optional[float]:
        try:
            data = self.data_manager.get_etf_data(etf, end_date=date, days=lookback_days)
            if data is None or len(data) < lookback_days:
                return None
            
            slope_list = []
            for i in range(len(data) - window + 1):
                window_data = data.iloc[i:i + window]
                low_values = window_data['low'].values
                high_values = window_data['high'].values
                
                if len(low_values) < window or len(high_values) < window:
                    continue
                if np.any(np.isnan(low_values)) or np.any(np.isnan(high_values)):
                    continue
                if np.any(np.isinf(low_values)) or np.any(np.isinf(high_values)):
                    continue
                if np.std(low_values) == 0 or np.std(high_values) == 0:
                    continue
                
                slope = np.polyfit(low_values, high_values, 1)[0]
                slope_list.append(slope)
            
            if len(slope_list) < 2:
                return None
            
            mean_slope = np.mean(slope_list)
            std_slope = np.std(slope_list)
            beta = mean_slope - 2 * std_slope
            return beta
        except Exception as e:
            print(f"计算{etf} RSRS Beta失败: {e}")
            return None
    
    def _check_rsrs_with_strength(self, etf: str, date: str) -> Tuple[bool, float]:
        slope = self._get_rsrs_slope(etf, date)
        beta = self._get_rsrs_beta(etf, date)
        if slope is None or beta is None:
            return False, 0.0
        strength = (slope - beta) / abs(beta) if beta != 0 else 0
        return slope > beta, strength
    
    def _check_above_ma(self, etf: str, date: str, days: int = 20) -> bool:
        try:
            data = self.data_manager.get_etf_data(etf, end_date=date, days=days)
            if data is None or len(data) < days:
                return False
            current_price = data['close'].iloc[-1]
            return current_price >= data['close'].mean()
        except Exception as e:
            print(f"计算{etf} {days}日均线失败: {e}")
            return False
    
    def filter_rsrs(self, etf_list: List[str], date: str) -> List[str]:
        print("\n📊 ETF RSRS+均线过滤 " + "*" * 40)
        result = []
        
        for etf in etf_list:
            rsrs_pass, strength = self._check_rsrs_with_strength(etf, date)
            above_ma_5 = self._check_above_ma(etf, date, 5)
            above_ma_10 = self._check_above_ma(etf, date, 10)
            
            flag = "❌"
            reason = ""
            if rsrs_pass:
                if strength > 0.15:
                    flag = "✔️"
                    reason = "强度>0.15"
                    result.append(etf)
                elif strength > 0.03 and above_ma_5:
                    flag = "✔️"
                    reason = "强度>0.03且站上MA5"
                    result.append(etf)
                elif above_ma_10:
                    flag = "✔️"
                    reason = "站上MA10"
                    result.append(etf)
                else:
                    reason = "未满足条件"
            else:
                reason = "RSRS未通过"
            
            print(f"  {flag} {etf}: RSRS={rsrs_pass} 强度={strength:.2f} MA5={above_ma_5} MA10={above_ma_10} ({reason})")
        
        return result
    
    def get_rank(self, date: str) -> List[str]:
        print(f"\n🔄 ETF轮动策略 - 排名计算 [{date}]")
        print("📊 ETF 跌幅检测 " + "*" * 40)
        drop_filtered = []
        
        for etf in self.etf_pool_3:
            data = self.data_manager.get_etf_data(etf, end_date=date, days=self.m_days + 5)
            if data is None or len(data) < 4:
                print(f"  ⏭️  {etf}: 数据不足，跳过")
                continue
            
            prices = data['close'].values
            if min(prices[-1] / prices[-2], prices[-2] / prices[-3], prices[-3] / prices[-4]) < 0.95:
                print(f"  ❌ {etf} 近3日跌幅超过5%, 已排除")
                continue
            
            if self.enable_stop_loss_by_cur_day:
                today_open = data['open'].iloc[-1]
                current_price = data['close'].iloc[-1]
                ratio = (current_price - today_open) / today_open
                if ratio <= self.stoploss_limit_by_cur_day:
                    print(f"  ❌ {etf} 今日跌幅达到 {ratio * 100:.2f}%, 已排除")
                    continue
            
            print(f"  ✔️ {etf} 检测通过")
            drop_filtered.append(etf)
        
        print(f"\n📊 跌幅检测通过: {len(drop_filtered)}/{len(self.etf_pool_3)} 只")
        
        rsrs_filtered = self.filter_rsrs(drop_filtered, date)
        print(f"📊 RSRS+均线过滤后: {len(rsrs_filtered)} 只")
        
        print("\n📊 计算动量得分" + "*" * 40)
        score_list = []
        
        for etf in rsrs_filtered:
            score = self.calculate_momentum(etf, date, self.m_days)
            if score > 0.3 and score < self.m_score:
                score_list.append((etf, score))
                print(f"  ✔️ {etf} 动量得分: {score:.4f}")
            else:
                print(f"  ⏭️  {etf} 得分 {score:.4f} 不在范围(0.3, {self.m_score})")
        
        df = pd.DataFrame(score_list, columns=['etf', 'score'])
        df = df.sort_values('score', ascending=False)
        
        if len(df) > 0:
            print(f"\n✅ ETF排名结果: {df['etf'].tolist()}")
        else:
            print(f"\n⚠️ 无符合条件的ETF")
        
        return df['etf'].tolist()
    
    def sell(self, context: Context, date: str):
        rank_list = self.get_rank(date)
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        if not rank_list:
            for etf in list(subportfolio.positions.keys()):
                print("👿👿👿👿👿 ETF轮动没有一个能打的, 清仓当前持仓")
                self.order_target_value(etf, 0, context, date)
            return
        
        self.buy_etf = None
        select_etf = rank_list[0]
        
        current_etf = None
        
        for asset in list(subportfolio.positions.keys()):
            if asset in self.etf_pool_3:
                current_etf = asset
                break
        
        if current_etf and current_etf != select_etf:
            print(f"ETF轮动调仓: {current_etf} -> {select_etf}")
            self.order_target_value(current_etf, 0, context, date)
            self.buy_etf = select_etf
        elif not current_etf:
            self.buy_etf = select_etf
            print(f"ETF轮动建仓: {select_etf}")
    
    def buy(self, context: Context, date: str):
        if self.buy_etf:
            subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
            self.order_target_value(self.buy_etf, subportfolio.cash, context, date)
    
    def stop_loss(self, context: Context, date: str):
        if not self.enable_stop_loss_by_cur_day:
            return
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        for code, pos in list(subportfolio.positions.items()):
            data = self.data_manager.get_etf_data(code, end_date=date, days=1)
            if data is not None and len(data) > 0:
                today_open = data['open'].iloc[-1]
                current_price = data['close'].iloc[-1]
                ratio = (current_price - today_open) / today_open
                
                if ratio <= self.stoploss_limit_by_cur_day:
                    print(f"{code} 距离开盘跌幅 {ratio * 100:.2f}% 清仓处理")
                    self.order_target_value(code, 0, context, date)


class WhiteHorseStrategy:
    def __init__(self, subportfolio_index: int, name: str, data_manager: DataManager = None):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.data_manager = data_manager
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None
        self.trade_records = []
        
        self.check_out_lists = []
        self.market_temperature = "warm"
        self.stock_num_2 = 5
        self.roe = 10
        self.roa = 6
    
    def initialize(self, context: Context):
        self.check_out_lists = []
        self.market_temperature = "warm"
    
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
            pos.init_time = date
            
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
            
            print(f"🚚🚚🚚 {code} 买价{current_price:<7.2f} 买量{amount:<7} 价值{amount * current_price:.2f}")
            return {'code': code, 'action': 'buy', 'amount': amount, 'price': current_price}
        
        elif value < current_value:
            if code not in subportfolio.positions:
                return None
            
            pos = subportfolio.positions[code]
            sell_value = current_value - value
            amount = int(sell_value / current_price / 100) * 100
            
            if amount <= 0:
                amount = pos.total_amount
            
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
            
            pnl = (current_price - pos.avg_cost) * amount
            pnl_pct = (current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
            
            self.trade_records.append({
                'date': date,
                'strategy': self.name,
                'code': code,
                'action': '卖出',
                'price': current_price,
                'amount': amount,
                'value': amount * current_price,
                'commission': commission + stamp_tax,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            print(f"🚛🚛🚛 {code} 卖价{current_price:<7.2f} 成本{pos.avg_cost:<7.2f} 卖量{amount:<7} 盈亏{pnl:.2f}({pnl_pct:.2f}%)")
            
            if pos.total_amount <= 0:
                del subportfolio.positions[code]
            
            return {'code': code, 'action': 'sell', 'amount': amount, 'price': current_price}
        
        return None
    
    def cal_market_temperature(self, context: Context, date: str):
        data = self.data_manager.get_stock_data('000300', end_date=date, days=250)
        if data is None or len(data) < 220:
            self.market_temperature = "warm"
            return
        
        close = data['close'].values
        market_height = (np.mean(close[-5:]) - np.min(close)) / (np.max(close) - np.min(close))
        
        if market_height < 0.20:
            self.market_temperature = "cold"
        elif close[-1] == np.min(close):
            self.market_temperature = "cold"
        elif market_height > 0.90:
            self.market_temperature = "hot"
        elif close[-1] == np.max(close):
            self.market_temperature = "hot"
        else:
            self.market_temperature = "warm"
    
    def get_stock_list(self, context: Context, date: str) -> List[str]:
        all_stocks = self.data_manager.get_index_stocks('000300', date)
        
        filtered_stocks = []
        for stock in all_stocks:
            if self.data_manager.is_st_stock(stock, date):
                continue
            if self.data_manager.is_paused(stock, date):
                continue
            
            stock_clean = stock.split('.')[0] if '.' in stock else stock
            if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
                continue
            
            price = self.data_manager.get_current_price(stock, date)
            if price and price <= 100:
                filtered_stocks.append(stock)
        
        if len(filtered_stocks) == 0:
            return []
        
        financial_df = self.data_manager.get_financial_data(filtered_stocks)
        if financial_df.empty:
            return []
        
        if self.market_temperature == "cold":
            financial_df = financial_df[
                (financial_df['pb_ratio'] > 0) & 
                (financial_df['pb_ratio'] < 1) &
                (financial_df['roe'] > 0)
            ]
        elif self.market_temperature == "warm":
            financial_df = financial_df[
                (financial_df['pb_ratio'] > 0) & 
                (financial_df['pb_ratio'] < 1) &
                (financial_df['roe'] > 0)
            ]
        else:
            financial_df = financial_df[
                (financial_df['pb_ratio'] > 3) &
                (financial_df['roe'] > 0)
            ]
        
        if financial_df.empty:
            return []
        
        financial_df['score'] = financial_df['roe'] * self.roe + financial_df.get('roa', 0) * self.roa
        financial_df = financial_df.sort_values('score', ascending=False)
        
        return financial_df.head(self.stock_num_2)['code'].tolist()
    
    def adjust_position(self, context: Context, date: str):
        self.cal_market_temperature(context, date)
        target_list = self.get_stock_list(context, date)
        
        print(f"白马目标调仓: {[s for s in target_list]}")
        print(f"今日市场温度: {self.market_temperature}")
        
        subportfolio = context.portfolio.subportfolios[self.subportfolio_index]
        
        for stock in list(subportfolio.positions.keys()):
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


class ThreeHorseCarriageBacktest:
    def __init__(self, start_date: str = '2022-01-01', end_date: str = None, 
                 initial_cash: float = 1000000.0):
        self.context = Context()
        self.g = GlobalParams()
        self.data_manager = DataManager()
        
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.datetime.now().strftime('%Y-%m-%d')
        self.initial_cash = initial_cash
        
        self.trade_days: List[str] = []
        self.daily_values: List[Dict] = []
        self.trade_records: List[Dict] = []
        
        self.portfolio_value_proportion = [0.5, 0, 0.5, 0]
        
        self.strategies = []
    
    def initialize(self):
        print("\n" + "=" * 60)
        print("🚀 初始化三驾马车回测框架")
        print("=" * 60)
        
        print("\n📅 正在获取交易日历...")
        self.trade_days = self.data_manager.get_trade_days(self.start_date, self.end_date)
        print(f"✅ 获取到 {len(self.trade_days)} 个交易日")
        
        self.context.portfolio = Portfolio(self.initial_cash)
        
        strategy_configs = [
            {"name": "小市值", "class": SmallCapStrategy, "pct": self.portfolio_value_proportion[0]},
            {"name": "ETF反弹", "class": ETFReboundStrategy, "pct": self.portfolio_value_proportion[1]},
            {"name": "ETF轮动", "class": ETFRotationStrategy, "pct": self.portfolio_value_proportion[2]},
            {"name": "白马攻防", "class": WhiteHorseStrategy, "pct": self.portfolio_value_proportion[3]},
        ]
        
        print("\n📊 初始化策略配置:")
        self.strategies = []
        subportfolio_idx = 0
        for i, config in enumerate(strategy_configs):
            if config["pct"] == 0:
                print(f"  ⏭️  {config['name']}: 跳过 (配置比例为0)")
                continue
            
            subportfolio_cash = self.initial_cash * config["pct"]
            subportfolio = SubPortfolio(subportfolio_cash)
            self.context.portfolio.subportfolios.append(subportfolio)
            
            strategy = config["class"](subportfolio_idx, config["name"], self.data_manager)
            strategy.initialize(self.context)
            self.strategies.append(strategy)
            
            print(f"  ✅ {config['name']}: 资金 {subportfolio_cash:,.2f} ({config['pct']*100:.0f}%)")
            subportfolio_idx += 1
        
        print(f"\n💰 总初始资金: {self.initial_cash:,.2f}")
        print(f"📈 活跃策略数: {len(self.strategies)}")
    
    def preload_data(self, preload_stocks: int = 200):
        print("\n" + "=" * 60)
        print("预加载数据...")
        print("=" * 60)
        
        all_stocks = self.data_manager.get_all_stocks()
        print(f"📊 获取到 {len(all_stocks)} 只股票")
        
        stocks_to_preload = all_stocks[:preload_stocks]
        end_date = self.end_date
        
        def preload_stock_data(stock: str) -> bool:
            try:
                self.data_manager.get_stock_data(stock, end_date=end_date, days=250)
                return True
            except Exception:
                return False
        
        print(f"📥 预加载前 {preload_stocks} 只股票数据 (约需1-2分钟)...")
        success_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.data_manager.max_workers) as executor:
            futures = {executor.submit(preload_stock_data, stock): stock for stock in stocks_to_preload}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="预加载股票数据", unit="只",
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'):
                try:
                    if future.result():
                        success_count += 1
                except Exception:
                    continue
        
        print(f"✅ 预加载完成: {success_count}/{preload_stocks} 只股票")
        
        print("\n📥 预加载ETF数据...")
        etf_pool = ['518880', '513100', '159915', '159628', '159536', '159985', '512800', '510180', '513030', '513520']
        etf_success = 0
        for etf in tqdm(etf_pool, desc="预加载ETF数据", unit="只",
                       bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
            try:
                self.data_manager.get_etf_data(etf, end_date=end_date, days=100)
                etf_success += 1
            except Exception:
                continue
        print(f"✅ ETF数据预加载完成: {etf_success}/{len(etf_pool)} 只")
        print("\n" + "=" * 60)
        print("数据预加载全部完成，准备开始回测...")
        print("=" * 60)
    
    def run_backtest(self, preload: bool = True):
        self.initialize()
        
        if preload:
            self.preload_data(preload_stocks=200)
        
        print("\n" + "=" * 60)
        print("开始运行回测...")
        print(f"回测区间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print("=" * 60)
        
        total_days = len(self.trade_days)
        last_print_day = 0
        
        for i, date in enumerate(tqdm(self.trade_days, desc="回测进度", unit="天", 
                                       bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')):
            self.context.current_dt = pd.to_datetime(date)
            self.context.previous_date = self.trade_days[i-1] if i > 0 else date
            
            if i % 20 == 0 or i == total_days - 1:
                progress_pct = (i + 1) / total_days * 100
                current_value = self.context.portfolio.total_value
                print(f"\n📅 进度: {i+1}/{total_days} ({progress_pct:.1f}%) | 日期: {date} | 总资产: {current_value:,.2f}")
            
            for strategy in self.strategies:
                if hasattr(strategy, 'prepare'):
                    try:
                        strategy.prepare(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] prepare 错误: {e}")
            
            if i % 5 == 0:
                print(f"\n🔄 [{date}] 执行调仓检查...")
                for strategy in self.strategies:
                    if hasattr(strategy, 'sell'):
                        try:
                            strategy.sell(self.context, date)
                        except Exception as e:
                            print(f"\n[{strategy.name}] sell 错误: {e}")
            
            for strategy in self.strategies:
                if hasattr(strategy, 'buy'):
                    try:
                        strategy.buy(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] buy 错误: {e}")
            
            for strategy in self.strategies:
                if hasattr(strategy, 'stop_loss'):
                    try:
                        strategy.stop_loss(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] stop_loss 错误: {e}")
            
            for strategy in self.strategies:
                if hasattr(strategy, 'adjust_position'):
                    try:
                        strategy.adjust_position(self.context, date)
                    except Exception as e:
                        print(f"\n[{strategy.name}] adjust_position 错误: {e}")
            
            for strategy in self.strategies:
                subportfolio = self.context.portfolio.subportfolios[strategy.subportfolio_index]
                prices = {}
                for code in list(subportfolio.positions.keys()):
                    price = self.data_manager.get_current_price(code, date)
                    if price:
                        prices[code] = price
                subportfolio.update_positions_value(prices)
            
            for strategy in self.strategies:
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
        
        print("\n" + "=" * 60)
        print("回测循环完成，正在生成报告...")
        print("=" * 60)
        self.print_results()
        self.save_results()
    
    def print_results(self):
        print("\n" + "=" * 60)
        print("📊 回测结果汇总")
        print("=" * 60)
        
        if len(self.daily_values) == 0:
            print("❌ 无回测数据")
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
        
        print(f"\n📈 收益指标:")
        print(f"  💰 初始资金: {start_value:,.2f}")
        print(f"  💰 最终资金: {end_value:,.2f}")
        print(f"  📊 总收益率: {total_return:.2f}%")
        print(f"  📊 年化收益率: {annual_return * 100:.2f}%")
        
        print(f"\n📉 风险指标:")
        print(f"  📊 年化波动率: {annual_volatility * 100:.2f}%")
        print(f"  📊 夏普比率: {sharpe_ratio:.2f}")
        print(f"  📊 最大回撤: {max_drawdown * 100:.2f}%")
        
        print(f"\n🎯 各策略表现:")
        for strategy in self.strategies:
            if strategy.starting_cash and strategy.starting_cash > 0:
                final_value = self.context.portfolio.subportfolios[strategy.subportfolio_index].total_value
                returns = (final_value / strategy.starting_cash - 1) * 100
                status = "✅" if returns >= 0 else "❌"
                print(f"  {status} [{strategy.name}]: 收益率 {returns:.2f}% (初始: {strategy.starting_cash:,.2f} -> 最终: {final_value:,.2f})")
    
    def save_results(self):
        print("\n" + "=" * 60)
        print("💾 保存回测结果...")
        print("=" * 60)
        
        if len(self.daily_values) > 0:
            df = pd.DataFrame(self.daily_values)
            output_path = os.path.join(os.path.dirname(__file__), 'backtest_daily_values.csv')
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"✅ 每日净值已保存至: {output_path}")
        
        all_trades = []
        for strategy in self.strategies:
            if hasattr(strategy, 'trade_records'):
                for trade in strategy.trade_records:
                    trade_copy = trade.copy()
                    trade_copy['strategy'] = strategy.name
                    all_trades.append(trade_copy)
        
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            trades_path = os.path.join(os.path.dirname(__file__), 'trade_records.csv')
            trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
            print(f"✅ 交易记录已保存至: {trades_path} (共 {len(all_trades)} 条)")
        
        strategy_values = {}
        for strategy in self.strategies:
            if hasattr(strategy, 'portfolio_value') and len(strategy.portfolio_value) > 0:
                strategy_values[strategy.name] = strategy.portfolio_value
        
        if MultiStrategyPDFReport is not None:
            pdf_path = os.path.join(os.path.dirname(__file__), 'backtest_report.pdf')
            print("📄 正在生成PDF报告...")
            try:
                strategy_configs = [
                    {"name": s.name, "pct": self.portfolio_value_proportion[i] if i < len(self.portfolio_value_proportion) else 0}
                    for i, s in enumerate(self.strategies)
                ]
                pdf_generator = MultiStrategyPDFReport(
                    strategy_name='三驾马车策略',
                    daily_values=self.daily_values,
                    strategy_values=strategy_values,
                    strategy_configs=strategy_configs,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    initial_cash=self.initial_cash
                )
                pdf_generator.generate_pdf_report(pdf_path)
                print(f"✅ PDF报告已保存至: {pdf_path}")
            except Exception as e:
                print(f"❌ 生成PDF报告失败: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 回测完成！")
        print("=" * 60)


def main():
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 最近30天
    
    backtest = ThreeHorseCarriageBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_cash=1000000.0
    )
    
    backtest.run_backtest()


if __name__ == '__main__':
    main()
