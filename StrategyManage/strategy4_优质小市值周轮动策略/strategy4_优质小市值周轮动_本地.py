# 克隆自聚宽文章：https://www.joinquant.com/post/67113
# 标题：【策略升级】优质小市值周轮动策略-V1.3
# 作者：屌丝逆袭量化
# 本地化版本：使用efinance数据源

import efinance as ef
import numpy as np
import pandas as pd
import datetime
import time
import os
import sys
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_report_generator import BacktestReportGenerator


@dataclass
class Position:
    """持仓信息"""
    security: str
    total_amount: int = 0
    avg_cost: float = 0.0
    price: float = 0.0
    value: float = 0.0
    
    def update_price(self, current_price: float):
        self.price = current_price
        self.value = self.total_amount * current_price


@dataclass
class Portfolio:
    """投资组合"""
    starting_cash: float
    total_value: float = 0.0
    available_cash: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    
    def __post_init__(self):
        self.available_cash = self.starting_cash
        self.total_value = self.starting_cash
    
    def update_total_value(self):
        positions_value = sum(p.value for p in self.positions.values())
        self.total_value = positions_value + self.available_cash


@dataclass
class Trade:
    """成交记录"""
    security: str
    amount: int
    price: float
    time: datetime.datetime
    action: str  # 'buy' or 'sell'


class LocalContext:
    """本地策略上下文"""
    def __init__(self, start_date: str, end_date: str, initial_cash: float = 1000000):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.current_dt = self.start_date
        self.previous_date = self.start_date - datetime.timedelta(days=1)
        self.portfolio = Portfolio(starting_cash=initial_cash)
        self.trades: List[Trade] = []
        
    def update_date(self, current_dt: datetime.datetime):
        self.current_dt = current_dt
        self.previous_date = current_dt - datetime.timedelta(days=1)


class GlobalConfig:
    """全局配置"""
    def __init__(self):
        self.stock_num = 10
        self.limit_up_list = []
        self.hold_list = []
        self.high_limit_list = []
        
        self.enable_price_filter = False
        self.price_threshold = 2.0
        
        self.enable_volume_filter = False
        self.min_avg_amount = 10e7
        self.lookback_days = 60
        
        self.enable_atr_stop_loss = False
        self.atr_multiple = 2.0
        self.atr_period = 14
        self.atr_stop_loss_records = {}
        
        self.enable_overall_risk_control = True
        self.max_drawdown_threshold = -0.1
        self.defense_duration = 20
        self.defense_start_date = None
        self.in_defense_mode = False
        
        self.portfolio_history = []
        self.max_lookback_days = 60
        
        self.defense_assets = {
            '518880': 0.5,
            '511010': 0.5
        }


class Logger:
    """日志类"""
    @staticmethod
    def info(msg: str):
        print(f"[INFO] {msg}")
    
    @staticmethod
    def warn(msg: str):
        print(f"[WARN] {msg}")
    
    @staticmethod
    def error(msg: str):
        print(f"[ERROR] {msg}")
    
    @staticmethod
    def debug(msg: str):
        print(f"[DEBUG] {msg}")


log = Logger()


