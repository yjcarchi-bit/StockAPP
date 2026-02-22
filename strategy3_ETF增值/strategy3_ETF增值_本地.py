# 克隆自聚宽文章：https://www.joinquant.com/post/67285
# 标题：来聚宽大半年了，准备全仓实盘了
# 作者：LULL
# 本地化版本：使用efinance获取数据，支持本地回测

# 策略名称：ETF收益率稳定性轮动策略（带短期动量过滤和ATR动态止损）- 本地版本
# 策略作者：屌丝逆袭量化
# 优化时间：2025-12-30
# 本地化时间：2026-02-21

import numpy as np
import math
import pandas as pd
from datetime import datetime, timedelta
import efinance as ef
import time
import warnings
import os
import sys
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from backtest_report_generator import BacktestReportGenerator
except ImportError:
    BacktestReportGenerator = None

try:
    from etf_strategy_pdf_report import ETFStrategyPDFReport, generate_pdf_report_from_strategy
except ImportError:
    ETFStrategyPDFReport = None
    generate_pdf_report_from_strategy = None

class ETFStrategy:
    """
    ETF收益率稳定性轮动策略 - 本地版本
    """
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.position_highs = {}
        self.position_stop_prices = {}
        self.position_cost = {}
        self.trade_history = []
        self.daily_values = []
        
        self.etf_pool0 = [
            "159915",  # 创业板ETF
            "518880",  # 黄金ETF
            "513100",  # 纳指ETF
            "511220",  # 城投债ETF
        ]
        
        self.etf_pool = [
            "518880", "159980", "159985", "501018",
            "513100", "513500", "513520", "513030", "513080",
            "159920",
            "510300", "510500", "510050", "510210", "159915",
            "588080", "159995", "513050", "159852", "159845",
            "515030", "159806", "516160", "159928", "512670",
            "511010", "511880",
        ]
        
        self.lookback_days = 25
        self.holdings_num = 1
        self.stop_loss = 0.95
        self.loss = 0.97
        self.defensive_etf = "511880"
        self.min_score_threshold = 0.0
        self.max_score_threshold = 6.0
        self.min_money = 5000
        
        self.use_short_momentum_filter = True
        self.short_lookback_days = 12
        self.short_momentum_threshold = 0.0
        
        self.use_atr_stop_loss = True
        self.atr_period = 14
        self.atr_multiplier = 2
        self.atr_trailing_stop = False
        self.atr_exclude_defensive = True
        
        self.use_ma_filter = False
        self.ma_short_period = 5
        self.ma_long_period = 25
        self.ma_filter_condition = "above"
        
        self.use_rsi_filter = False
        self.rsi_period = 6
        self.rsi_lookback_days = 1
        self.rsi_threshold = 95
        
        self.use_macd_filter = False
        self.macd_fast_period = 12
        self.macd_slow_period = 26
        self.macd_signal_period = 9
        self.macd_filter_condition = "bullish"
        
        self.use_volume_filter = False
        self.volume_lookback_days = 7
        self.volume_threshold = 2.0
        self.volume_exclude_defensive = True
        
        self.use_bollinger_filter = False
        self.bollinger_period = 20
        self.bollinger_std = 2.0
        self.bollinger_lookback_days = 3
        
        self.etf_names = {}
        self._load_etf_names()
        
    def _load_etf_names(self):
        """加载ETF名称"""
        self.etf_names = {
            "159915": "创业板ETF",
            "518880": "黄金ETF",
            "513100": "纳指ETF",
            "511220": "城投债ETF",
            "159980": "有色ETF",
            "159985": "豆粕ETF",
            "501018": "南方原油LOF",
            "513500": "标普500ETF",
            "513520": "日经ETF",
            "513030": "德国ETF",
            "513080": "法国ETF",
            "159920": "恒生ETF",
            "510300": "沪深300ETF",
            "510500": "中证500ETF",
            "510050": "上证50ETF",
            "510210": "上证指数ETF",
            "588080": "科创板50ETF",
            "159995": "芯片ETF",
            "513050": "中概互联ETF",
            "159852": "半导体ETF",
            "159845": "新能源ETF",
            "515030": "新能源车ETF",
            "159806": "光伏ETF",
            "516160": "新能源ETF",
            "159928": "消费ETF",
            "512670": "国防军工ETF",
            "511010": "国债ETF",
            "511880": "银华日利",
        }
    
    def get_etf_name(self, etf_code):
        """获取ETF名称"""
        return self.etf_names.get(etf_code, etf_code)
    
    def get_etf_data(self, etf_code, start_date, end_date):
        """
        使用efinance获取ETF历史数据
        """
        try:
            df = ef.stock.get_quote_history(
                etf_code,
                beg=start_date.strftime('%Y%m%d'),
                end=end_date.strftime('%Y%m%d'),
                klt=101,
                fqt=1
            )
            
            if df is None or len(df) == 0:
                return None
            
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df = df.reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"获取{etf_code}数据失败: {e}")
            return None
    
    def get_latest_price(self, etf_code):
        """
        获取ETF最新价格
        """
        try:
            df = ef.stock.get_quote_history(
                etf_code,
                beg=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                end=datetime.now().strftime('%Y%m%d'),
                klt=101,
                fqt=1
            )
            
            if df is not None and len(df) > 0:
                return float(df['收盘'].iloc[-1])
            return 0
            
        except Exception as e:
            print(f"获取{etf_code}最新价格失败: {e}")
            return 0
    
    def calculate_atr(self, high_prices, low_prices, close_prices, period=14):
        """
        计算ATR指标
        """
        if len(high_prices) < period + 1:
            return 0, [], False, f"数据不足{period+1}天"
        
        tr_values = np.zeros(len(high_prices))
        
        for i in range(1, len(high_prices)):
            tr1 = high_prices[i] - low_prices[i]
            tr2 = abs(high_prices[i] - close_prices[i-1])
            tr3 = abs(low_prices[i] - close_prices[i-1])
            tr_values[i] = max(tr1, tr2, tr3)
        
        atr_values = np.zeros(len(tr_values))
        for i in range(period, len(tr_values)):
            atr_values[i] = np.mean(tr_values[i-period+1:i+1])
        
        current_atr = atr_values[-1] if len(atr_values) > 0 else 0
        valid_atr = atr_values[period:] if len(atr_values) > period else atr_values
        
        return current_atr, valid_atr, True, "计算成功"
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2.0):
        """
        计算布林带指标
        """
        if len(prices) < period:
            return [], [], []
        
        middle_band = np.zeros(len(prices))
        upper_band = np.zeros(len(prices))
        lower_band = np.zeros(len(prices))
        
        for i in range(period - 1, len(prices)):
            window = prices[i-period+1:i+1]
            middle = np.mean(window)
            std = np.std(window)
            
            middle_band[i] = middle
            upper_band[i] = middle + std_dev * std
            lower_band[i] = middle - std_dev * std
        
        return middle_band[period-1:], upper_band[period-1:], lower_band[period-1:]
    
    def calculate_rsi(self, prices, period=6):
        """
        计算RSI指标
        """
        if len(prices) < period + 1:
            return []
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.zeros_like(prices)
        avg_losses = np.zeros_like(prices)
        
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        rsi_values = np.zeros(len(prices))
        rsi_values[:period] = 50
        
        for i in range(period + 1, len(prices)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
            
            if avg_losses[i] == 0:
                rsi_values[i] = 100
            else:
                rs = avg_gains[i] / avg_losses[i]
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return rsi_values[period:]
    
    def calculate_macd(self, prices, fast_period=12, slow_period=26, signal_period=9):
        """
        计算MACD指标
        """
        if len(prices) < slow_period + signal_period:
            return [], [], []
        
        def calculate_ema(data, period):
            ema = np.zeros_like(data)
            ema[0] = data[0]
            alpha = 2 / (period + 1)
            
            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
            return ema
        
        ema_fast = calculate_ema(prices, fast_period)
        ema_slow = calculate_ema(prices, slow_period)
        dif = ema_fast - ema_slow
        dea = calculate_ema(dif, signal_period)
        macd_bar = dif - dea
        
        start_idx = slow_period + signal_period - 1
        return dif[start_idx:], dea[start_idx:], macd_bar[start_idx:]
    
    def check_bollinger_filter(self, etf_code, close_prices, current_price):
        """
        检查布林带过滤条件
        """
        try:
            if len(close_prices) < self.bollinger_period:
                return True, f"数据不足{self.bollinger_period}天"
            
            middle_band, upper_band, lower_band = self.calculate_bollinger_bands(
                close_prices, self.bollinger_period, self.bollinger_std
            )
            
            if len(upper_band) < self.bollinger_lookback_days:
                return True, f"布林带数据不足{self.bollinger_lookback_days}天"
            
            recent_upper_band = upper_band[-self.bollinger_lookback_days:]
            recent_close_prices = close_prices[-self.bollinger_lookback_days:]
            
            breakthrough_occurred = False
            for i in range(len(recent_close_prices)):
                if recent_close_prices[i] > recent_upper_band[i]:
                    breakthrough_occurred = True
                    break
            
            if len(close_prices) >= 5:
                ma5 = np.mean(close_prices[-5:])
            else:
                ma5 = np.mean(close_prices)
            
            if breakthrough_occurred and current_price < ma5:
                return False, f"近{self.bollinger_lookback_days}日曾突破布林带上轨，且当前价{current_price:.3f}<MA5({ma5:.3f})"
            else:
                return True, "布林带检查通过"
        
        except Exception as e:
            print(f"检查{etf_code}布林带时出错: {e}")
            return True, f"检查出错:{str(e)}"
    
    def check_volume_anomaly(self, etf_code, volume_data, recent_volume):
        """
        检查成交量是否异常
        """
        if self.volume_exclude_defensive and etf_code == self.defensive_etf:
            return True, 0.0, 0, 0, "防御ETF豁免成交量检查"
        
        try:
            if len(volume_data) < self.volume_lookback_days:
                return True, 0.0, recent_volume, 0, f"数据不足{self.volume_lookback_days}天"
            
            if len(volume_data) >= self.volume_lookback_days + 1:
                avg_volume = np.mean(volume_data[-(self.volume_lookback_days+1):-1])
            else:
                avg_volume = np.mean(volume_data[:-1])
            
            if avg_volume <= 0:
                return True, 0.0, recent_volume, avg_volume, f"历史均量异常:{avg_volume:.0f}"
            
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
            
            if volume_ratio > self.volume_threshold:
                return False, volume_ratio, recent_volume, avg_volume, f"成交量异常:近1分钟{recent_volume:.0f} > 近{self.volume_lookback_days}日均值{avg_volume:.0f}的{self.volume_threshold}倍"
            else:
                return True, volume_ratio, recent_volume, avg_volume, f"成交量正常:比值{volume_ratio:.2f}"
        
        except Exception as e:
            print(f"检查{etf_code}成交量时出错: {e}")
            return True, 0.0, 0, 0, f"检查出错:{str(e)}"
    
    def calculate_momentum_metrics(self, etf_code, end_date):
        """
        计算ETF动量得分
        """
        try:
            lookback = max(self.lookback_days, self.short_lookback_days, self.ma_long_period,
                          self.rsi_period + self.rsi_lookback_days,
                          self.macd_slow_period + self.macd_signal_period,
                          self.volume_lookback_days,
                          self.bollinger_period + self.bollinger_lookback_days) + 30
            
            start_date = end_date - timedelta(days=lookback * 2)
            
            df = self.get_etf_data(etf_code, start_date, end_date)
            
            if df is None or len(df) < lookback:
                return None
            
            df = df.tail(lookback + 10)
            
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            volume_data = df['volume'].values
            
            current_price = close_prices[-1]
            if current_price <= 0:
                return None
            
            if len(close_prices) >= self.ma_long_period:
                ma5 = np.mean(close_prices[-self.ma_short_period:])
                ma25 = np.mean(close_prices[-self.ma_long_period:])
                
                if self.ma_filter_condition == "above":
                    ma_condition_met = ma5 >= ma25
                    condition_desc = f"MA{self.ma_short_period}>={self.ma_long_period}"
                else:
                    ma_condition_met = ma5 <= ma25
                    condition_desc = f"MA{self.ma_short_period}<={self.ma_long_period}"
                
                ma_ratio = ma5 / ma25 - 1
            else:
                ma5 = 0
                ma25 = 0
                ma_condition_met = True
                ma_ratio = 0
                condition_desc = "数据不足"
            
            rsi_filter_pass = True
            current_rsi = 0
            max_rsi = 0
            rsi_info = "未启用RSI过滤或数据不足"
            
            if self.use_rsi_filter and len(close_prices) >= self.rsi_period + self.rsi_lookback_days:
                rsi_values = self.calculate_rsi(close_prices, self.rsi_period)
                
                if len(rsi_values) >= self.rsi_lookback_days:
                    recent_rsi = rsi_values[-self.rsi_lookback_days:]
                    rsi_ever_above_threshold = np.any(recent_rsi > self.rsi_threshold)
                    current_below_ma5 = current_price < ma5 if ma5 > 0 else False
                    
                    if rsi_ever_above_threshold and current_below_ma5:
                        rsi_filter_pass = False
                        max_rsi = np.max(recent_rsi)
                        current_rsi = recent_rsi[-1] if len(recent_rsi) > 0 else 0
                        print(f"⛔ RSI过滤: {etf_code} 近{self.rsi_lookback_days}日RSI曾达{max_rsi:.1f}，当前价{current_price:.3f}<MA5，RSI={current_rsi:.1f}")
                    else:
                        max_rsi = np.max(recent_rsi) if len(recent_rsi) > 0 else 0
                        current_rsi = recent_rsi[-1] if len(recent_rsi) > 0 else 0
                        rsi_info = f"RSI(max={max_rsi:.1f}, current={current_rsi:.1f})"
            
            macd_filter_pass = True
            dif_value = 0
            dea_value = 0
            macd_bar = 0
            macd_info = "未启用MACD过滤或数据不足"
            
            if self.use_macd_filter and len(close_prices) >= self.macd_slow_period + self.macd_signal_period:
                dif_values, dea_values, macd_bars = self.calculate_macd(
                    close_prices, 
                    self.macd_fast_period, 
                    self.macd_slow_period, 
                    self.macd_signal_period
                )
                
                if len(dif_values) > 0:
                    dif_value = dif_values[-1]
                    dea_value = dea_values[-1]
                    macd_bar = macd_bars[-1]
                    
                    if self.macd_filter_condition == "bullish":
                        macd_condition_met = dif_value > dea_value
                        condition_desc = f"DIF({dif_value:.4f})>DEA({dea_value:.4f})"
                    else:
                        macd_condition_met = dif_value < dea_value
                        condition_desc = f"DIF({dif_value:.4f})<DEA({dea_value:.4f})"
                    
                    macd_filter_pass = macd_condition_met
                    macd_info = f"MACD(DIF={dif_value:.4f}, DEA={dea_value:.4f}, BAR={macd_bar:.4f})"
                    
                    if not macd_filter_pass:
                        print(f"📉 MACD过滤: {etf_code} 不满足{condition_desc}，MACD柱={macd_bar:.4f}")
            
            volume_filter_pass = True
            volume_ratio = 0
            recent_volume = 0
            avg_volume = 0
            volume_info = "未启用成交量过滤"
            
            if self.use_volume_filter:
                recent_volume = volume_data[-1] if len(volume_data) > 0 else 0
                volume_filter_pass, volume_ratio, recent_volume, avg_volume, volume_info = self.check_volume_anomaly(
                    etf_code, volume_data, recent_volume
                )
                
                if not volume_filter_pass:
                    print(f"📊 成交量过滤: {etf_code} {volume_info}")
            
            bollinger_filter_pass = True
            bollinger_info = "未启用布林带过滤"
            
            if self.use_bollinger_filter:
                bollinger_filter_pass, bollinger_info = self.check_bollinger_filter(
                    etf_code, close_prices[:-1], current_price
                )
                
                if not bollinger_filter_pass:
                    print(f"📈 布林带过滤: {etf_code} {bollinger_info}")
            
            if len(close_prices) >= self.short_lookback_days + 1:
                short_return = close_prices[-1] / close_prices[-(self.short_lookback_days + 1)] - 1
                short_annualized = (1 + short_return) ** (250 / self.short_lookback_days) - 1
            else:
                short_return = 0
                short_annualized = 0
            
            recent_days = min(self.lookback_days, len(close_prices) - 1)
            if recent_days >= 10:
                recent_price_series = close_prices[-(recent_days+1):]
                y = np.log(recent_price_series)
                x = np.arange(len(y))
                weights = np.linspace(1, 2, len(y))
                
                slope, intercept = np.polyfit(x, y, 1, w=weights)
                annualized_returns = math.exp(slope * 250) - 1
                
                ss_res = np.sum(weights * (y - (slope * x + intercept)) ** 2)
                ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
                r_squared = 1 - ss_res / ss_tot if ss_tot else 0
                
                score = annualized_returns * r_squared
                
                if len(close_prices) >= 4:
                    day1_ratio = close_prices[-1] / close_prices[-2]
                    day2_ratio = close_prices[-2] / close_prices[-3]
                    day3_ratio = close_prices[-3] / close_prices[-4]
                    
                    if min(day1_ratio, day2_ratio, day3_ratio) < self.loss:
                        score = 0
                        print(f"⚠️ {etf_code} 近3日有单日跌幅超{((1-self.loss)*100):.0f}%，已排除")
            else:
                annualized_returns = 0
                r_squared = 0
                score = 0
            
            return {
                'etf': etf_code,
                'annualized_returns': annualized_returns,
                'r_squared': r_squared,
                'score': score,
                'current_price': current_price,
                'short_return': short_return,
                'short_annualized': short_annualized,
                'short_momentum_pass': short_return >= self.short_momentum_threshold,
                'ma5': ma5,
                'ma25': ma25,
                'ma_condition_met': ma_condition_met,
                'ma_ratio': ma_ratio,
                'rsi_filter_pass': rsi_filter_pass,
                'current_rsi': current_rsi,
                'max_recent_rsi': max_rsi,
                'macd_filter_pass': macd_filter_pass,
                'dif': dif_value,
                'dea': dea_value,
                'macd_bar': macd_bar,
                'volume_filter_pass': volume_filter_pass,
                'volume_ratio': volume_ratio,
                'bollinger_filter_pass': bollinger_filter_pass,
                'bollinger_info': bollinger_info,
                'high_prices': high_prices,
                'low_prices': low_prices,
                'close_prices': close_prices
            }
        except Exception as e:
            print(f"计算{etf_code}动量指标时出错: {e}")
            return None
    
    def get_ranked_etfs(self, end_date):
        """
        获取排名ETF
        """
        etf_metrics = []
        for etf in self.etf_pool:
            print(f"正在计算 {etf} {self.get_etf_name(etf)} 的动量指标...")
            metrics = self.calculate_momentum_metrics(etf, end_date)
            
            if metrics is not None:
                if self.use_short_momentum_filter and not metrics['short_momentum_pass']:
                    print(f"📉 排除短期动量不足的ETF: {etf}，短期动量: {metrics['short_return']:.4f}")
                    continue
                
                if self.use_ma_filter and not metrics['ma_condition_met']:
                    print(f"📊 排除MA条件不符的ETF: {etf}，MA{self.ma_short_period}: {metrics['ma5']:.3f}，MA{self.ma_long_period}: {metrics['ma25']:.3f}")
                    continue
                
                if self.use_rsi_filter and not metrics['rsi_filter_pass']:
                    continue
                
                if self.use_macd_filter and not metrics['macd_filter_pass']:
                    continue
                
                if self.use_volume_filter and not metrics['volume_filter_pass']:
                    continue
                
                if self.use_bollinger_filter and not metrics['bollinger_filter_pass']:
                    continue
                
                if 0 < metrics['score'] < self.max_score_threshold:
                    etf_metrics.append(metrics)
                else:
                    print(f"排除异常值ETF: {etf}，得分: {metrics['score']:.4f}")
            
            time.sleep(0.5)
        
        etf_metrics.sort(key=lambda x: x['score'], reverse=True)
        return etf_metrics
    
    def check_atr_stop_loss(self, current_date, metrics_dict):
        """
        检查并执行ATR动态止损
        """
        if not self.use_atr_stop_loss:
            return
        
        for etf_code in list(self.positions.keys()):
            if etf_code not in self.etf_pool:
                continue
            
            if self.positions[etf_code] <= 0:
                continue
            
            if self.atr_exclude_defensive and etf_code == self.defensive_etf:
                continue
            
            try:
                metrics = metrics_dict.get(etf_code)
                if metrics is None:
                    continue
                
                current_price = metrics['current_price']
                if current_price <= 0:
                    continue
                
                cost_price = self.position_cost.get(etf_code, current_price)
                
                current_atr, _, success, _ = self.calculate_atr(
                    metrics['high_prices'],
                    metrics['low_prices'],
                    metrics['close_prices'],
                    self.atr_period
                )
                
                if not success:
                    continue
                
                if etf_code not in self.position_highs:
                    self.position_highs[etf_code] = current_price
                else:
                    self.position_highs[etf_code] = max(self.position_highs[etf_code], current_price)
                
                position_high = self.position_highs[etf_code]
                
                if self.atr_trailing_stop:
                    atr_stop_price = position_high - self.atr_multiplier * current_atr
                else:
                    atr_stop_price = cost_price - self.atr_multiplier * current_atr
                
                self.position_stop_prices[etf_code] = atr_stop_price
                
                if current_price <= atr_stop_price:
                    self.sell_etf(etf_code, current_price, current_date)
                    loss_percent = (current_price/cost_price - 1) * 100
                    atr_stop_type = "跟踪" if self.atr_trailing_stop else "固定"
                    print(f"🚨 ATR动态止损({atr_stop_type})卖出: {etf_code} {self.get_etf_name(etf_code)}，成本: {cost_price:.3f}，现价: {current_price:.3f}，ATR: {current_atr:.3f}，止损价: {atr_stop_price:.3f}，亏损: {loss_percent:.2f}%")
                    
                    if etf_code in self.position_highs:
                        del self.position_highs[etf_code]
                    if etf_code in self.position_stop_prices:
                        del self.position_stop_prices[etf_code]
            
            except Exception as e:
                print(f"检查{etf_code} ATR止损时出错: {e}")
    
    def check_fixed_stop_loss(self, current_date, metrics_dict):
        """
        检查固定百分比止损
        """
        for etf_code in list(self.positions.keys()):
            if etf_code not in self.etf_pool:
                continue
            
            if self.positions[etf_code] <= 0:
                continue
            
            try:
                metrics = metrics_dict.get(etf_code)
                if metrics is None:
                    continue
                
                current_price = metrics['current_price']
                cost_price = self.position_cost.get(etf_code, current_price)
                
                if current_price <= cost_price * self.stop_loss:
                    self.sell_etf(etf_code, current_price, current_date)
                    loss_percent = (current_price/cost_price - 1) * 100
                    print(f"🚨 固定百分比止损卖出: {etf_code} {self.get_etf_name(etf_code)}，成本: {cost_price:.3f}，现价: {current_price:.3f}，亏损: {loss_percent:.2f}%")
                    
                    if etf_code in self.position_highs:
                        del self.position_highs[etf_code]
                    if etf_code in self.position_stop_prices:
                        del self.position_stop_prices[etf_code]
            
            except Exception as e:
                print(f"检查{etf_code}固定止损时出错: {e}")
    
    def buy_etf(self, etf_code, price, amount, current_date):
        """
        买入ETF
        """
        cost = price * amount
        if cost > self.cash:
            amount = int(self.cash / price / 100) * 100
            if amount <= 0:
                print(f"资金不足，无法买入 {etf_code}")
                return False
            cost = price * amount
        
        self.cash -= cost
        
        if etf_code in self.positions:
            old_amount = self.positions[etf_code]
            old_cost = self.position_cost[etf_code] * old_amount
            self.positions[etf_code] += amount
            self.position_cost[etf_code] = (old_cost + cost) / self.positions[etf_code]
        else:
            self.positions[etf_code] = amount
            self.position_cost[etf_code] = price
        
        self.position_highs[etf_code] = price
        
        trade_record = {
            'date': current_date,
            'action': 'buy',
            'etf': etf_code,
            'name': self.get_etf_name(etf_code),
            'price': price,
            'amount': amount,
            'value': cost
        }
        self.trade_history.append(trade_record)
        
        print(f"📥 买入 {etf_code} {self.get_etf_name(etf_code)}，数量: {amount}，价格: {price:.3f}，金额: {cost:.2f}")
        return True
    
    def sell_etf(self, etf_code, price, current_date):
        """
        卖出ETF
        """
        if etf_code not in self.positions or self.positions[etf_code] <= 0:
            return False
        
        amount = self.positions[etf_code]
        revenue = price * amount
        
        self.cash += revenue
        self.positions[etf_code] = 0
        
        trade_record = {
            'date': current_date,
            'action': 'sell',
            'etf': etf_code,
            'name': self.get_etf_name(etf_code),
            'price': price,
            'amount': amount,
            'value': revenue
        }
        self.trade_history.append(trade_record)
        
        print(f"📤 卖出 {etf_code} {self.get_etf_name(etf_code)}，数量: {amount}，价格: {price:.3f}，金额: {revenue:.2f}")
        return True
    
    def get_total_value(self, metrics_dict):
        """
        计算总资产价值
        """
        total = self.cash
        for etf_code, amount in self.positions.items():
            if amount > 0:
                metrics = metrics_dict.get(etf_code)
                if metrics:
                    total += amount * metrics['current_price']
        return total
    
    def is_defensive_etf_available(self, metrics_dict):
        """
        检查防御性ETF是否可交易
        """
        defensive_etf = self.defensive_etf
        
        if defensive_etf not in self.etf_pool:
            return False
        
        metrics = metrics_dict.get(defensive_etf)
        if metrics is None:
            return False
        
        current_price = metrics['current_price']
        if current_price <= 0:
            return False
        
        return True
    
    def run_backtest(self, start_date, end_date):
        """
        运行回测
        """
        print("=" * 60)
        print("ETF收益率稳定性轮动策略 - 本地回测")
        print("=" * 60)
        print(f"回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        print(f"初始资金: {self.initial_capital:,.2f}")
        print("=" * 60)
        
        current_date = start_date
        trade_dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        for trade_date in trade_dates:
            print(f"\n{'='*60}")
            print(f"📅 交易日: {trade_date.strftime('%Y-%m-%d')}")
            print(f"{'='*60}")
            
            metrics_dict = {}
            for etf_code in self.etf_pool:
                metrics = self.calculate_momentum_metrics(etf_code, trade_date)
                if metrics:
                    metrics_dict[etf_code] = metrics
                time.sleep(0.3)
            
            if not metrics_dict:
                print(f"无法获取{trade_date.strftime('%Y-%m-%d')}的数据，跳过")
                continue
            
            self.check_atr_stop_loss(trade_date, metrics_dict)
            self.check_fixed_stop_loss(trade_date, metrics_dict)
            
            ranked_etfs = []
            for etf_code in self.etf_pool:
                metrics = metrics_dict.get(etf_code)
                if metrics:
                    if self.use_short_momentum_filter and not metrics['short_momentum_pass']:
                        continue
                    if self.use_ma_filter and not metrics['ma_condition_met']:
                        continue
                    if self.use_rsi_filter and not metrics['rsi_filter_pass']:
                        continue
                    if self.use_macd_filter and not metrics['macd_filter_pass']:
                        continue
                    if self.use_volume_filter and not metrics['volume_filter_pass']:
                        continue
                    if self.use_bollinger_filter and not metrics['bollinger_filter_pass']:
                        continue
                    if 0 < metrics['score'] < self.max_score_threshold:
                        ranked_etfs.append(metrics)
            
            ranked_etfs.sort(key=lambda x: x['score'], reverse=True)
            
            print("\n=== ETF趋势指标分析 ===")
            for metrics in ranked_etfs[:5]:
                print(f"{metrics['etf']} {self.get_etf_name(metrics['etf'])}: 年化={metrics['annualized_returns']:.4f}, R²={metrics['r_squared']:.4f}, 得分={metrics['score']:.4f}, 短期动量={metrics['short_return']:.4f}, 当前价={metrics['current_price']:.3f}")
            
            target_etf = None
            if ranked_etfs and ranked_etfs[0]['score'] >= self.min_score_threshold:
                target_etf = ranked_etfs[0]['etf']
                print(f"\n🎯 正常模式，选择得分最高的ETF: {target_etf} {self.get_etf_name(target_etf)}，得分: {ranked_etfs[0]['score']:.4f}")
            else:
                if self.is_defensive_etf_available(metrics_dict):
                    target_etf = self.defensive_etf
                    print(f"\n🛡️ 进入防御模式，选择防御ETF: {target_etf} {self.get_etf_name(target_etf)}")
                else:
                    print("\n💤 进入空仓模式")
            
            for etf_code in list(self.positions.keys()):
                if etf_code in self.etf_pool and self.positions[etf_code] > 0:
                    if etf_code != target_etf:
                        metrics = metrics_dict.get(etf_code)
                        if metrics:
                            self.sell_etf(etf_code, metrics['current_price'], trade_date)
            
            if target_etf:
                metrics = metrics_dict.get(target_etf)
                if metrics:
                    current_position = self.positions.get(target_etf, 0)
                    current_value = current_position * metrics['current_price']
                    total_value = self.get_total_value(metrics_dict)
                    
                    if current_position == 0 or abs(current_value - total_value) > total_value * 0.05:
                        if current_position > 0:
                            self.sell_etf(target_etf, metrics['current_price'], trade_date)
                        
                        target_amount = int(total_value / metrics['current_price'] / 100) * 100
                        if target_amount > 0:
                            self.buy_etf(target_etf, metrics['current_price'], target_amount, trade_date)
            
            total_value = self.get_total_value(metrics_dict)
            self.daily_values.append({
                'date': trade_date,
                'value': total_value,
                'cash': self.cash,
                'positions': dict(self.positions)
            })
            
            print(f"\n📊 当日资产: {total_value:,.2f} (现金: {self.cash:,.2f})")
        
        self.print_backtest_results()
    
    def print_backtest_results(self):
        """
        打印回测结果
        """
        print("\n" + "=" * 60)
        print("回测结果汇总")
        print("=" * 60)
        
        if not self.daily_values:
            print("无回测数据")
            return
        
        df_values = pd.DataFrame(self.daily_values)
        df_values['date'] = pd.to_datetime(df_values['date'])
        df_values = df_values.set_index('date')
        
        final_value = df_values['value'].iloc[-1]
        total_return = (final_value / self.initial_capital - 1) * 100
        
        df_values['daily_return'] = df_values['value'].pct_change()
        annual_return = df_values['daily_return'].mean() * 252 * 100
        annual_volatility = df_values['daily_return'].std() * np.sqrt(252) * 100
        sharpe_ratio = (annual_return - 3) / annual_volatility if annual_volatility > 0 else 0
        
        max_value = df_values['value'].expanding().max()
        drawdown = (df_values['value'] - max_value) / max_value
        max_drawdown = drawdown.min() * 100
        
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annual_return:.2f}%")
        print(f"年化波动率: {annual_volatility:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"交易次数: {len(self.trade_history)}")
        
        print("\n交易记录:")
        df_trades = pd.DataFrame(self.trade_history)
        if not df_trades.empty:
            print(df_trades.to_string(index=False))
        
        return df_values, df_trades

    def generate_report(self, output_path=None):
        """
        生成报告（HTML和PDF）
        """
        if not self.daily_values:
            print("无回测数据，无法生成报告")
            return None
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if generate_pdf_report_from_strategy is not None:
            pdf_path = os.path.join(script_dir, 'backtest_report.pdf')
            try:
                generate_pdf_report_from_strategy(self, pdf_path)
            except Exception as e:
                print(f"生成PDF报告失败: {e}")
        
        if output_path is None:
            output_path = os.path.join(script_dir, 'backtest_report.html')
        
        if BacktestReportGenerator is not None:
            try:
                generator = BacktestReportGenerator(
                    strategy_name='ETF收益率稳定性轮动策略',
                    daily_values=[{'date': v['date'], 'total_value': v['value'], 
                                  'cash': v['cash'], 'position_value': v['value'] - v['cash']} 
                                 for v in self.daily_values],
                    trade_records=[{'date': t['date'], 'action': t['action'], 
                                   'code': t['etf'], 'name': t['name'],
                                   'price': t['price'], 'amount': t['amount'],
                                   'value': t['value']} 
                                  for t in self.trade_history],
                    start_date=self.daily_values[0]['date'].strftime('%Y-%m-%d') if self.daily_values else None,
                    end_date=self.daily_values[-1]['date'].strftime('%Y-%m-%d') if self.daily_values else None,
                    initial_cash=self.initial_capital
                )
                generator.generate_html_report(output_path)
            except Exception as e:
                print(f"生成HTML报告失败: {e}")


def main():
    """
    主函数
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    strategy = ETFStrategy(initial_capital=100000)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*3)
    
    strategy.run_backtest(start_date, end_date)
    strategy.generate_report()


if __name__ == "__main__":
    main()