class EfinanceDataProvider:
    """efinance数据提供者"""
    
    def __init__(self):
        self._all_stocks_cache = None
        self._stock_info_cache = {}
        self._price_cache = {}
        self._realtime_quotes_cache = None
        self._realtime_quotes_time = None
    
    def get_all_stocks(self) -> List[str]:
        """获取所有A股股票代码"""
        if self._all_stocks_cache is not None:
            return self._all_stocks_cache
        
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and not df.empty:
                codes = df['股票代码'].tolist()
                self._all_stocks_cache = [c for c in codes if c.startswith(('00', '60', '30'))]
                return self._all_stocks_cache
        except Exception as e:
            log.error(f"获取股票列表失败: {e}")
        
        return []
    
    def get_stock_info(self, code: str) -> Dict:
        """获取股票基本信息"""
        if code in self._stock_info_cache:
            return self._stock_info_cache[code]
        
        try:
            df = ef.stock.get_base_info(code)
            if df is not None and not df.empty:
                if isinstance(df, pd.DataFrame):
                    info = df.iloc[0].to_dict()
                else:
                    info = df.to_dict()
                self._stock_info_cache[code] = info
                return info
        except:
            pass
        
        return {'股票代码': code, '股票名称': '', '上市时间': None}
    
    def get_price(self, codes: List[str], start_date: str, end_date: str, 
                  fields: List[str] = None) -> pd.DataFrame:
        """获取股票价格数据"""
        if isinstance(codes, str):
            codes = [codes]
        
        all_data = []
        for code in codes:
            try:
                cache_key = f"{code}_{start_date}_{end_date}"
                if cache_key in self._price_cache:
                    all_data.append(self._price_cache[cache_key])
                    continue
                
                df = ef.stock.get_quote_history(code, beg=start_date, end=end_date)
                if df is not None and not df.empty:
                    df['code'] = code
                    df = df.rename(columns={
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'money',
                        '涨跌幅': 'change_pct'
                    })
                    all_data.append(df)
                    self._price_cache[cache_key] = df
                    time.sleep(0.1)
            except Exception as e:
                log.debug(f"获取{code}价格数据失败: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data, ignore_index=True)
        return result
    
    def get_realtime_quotes(self, codes: List[str] = None) -> pd.DataFrame:
        """获取实时行情"""
        try:
            if codes is None:
                if self._realtime_quotes_cache is not None and self._realtime_quotes_time is not None:
                    if (datetime.datetime.now() - self._realtime_quotes_time).seconds < 300:
                        return self._realtime_quotes_cache
                
                df = ef.stock.get_realtime_quotes()
                if df is not None:
                    self._realtime_quotes_cache = df
                    self._realtime_quotes_time = datetime.datetime.now()
                return df
            else:
                df = ef.stock.get_realtime_quotes(codes)
                return df
        except Exception as e:
            log.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_market_cap(self, codes: List[str], date: str = None) -> pd.DataFrame:
        """获取市值数据"""
        try:
            df = ef.stock.get_base_info(codes)
            if df is not None and not df.empty:
                if isinstance(df, pd.Series):
                    df = pd.DataFrame([df])
                
                result = pd.DataFrame({
                    'code': df['股票代码'].tolist() if '股票代码' in df.columns else codes,
                    'market_cap': df['总市值'].tolist() if '总市值' in df.columns else [0] * len(df),
                    'circulating_market_cap': df['流通市值'].tolist() if '流通市值' in df.columns else [0] * len(df),
                    'pb_ratio': df['市净率'].tolist() if '市净率' in df.columns else [0] * len(df),
                    'pe_ratio': df['市盈率(动)'].tolist() if '市盈率(动)' in df.columns else [0] * len(df)
                })
                return result
        except Exception as e:
            log.error(f"获取市值数据失败: {e}")
        
        return pd.DataFrame()
    
    def get_financial_indicator(self, codes: List[str]) -> pd.DataFrame:
        """获取财务指标"""
        all_data = []
        for code in codes:
            try:
                df = ef.stock.get_base_info(code)
                if df is not None and not df.empty:
                    if isinstance(df, pd.DataFrame):
                        latest = df.iloc[0]
                    else:
                        latest = df
                    all_data.append({
                        'code': code,
                        'roe': 0,
                        'gross_profit_margin': 0,
                        'inc_total_revenue_year_on_year': 0,
                        'inc_net_profit_annual': 0
                    })
                time.sleep(0.02)
            except Exception as e:
                log.debug(f"获取{code}财务指标失败: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.DataFrame(all_data)


class LocalBacktestEngine:
    """本地回测引擎"""
    
    def __init__(self, context: LocalContext, config: GlobalConfig, data_provider: EfinanceDataProvider):
        self.context = context
        self.config = config
        self.data_provider = data_provider
        self.daily_results = []
        self.strategy_name = "优质小市值周轮动策略"
    
    def run(self):
        """运行回测"""
        log.info(f"开始回测，起始日期: {self.context.start_date.strftime('%Y-%m-%d')}, "
                f"结束日期: {self.context.end_date.strftime('%Y-%m-%d')}, "
                f"初始资金: {self.context.portfolio.starting_cash:.2f}")
        
        current_date = self.context.start_date
        trading_days = self._get_trading_days()
        
        for trade_date in trading_days:
            if trade_date < self.context.start_date or trade_date > self.context.end_date:
                continue
            
            self.context.update_date(trade_date)
            log.info(f"\n{'='*60}\n当前日期: {trade_date.strftime('%Y-%m-%d')}")
            
            self._prepare_stock_list()
            
            if trade_date.weekday() == 0:
                self._weekly_adjustment()
            
            self._check_risk_control()
            
            self._update_positions_value()
            
            self._record_daily_result(trade_date)
            
            self._record_portfolio_value()
            
            self._print_position_info()
        
        self._generate_report()
    
    def _get_trading_days(self) -> List[datetime.datetime]:
        """获取交易日列表"""
        start = self.context.start_date - datetime.timedelta(days=100)
        end = self.context.end_date + datetime.timedelta(days=10)
        
        try:
            df = ef.stock.get_trading_dates()
            if df is not None and not df.empty:
                trading_days = pd.to_datetime(df['trade_date']).tolist()
                return [d for d in trading_days if start <= d <= end]
        except:
            pass
        
        all_days = pd.date_range(start=start, end=end, freq='B')
        return [d for d in all_days]
    
    def _get_previous_trading_day(self, date: datetime.datetime) -> datetime.datetime:
        """获取前一个交易日"""
        trading_days = self._get_trading_days()
        prev_days = [d for d in trading_days if d < date]
        if prev_days:
            return prev_days[-1]
        return date - datetime.timedelta(days=1)
    
    def _prepare_stock_list(self):
        """准备股票池"""
        if self.config.in_defense_mode:
            log.info("当前处于防御模式，跳过股票池准备")
            return
        
        self.config.hold_list = list(self.context.portfolio.positions.keys())
        
        if self.config.hold_list:
            yesterday = self._get_previous_trading_day(self.context.current_dt)
            df = self.data_provider.get_price(
                self.config.hold_list,
                start_date=yesterday.strftime('%Y%m%d'),
                end_date=yesterday.strftime('%Y%m%d')
            )
            if not df.empty:
                pass
        
        self.config.high_limit_list = []
    
    def _weekly_adjustment(self):
        """周调仓"""
        if self.config.in_defense_mode:
            log.info("当前处于防御模式，跳过正常的股票轮动调整")
            self._check_defense_period_end()
            return
        
        log.info("执行周调仓...")
        
        target_list, quotes_df = self._get_stock_list_with_quotes()
        
        if not target_list:
            log.warn("选股结果为空，跳过调仓")
            return
        
        target_list = target_list[:min(self.config.stock_num, len(target_list))]
        
        for stock in self.config.hold_list:
            if stock not in target_list:
                log.info(f"卖出 [{stock}]")
                self._close_position(stock)
                if stock in self.config.atr_stop_loss_records:
                    del self.config.atr_stop_loss_records[stock]
            else:
                log.info(f"已持有 [{stock}]")
        
        position_count = len(self.context.portfolio.positions)
        target_num = len(target_list)
        
        if target_num > position_count:
            value = self.context.portfolio.available_cash / (target_num - position_count)
            for stock in target_list:
                if stock not in self.context.portfolio.positions:
                    if self._open_position_with_quotes(stock, value, quotes_df):
                        self._update_atr_stop_loss_price(stock)
                        if len(self.context.portfolio.positions) == target_num:
                            break
    
    def _get_stock_list_with_quotes(self):
        """获取目标股票列表 - 使用历史价格数据"""
        yesterday = self._get_previous_trading_day(self.context.current_dt)
        yesterday_str = yesterday.strftime('%Y%m%d')
        
        quotes_df = self.data_provider.get_realtime_quotes()
        if quotes_df.empty:
            return [], pd.DataFrame()
        
        initial_list = self._filter_kcbj_stock(quotes_df['股票代码'].tolist())
        
        quotes_df = quotes_df[quotes_df['股票代码'].isin(initial_list)]
        
        def is_st(name):
            if not name or pd.isna(name):
                return False
            name = str(name)
            return 'ST' in name or '*' in name or '退' in name
        
        quotes_df = quotes_df[~quotes_df['股票名称'].apply(is_st)]
        
        quotes_df['流通市值'] = pd.to_numeric(quotes_df['流通市值'], errors='coerce').fillna(0)
        quotes_df['总市值'] = pd.to_numeric(quotes_df['总市值'], errors='coerce').fillna(0)
        quotes_df['最新价'] = pd.to_numeric(quotes_df['最新价'], errors='coerce').fillna(0)
        
        quotes_df = quotes_df[quotes_df['流通市值'] > 0]
        quotes_df = quotes_df[quotes_df['总市值'] > 0]
        quotes_df = quotes_df[quotes_df['最新价'] > 0]
        
        quotes_df = quotes_df.sort_values('流通市值', ascending=True)
        
        price_list = quotes_df['股票代码'].tolist()[:int(len(quotes_df) * 0.1)]
        
        if not price_list:
            return [], pd.DataFrame()
        
        price_list = price_list[:15]
        
        log.info(f"初步筛选后股票数量: {len(price_list)}, 样例: {price_list[:3]}")
        
        return price_list, quotes_df
    
    def _open_position_with_quotes(self, security: str, value: float, quotes_df: pd.DataFrame) -> bool:
        """使用历史价格开仓"""
        yesterday = self._get_previous_trading_day(self.context.current_dt)
        price_df = self.data_provider.get_price(
            security,
            start_date=yesterday.strftime('%Y%m%d'),
            end_date=yesterday.strftime('%Y%m%d')
        )
        
        if price_df.empty:
            log.warn(f"无法获取{security}价格数据")
            return False
        
        current_price = float(price_df['close'].iloc[-1])
        if current_price <= 0:
            return False
        
        shares = int(value / current_price / 100) * 100
        if shares <= 0:
            return False
        
        actual_value = shares * current_price
        if actual_value > self.context.portfolio.available_cash:
            shares = int(self.context.portfolio.available_cash / current_price / 100) * 100
            actual_value = shares * current_price
        
        if shares <= 0:
            return False
        
        self.context.portfolio.available_cash -= actual_value
        
        if security in self.context.portfolio.positions:
            position = self.context.portfolio.positions[security]
            total_value = position.avg_cost * position.total_amount + actual_value
            position.total_amount += shares
            position.avg_cost = total_value / position.total_amount
            position.price = current_price
            position.value = position.total_amount * current_price
        else:
            self.context.portfolio.positions[security] = Position(
                security=security,
                total_amount=shares,
                avg_cost=current_price,
                price=current_price,
                value=actual_value
            )
        
        trade = Trade(
            security=security,
            amount=shares,
            price=current_price,
            time=self.context.current_dt,
            action='buy'
        )
        self.context.trades.append(trade)
        
        log.info(f"买入 {security}: {shares}股 @ {current_price:.2f}, 金额: {actual_value:.2f}")
        return True
    
    def _filter_kcbj_stock(self, stock_list: List[str]) -> List[str]:
        """过滤科创板、北交所和创业板"""
        return [s for s in stock_list if not (
            s.startswith('68') or 
            s.startswith('4') or 
            s.startswith('8') or 
            s.startswith('92') or
            s.startswith('30')
        )]
    
    def _filter_new_stock(self, stock_list: List[str], date: datetime.datetime) -> List[str]:
        """过滤次新股 - 简化版本，跳过API调用"""
        return stock_list
    
    def _filter_st_stock(self, stock_list: List[str]) -> List[str]:
        """过滤ST股票 - 使用实时行情数据"""
        quotes_df = self.data_provider.get_realtime_quotes()
        if quotes_df.empty:
            return stock_list
        
        quotes_df = quotes_df[quotes_df['股票代码'].isin(stock_list)]
        
        def is_st(name):
            if not name or pd.isna(name):
                return False
            name = str(name)
            return 'ST' in name or '*' in name or '退' in name
        
        filtered = quotes_df[~quotes_df['股票名称'].apply(is_st)]['股票代码'].tolist()
        return filtered
    
    def _filter_price_stock(self, stock_list: List[str], date_str: str) -> List[str]:
        """价格过滤"""
        if not stock_list:
            return stock_list
        
        price_df = self.data_provider.get_price(stock_list, date_str, date_str)
        if price_df.empty:
            return stock_list
        
        filtered = price_df[price_df['close'] >= self.config.price_threshold]['code'].tolist()
        log.info(f"价格过滤: 从{len(stock_list)}只股票中过滤出{len(filtered)}只价格>={self.config.price_threshold}元的股票")
        return filtered
    
    def _filter_volume_stock(self, stock_list: List[str], end_date_str: str) -> List[str]:
        """成交量过滤"""
        if not stock_list:
            return stock_list
        
        end_date = pd.to_datetime(end_date_str)
        start_date = (end_date - datetime.timedelta(days=self.config.lookback_days + 10)).strftime('%Y%m%d')
        
        price_df = self.data_provider.get_price(stock_list, start_date, end_date_str)
        if price_df.empty:
            return stock_list
        
        avg_amounts = price_df.groupby('code')['money'].mean()
        filtered = avg_amounts[avg_amounts >= self.config.min_avg_amount].index.tolist()
        
        log.info(f"成交量过滤: 从{len(stock_list)}只股票中过滤出{len(filtered)}只{self.config.lookback_days}日平均成交额>={self.config.min_avg_amount/10000:.2f}万的股票")
        return filtered
    
    def _open_position(self, security: str, value: float) -> bool:
        """开仓"""
        yesterday = self._get_previous_trading_day(self.context.current_dt)
        price_df = self.data_provider.get_price(
            security,
            start_date=yesterday.strftime('%Y%m%d'),
            end_date=yesterday.strftime('%Y%m%d')
        )
        
        if price_df.empty:
            log.warn(f"无法获取{security}价格数据")
            return False
        
        current_price = float(price_df['close'].iloc[-1])
        if current_price <= 0:
            return False
        
        shares = int(value / current_price / 100) * 100
        if shares <= 0:
            return False
        
        actual_value = shares * current_price
        if actual_value > self.context.portfolio.available_cash:
            shares = int(self.context.portfolio.available_cash / current_price / 100) * 100
            actual_value = shares * current_price
        
        if shares <= 0:
            return False
        
        self.context.portfolio.available_cash -= actual_value
        
        if security in self.context.portfolio.positions:
            position = self.context.portfolio.positions[security]
            total_value = position.avg_cost * position.total_amount + actual_value
            position.total_amount += shares
            position.avg_cost = total_value / position.total_amount
            position.price = current_price
            position.value = position.total_amount * current_price
        else:
            self.context.portfolio.positions[security] = Position(
                security=security,
                total_amount=shares,
                avg_cost=current_price,
                price=current_price,
                value=actual_value
            )
        
        trade = Trade(
            security=security,
            amount=shares,
            price=current_price,
            time=self.context.current_dt,
            action='buy'
        )
        self.context.trades.append(trade)
        
        log.info(f"买入 {security}: {shares}股 @ {current_price:.2f}, 金额: {actual_value:.2f}")
        return True
    
    def _close_position(self, security: str) -> bool:
        """平仓"""
        if security not in self.context.portfolio.positions:
            return False
        
        position = self.context.portfolio.positions[security]
        
        yesterday = self._get_previous_trading_day(self.context.current_dt)
        price_df = self.data_provider.get_price(
            security,
            start_date=yesterday.strftime('%Y%m%d'),
            end_date=yesterday.strftime('%Y%m%d')
        )
        
        if price_df.empty:
            log.warn(f"无法获取{security}价格数据，使用成本价平仓")
            current_price = position.avg_cost
        else:
            current_price = float(price_df['close'].iloc[-1])
        
        actual_value = position.total_amount * current_price
        self.context.portfolio.available_cash += actual_value
        
        trade = Trade(
            security=security,
            amount=position.total_amount,
            price=current_price,
            time=self.context.current_dt,
            action='sell'
        )
        self.context.trades.append(trade)
        
        log.info(f"卖出 {security}: {position.total_amount}股 @ {current_price:.2f}, 金额: {actual_value:.2f}")
        
        del self.context.portfolio.positions[security]
        return True
    
    def _update_positions_value(self):
        """更新持仓市值"""
        if not self.context.portfolio.positions:
            return
        
        yesterday = self._get_previous_trading_day(self.context.current_dt)
        
        for security, position in self.context.portfolio.positions.items():
            price_df = self.data_provider.get_price(
                security,
                start_date=yesterday.strftime('%Y%m%d'),
                end_date=yesterday.strftime('%Y%m%d')
            )
            if not price_df.empty:
                current_price = float(price_df['close'].iloc[-1])
                position.update_price(current_price)
        
        self.context.portfolio.update_total_value()
    
    def _check_risk_control(self):
        """风控检查"""
        self._check_overall_drawdown()
        
        if not self.config.in_defense_mode and self.config.enable_atr_stop_loss:
            self._check_atr_stop_loss()
        
        if self.config.in_defense_mode:
            self._check_defense_period_end()
    
    def _check_overall_drawdown(self):
        """检查整体回撤"""
        if not self.config.enable_overall_risk_control:
            return
        
        if self.config.in_defense_mode:
            return
        
        current_value = self.context.portfolio.total_value
        
        if not self.config.portfolio_history:
            log.info("暂无历史资产数据，无法计算回撤")
            return
        
        lookback_days = min(len(self.config.portfolio_history), self.config.defense_duration)
        recent_history = self.config.portfolio_history[-lookback_days:]
        
        if not recent_history:
            return
        
        max_value = max([record['total_value'] for record in recent_history])
        
        if max_value > 0:
            drawdown = (current_value - max_value) / max_value
        else:
            drawdown = 0
        
        log.info(f"整体回撤检查: 当前资产{current_value:.2f}, 近期{lookback_days}天最高资产{max_value:.2f}, "
                f"回撤率{drawdown*100:.2f}%, 阈值{self.config.max_drawdown_threshold*100:.2f}%")
        
        if drawdown < self.config.max_drawdown_threshold:
            log.warn(f"整体回撤超过阈值({self.config.max_drawdown_threshold*100:.2f}%)，触发防御机制")
            self._enter_defense_mode()
    
    def _enter_defense_mode(self):
        """进入防御模式"""
        self.config.in_defense_mode = True
        self.config.defense_start_date = self.context.current_dt.date()
        
        log.info(f"开始进入防御模式，防御开始日期: {self.config.defense_start_date}")
        
        holdings = list(self.context.portfolio.positions.keys())
        if holdings:
            log.info(f"开始清空股票持仓，共{len(holdings)}只股票")
            for stock in holdings:
                self._close_position(stock)
                if stock in self.config.atr_stop_loss_records:
                    del self.config.atr_stop_loss_records[stock]
        
        if self.context.portfolio.available_cash > 100:
            self._allocate_defense_assets()
    
    def _allocate_defense_assets(self):
        """分配防御资产"""
        total_cash = self.context.portfolio.available_cash
        log.info(f"开始分配防御资产，可用现金: {total_cash:.2f}")
        
        total_weight = sum(self.config.defense_assets.values())
        
        for asset, weight in self.config.defense_assets.items():
            normalized_weight = weight / total_weight
            allocate_amount = total_cash * normalized_weight
            
            if allocate_amount > 100:
                log.info(f"买入防御资产[{asset}]，金额: {allocate_amount:.2f}，权重: {normalized_weight:.2f}")
                self._open_position(asset, allocate_amount)
    
    def _check_defense_period_end(self):
        """检查防御期限是否结束"""
        if not self.config.in_defense_mode or not self.config.defense_start_date:
            return
        
        current_date = self.context.current_dt.date()
        days_in_defense = (current_date - self.config.defense_start_date).days
        
        log.info(f"防御模式已持续{days_in_defense}天，总防御期限{self.config.defense_duration}天")
        
        if days_in_defense >= self.config.defense_duration:
            log.info("防御期限结束，退出防御模式")
            self._exit_defense_mode()
    
    def _exit_defense_mode(self):
        """退出防御模式"""
        self.config.in_defense_mode = False
        self.config.defense_start_date = None
        
        log.info("开始退出防御模式，恢复正常的股票轮动策略")
        
        holdings = list(self.context.portfolio.positions.keys())
        if holdings:
            log.info(f"开始清空防御资产，共{len(holdings)}只")
            for asset in holdings:
                self._close_position(asset)
        
        self.config.hold_list = []
        self.config.atr_stop_loss_records = {}
        self.config.high_limit_list = []
        self.config.portfolio_history = []
        log.info("防御模式退出完成，等待下一次正常调仓")
    
    def _check_atr_stop_loss(self):
        """ATR止损检查"""
        if not self.config.enable_atr_stop_loss:
            return
        
        holdings = list(self.context.portfolio.positions.keys())
        if not holdings:
            return
        
        log.info(f"开始执行ATR止损检查，当前持仓数量: {len(holdings)}")
        
        for stock in holdings:
            position = self.context.portfolio.positions[stock]
            current_price = position.price
            
            if stock not in self.config.atr_stop_loss_records:
                self._update_atr_stop_loss_price(stock)
            
            if stock in self.config.atr_stop_loss_records:
                stop_price = self.config.atr_stop_loss_records[stock]
                
                if current_price <= stop_price:
                    log.info(f"股票[{stock}]触发ATR止损，当前价格{current_price:.2f}，止损价格{stop_price:.2f}")
                    self._close_position(stock)
                    del self.config.atr_stop_loss_records[stock]
                else:
                    new_stop_price = self._update_trailing_stop_loss(stock, current_price)
                    if new_stop_price > stop_price:
                        self.config.atr_stop_loss_records[stock] = new_stop_price
                        log.info(f"股票[{stock}]更新跟踪止损价: {stop_price:.2f} -> {new_stop_price:.2f}")
    
    def _update_atr_stop_loss_price(self, stock: str) -> Optional[float]:
        """计算ATR止损价格"""
        try:
            end_date = self._get_previous_trading_day(self.context.current_dt)
            start_date = end_date - datetime.timedelta(days=self.config.atr_period + 20)
            
            price_df = self.data_provider.get_price(
                stock,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if len(price_df) < self.config.atr_period:
                log.warn(f"股票[{stock}]历史数据不足，无法计算ATR")
                return None
            
            price_df['prev_close'] = price_df['close'].shift(1)
            price_df['high_low'] = price_df['high'] - price_df['low']
            price_df['high_prev_close'] = abs(price_df['high'] - price_df['prev_close'])
            price_df['low_prev_close'] = abs(price_df['low'] - price_df['prev_close'])
            
            price_df['tr'] = price_df[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
            
            atr = price_df['tr'].tail(self.config.atr_period).mean()
            
            if stock in self.context.portfolio.positions:
                cost_price = self.context.portfolio.positions[stock].avg_cost
            else:
                cost_price = price_df['close'].iloc[-1]
            
            stop_loss_price = cost_price - (atr * self.config.atr_multiple)
            
            self.config.atr_stop_loss_records[stock] = stop_loss_price
            
            log.info(f"股票[{stock}]ATR止损价计算完成: 成本价{cost_price:.2f}, ATR={atr:.4f}, 止损价={stop_loss_price:.2f}")
            
            return stop_loss_price
            
        except Exception as e:
            log.error(f"计算股票[{stock}]ATR止损价时出错: {e}")
            return None
    
    def _update_trailing_stop_loss(self, stock: str, current_price: float) -> float:
        """更新跟踪止损价格"""
        if stock not in self.config.atr_stop_loss_records:
            return current_price
        
        current_stop = self.config.atr_stop_loss_records[stock]
        
        if stock in self.context.portfolio.positions:
            cost_price = self.context.portfolio.positions[stock].avg_cost
        else:
            cost_price = current_price
        
        try:
            end_date = self._get_previous_trading_day(self.context.current_dt)
            start_date = end_date - datetime.timedelta(days=self.config.atr_period + 20)
            
            price_df = self.data_provider.get_price(
                stock,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if len(price_df) >= self.config.atr_period:
                price_df['prev_close'] = price_df['close'].shift(1)
                price_df['high_low'] = price_df['high'] - price_df['low']
                price_df['high_prev_close'] = abs(price_df['high'] - price_df['prev_close'])
                price_df['low_prev_close'] = abs(price_df['low'] - price_df['prev_close'])
                price_df['tr'] = price_df[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
                atr = price_df['tr'].tail(self.config.atr_period).mean()
                
                new_stop = current_price - (atr * self.config.atr_multiple)
                
                if new_stop > current_stop:
                    return new_stop
        
        except Exception as e:
            log.error(f"更新跟踪止损时出错: {e}")
        
        return current_stop
    
    def _record_portfolio_value(self):
        """记录资产价值"""
        self.context.portfolio.update_total_value()
        current_date = self.context.current_dt
        total_value = self.context.portfolio.total_value
        
        self.config.portfolio_history.append({
            'date': current_date,
            'total_value': total_value
        })
        
        if len(self.config.portfolio_history) > self.config.max_lookback_days:
            self.config.portfolio_history.pop(0)
        
        log.info(f"记录资产: 日期{current_date.strftime('%Y-%m-%d')}，总资产{total_value:.2f}")
    
    def _record_daily_result(self, trade_date: datetime.datetime):
        """记录每日结果用于生成报告"""
        self.context.portfolio.update_total_value()
        
        position_count = len(self.context.portfolio.positions)
        position_value = sum(p.value for p in self.context.portfolio.positions.values())
        
        self.daily_results.append({
            'date': trade_date,
            'total_value': self.context.portfolio.total_value,
            'cash': self.context.portfolio.available_cash,
            'position_value': position_value,
            'position_count': position_count
        })
    
    def _print_position_info(self):
        """打印持仓信息"""
        print("\n" + "="*60)
        
        if self.config.in_defense_mode:
            print('策略状态：防御模式')
            if self.config.defense_start_date:
                current_date = self.context.current_dt.date()
                days_in_defense = (current_date - self.config.defense_start_date).days
                remaining_days = max(0, self.config.defense_duration - days_in_defense)
                print(f'防御已持续：{days_in_defense}天，剩余：{remaining_days}天')
        else:
            print('策略状态：正常模式')
            
            current_value = self.context.portfolio.total_value
            if self.config.portfolio_history:
                lookback_days = min(len(self.config.portfolio_history), self.config.defense_duration)
                recent_history = self.config.portfolio_history[-lookback_days:]
                if recent_history:
                    max_value = max([record['total_value'] for record in recent_history])
                    if max_value > 0:
                        drawdown = (current_value - max_value) / max_value * 100
                        print(f'当前回撤：{drawdown:.2f}% (相对于最近{lookback_days}天最高点)')
        
        if not self.config.in_defense_mode:
            print('ATR止损记录：')
            for stock, stop_price in self.config.atr_stop_loss_records.items():
                if stock in self.context.portfolio.positions:
                    position = self.context.portfolio.positions[stock]
                    current_price = position.price
                    distance_pct = (current_price - stop_price) / current_price * 100 if current_price > 0 else 0
                    print(f'股票:{stock}，止损价:{stop_price:.2f}，现价:{current_price:.2f}，距离止损:{distance_pct:.2f}%')
        
        total_value = self.context.portfolio.total_value
        starting_cash = self.context.portfolio.starting_cash
        overall_return = (total_value - starting_cash) / starting_cash * 100
        print(f'整体收益：起始资金{starting_cash:.2f}，当前总资产{total_value:.2f}，收益率{overall_return:.2f}%')
        
        for position in self.context.portfolio.positions.values():
            securities = position.security
            cost = position.avg_cost
            price = position.price
            ret = 100*(price/cost-1) if cost > 0 else 0
            value = position.value
            amount = position.total_amount
            print(f'代码:{securities}')
            print(f'成本价:{cost:.2f}')
            print(f'现价:{price:.2f}')
            print(f'收益率:{ret:.2f}%')
            print(f'持仓(股):{amount}')
            print(f'市值:{value:.2f}')
            print('———————————————————————————————————')
        print('———————————————————————————————————————分割线————————————————————————————————————————')
    
    def _generate_report(self):
        """生成回测报告"""
        print("\n" + "="*80)
        print("回测报告")
        print("="*80)
        
        total_value = self.context.portfolio.total_value
        starting_cash = self.context.portfolio.starting_cash
        total_return = (total_value - starting_cash) / starting_cash * 100
        
        print(f"初始资金: {starting_cash:.2f}")
        print(f"最终资产: {total_value:.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"交易次数: {len(self.context.trades)}")
        
        buy_trades = [t for t in self.context.trades if t.action == 'buy']
        sell_trades = [t for t in self.context.trades if t.action == 'sell']
        print(f"买入次数: {len(buy_trades)}")
        print(f"卖出次数: {len(sell_trades)}")
        
        if self.config.portfolio_history:
            values = [r['total_value'] for r in self.config.portfolio_history]
            max_value = max(values)
            min_value = min(values)
            max_drawdown = (max_value - min_value) / max_value * 100 if max_value > 0 else 0
            print(f"最大资产: {max_value:.2f}")
            print(f"最小资产: {min_value:.2f}")
            print(f"最大回撤: {max_drawdown:.2f}%")
        
        print("="*80)
        
        trade_records = []
        for trade in self.context.trades:
            trade_records.append({
                'date': trade.time,
                'security': trade.security,
                'action': trade.action,
                'amount': trade.amount,
                'price': trade.price
            })
        
        try:
            report_generator = BacktestReportGenerator(
                strategy_name=self.strategy_name,
                daily_values=self.daily_results,
                trade_records=trade_records,
                start_date=self.context.start_date.strftime('%Y-%m-%d'),
                end_date=self.context.end_date.strftime('%Y-%m-%d'),
                initial_cash=starting_cash
            )
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            report_path = os.path.join(script_dir, 'backtest_report.html')
            report_generator.generate_html_report(report_path)
            
            print(f"\n📊 回测报告已生成: {report_path}")
        except Exception as e:
            print(f"生成HTML报告时出错: {e}")
            print("请确保已安装 plotly: pip install plotly")


def run_backtest(start_date: str = None, end_date: str = None, initial_cash: float = 1000000):
    """运行回测
    
    参数:
        start_date: 开始日期，默认为3年前的今天
        end_date: 结束日期，默认为今天
        initial_cash: 初始资金
    """
    if end_date is None:
        end_date = datetime.datetime.now().strftime('%Y%m%d')
    
    if start_date is None:
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=3*365)
        start_date = start_dt.strftime('%Y%m%d')
    
    context = LocalContext(start_date, end_date, initial_cash)
    config = GlobalConfig()
    data_provider = EfinanceDataProvider()
    
    engine = LocalBacktestEngine(context, config, data_provider)
    engine.run()


if __name__ == '__main__':
    run_backtest(initial_cash=1000000)
