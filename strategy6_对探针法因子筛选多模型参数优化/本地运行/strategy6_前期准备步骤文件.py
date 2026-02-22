# --------------------------------------------------------------------------------
# 策略名称：对探针法因子筛选多模型参数优化 - 本地版本
# 原始来源：聚宽平台
# 本地化时间：2026-02-21
# 说明：将聚宽平台代码转换为本地可运行版本，使用efinance获取数据
# --------------------------------------------------------------------------------

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import efinance as ef
import time
import warnings
import os
import pickle
import lightgbm as lgb
from tqdm import tqdm
from scipy import stats
warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------------
# 1. 本地因子计算函数
# --------------------------------------------------------------------------------

class FactorCalculator:
    """本地因子计算器"""
    
    @staticmethod
    def calculate_ma(prices, window):
        """计算移动平均"""
        return pd.Series(prices).rolling(window=window).mean().values
    
    @staticmethod
    def calculate_ema(prices, window):
        """计算指数移动平均"""
        return pd.Series(prices).ewm(span=window, adjust=False).mean().values
    
    @staticmethod
    def calculate_std(prices, window):
        """计算滚动标准差"""
        return pd.Series(prices).rolling(window=window).std().values
    
    @staticmethod
    def calculate_momentum(prices, window):
        """计算动量"""
        return pd.Series(prices).pct_change(window).values
    
    @staticmethod
    def calculate_roc(prices, window):
        """计算变动率指标ROC"""
        return (pd.Series(prices) / pd.Series(prices).shift(window) - 1).values * 100
    
    @staticmethod
    def calculate_rsi(prices, window=14):
        """计算RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = pd.Series(gains).rolling(window=window).mean().values
        avg_losses = pd.Series(losses).rolling(window=window).mean().values
        
        rs = np.where(avg_losses != 0, avg_gains / avg_losses, 0)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        """计算MACD"""
        ema_fast = pd.Series(prices).ewm(span=fast, adjust=False).mean()
        ema_slow = pd.Series(prices).ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2
        return dif.values, dea.values, macd.values
    
    @staticmethod
    def calculate_atr(high, low, close, window=14):
        """计算ATR"""
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        tr[0] = tr1[0]
        atr = pd.Series(tr).rolling(window=window).mean().values
        return atr
    
    @staticmethod
    def calculate_kurtosis(returns, window):
        """计算峰度"""
        return pd.Series(returns).rolling(window=window).kurt().values
    
    @staticmethod
    def calculate_skewness(returns, window):
        """计算偏度"""
        return pd.Series(returns).rolling(window=window).skew().values
    
    @staticmethod
    def calculate_bollinger(prices, window=20, num_std=2):
        """计算布林带"""
        ma = pd.Series(prices).rolling(window=window).mean()
        std = pd.Series(prices).rolling(window=window).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        return ma.values, upper.values, lower.values
    
    @staticmethod
    def calculate_mfi(high, low, close, volume, window=14):
        """计算MFI资金流量指标"""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        positive_flow = np.where(typical_price > np.roll(typical_price, 1), money_flow, 0)
        negative_flow = np.where(typical_price < np.roll(typical_price, 1), money_flow, 0)
        
        positive_flow[0] = 0
        negative_flow[0] = 0
        
        positive_sum = pd.Series(positive_flow).rolling(window=window).sum().values
        negative_sum = pd.Series(negative_flow).rolling(window=window).sum().values
        
        mfi = 100 - (100 / (1 + positive_sum / np.where(negative_sum != 0, negative_sum, 1)))
        return mfi
    
    @staticmethod
    def calculate_wvad(close, open_price, high, low, volume, window=24):
        """计算WVAD威廉变异离散量"""
        wvad = ((close - open_price) / (high - low + 1e-10)) * volume
        wvad_ma = pd.Series(wvad).rolling(window=window).sum().values
        return wvad_ma
    
    @staticmethod
    def calculate_psy(prices, window=12):
        """计算PSY心理线"""
        up_days = (pd.Series(prices).diff() > 0).astype(int)
        psy = up_days.rolling(window=window).mean().values * 100
        return psy
    
    @staticmethod
    def calculate_vpt(close, volume):
        """计算VPT成交量变动率"""
        vpt = np.zeros(len(close))
        vpt[0] = 0
        for i in range(1, len(close)):
            vpt[i] = vpt[i-1] + volume[i] * (close[i] - close[i-1]) / (close[i-1] + 1e-10)
        return vpt
    
    @staticmethod
    def calculate_vmacd(volume, fast=12, slow=26, signal=9):
        """计算VMACD"""
        return FactorCalculator.calculate_macd(volume, fast, slow, signal)
    
    @staticmethod
    def calculate_bias(prices, window):
        """计算BIAS乖离率"""
        ma = pd.Series(prices).rolling(window=window).mean()
        bias = (pd.Series(prices) - ma) / ma * 100
        return bias.values
    
    @staticmethod
    def calculate_arron(high, low, window=25):
        """计算Arron指标"""
        aroon_up = np.zeros(len(high))
        aroon_down = np.zeros(len(high))
        
        for i in range(window, len(high)):
            high_window = high[i-window+1:i+1]
            low_window = low[i-window+1:i+1]
            
            high_idx = np.argmax(high_window)
            low_idx = np.argmin(low_window)
            
            aroon_up[i] = (window - high_idx) / window * 100
            aroon_down[i] = (window - low_idx) / window * 100
        
        return aroon_up, aroon_down
    
    @staticmethod
    def calculate_mass_index(high, low, window=25):
        """计算MASS指标"""
        range_hl = high - low
        ema9 = pd.Series(range_hl).ewm(span=9, adjust=False).mean()
        ema9_ema9 = ema9.ewm(span=9, adjust=False).mean()
        
        mass_ratio = ema9 / (ema9_ema9 + 1e-10)
        mass_index = mass_ratio.rolling(window=window).sum().values
        return mass_index
    
    @staticmethod
    def calculate_vosc(volume, window_short=12, window_long=26):
        """计算VOSC成交量震荡指标"""
        ma_short = pd.Series(volume).rolling(window=window_short).mean()
        ma_long = pd.Series(volume).rolling(window=window_long).mean()
        vosc = (ma_short - ma_long) / ma_long * 100
        return vosc.values
    
    @staticmethod
    def calculate_cr(high, low, close, window=20):
        """计算CR能量指标"""
        mid = (high + low) / 2
        
        up = np.where(high > np.roll(mid, 1), high - np.roll(mid, 1), 0)
        down = np.where(np.roll(mid, 1) > low, np.roll(mid, 1) - low, 0)
        
        up[0] = 0
        down[0] = 0
        
        up_sum = pd.Series(up).rolling(window=window).sum().values
        down_sum = pd.Series(down).rolling(window=window).sum().values
        
        cr = up_sum / (down_sum + 1e-10) * 100
        return cr
    
    @staticmethod
    def calculate_kdj(high, low, close, n=9, m1=3, m2=3):
        """计算KDJ指标"""
        low_n = pd.Series(low).rolling(window=n).min()
        high_n = pd.Series(high).rolling(window=n).max()
        
        rsv = (close - low_n) / (high_n - low_n + 1e-10) * 100
        
        k = pd.Series(rsv).ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k.values, d.values, j.values
    
    @staticmethod
    def calculate_cci(high, low, close, window=14):
        """计算CCI商品通道指标"""
        tp = (high + low + close) / 3
        ma = pd.Series(tp).rolling(window=window).mean()
        md = pd.Series(tp).rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - ma) / (0.015 * md + 1e-10)
        return cci.values
    
    @staticmethod
    def calculate_obv(close, volume):
        """计算OBV能量潮指标"""
        direction = np.where(close > np.roll(close, 1), 1, np.where(close < np.roll(close, 1), -1, 0))
        direction[0] = 0
        obv = np.cumsum(volume * direction)
        return obv
    
    @staticmethod
    def calculate_wr(high, low, close, window=14):
        """计算威廉指标W%R"""
        high_n = pd.Series(high).rolling(window=window).max()
        low_n = pd.Series(low).rolling(window=window).min()
        wr = (high_n - close) / (high_n - low_n + 1e-10) * 100
        return wr.values
    
    @staticmethod
    def calculate_dmi(high, low, close, window=14):
        """计算DMI指标"""
        up_move = high - np.roll(high, 1)
        down_move = np.roll(low, 1) - low
        
        up_move[0] = 0
        down_move[0] = 0
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        tr[0] = tr1[0]
        
        atr = pd.Series(tr).rolling(window=window).mean().values
        plus_di = 100 * pd.Series(plus_dm).rolling(window=window).mean().values / (atr + 1e-10)
        minus_di = 100 * pd.Series(minus_dm).rolling(window=window).mean().values / (atr + 1e-10)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = pd.Series(dx).rolling(window=window).mean().values
        
        return plus_di, minus_di, dx, adx
    
    @staticmethod
    def calculate_vwap(high, low, close, volume):
        """计算VWAP成交量加权平均价"""
        tp = (high + low + close) / 3
        vwap = np.cumsum(tp * volume) / (np.cumsum(volume) + 1e-10)
        return vwap
    
    @staticmethod
    def calculate_bollinger_width(prices, window=20, num_std=2):
        """计算布林带宽度"""
        ma = pd.Series(prices).rolling(window=window).mean()
        std = pd.Series(prices).rolling(window=window).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        width = (upper - lower) / (ma + 1e-10) * 100
        return width.values
    
    @staticmethod
    def calculate_price_position(close, window=20):
        """计算价格在N日内的相对位置"""
        low_n = pd.Series(close).rolling(window=window).min()
        high_n = pd.Series(close).rolling(window=window).max()
        position = (close - low_n) / (high_n - low_n + 1e-10)
        return position.values
    
    @staticmethod
    def calculate_volatility_ratio(close, short_window=5, long_window=20):
        """计算波动率比率"""
        returns = pd.Series(close).pct_change()
        short_vol = returns.rolling(window=short_window).std()
        long_vol = returns.rolling(window=long_window).std()
        ratio = short_vol / (long_vol + 1e-10)
        return ratio.values
    
    @staticmethod
    def calculate_volume_ratio(volume, window=5):
        """计算量比"""
        ma_volume = pd.Series(volume).rolling(window=window).mean()
        ratio = volume / (ma_volume + 1e-10)
        return ratio.values
    
    @staticmethod
    def calculate_trend_strength(close, window=20):
        """计算趋势强度（线性回归斜率/R²）"""
        from scipy import stats
        trends = np.zeros(len(close))
        r_squares = np.zeros(len(close))
        
        for i in range(window, len(close)):
            y = close[i-window:i]
            x = np.arange(window)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            trends[i] = slope / (close[i] + 1e-10) * 100
            r_squares[i] = r_value ** 2
        
        return trends, r_squares
    
    @staticmethod
    def calculate_mfi_divergence(close, mfi, window=10):
        """计算MFI背离"""
        divergence = np.zeros(len(close))
        for i in range(window, len(close)):
            price_trend = close[i] - close[i-window]
            mfi_trend = mfi[i] - mfi[i-window]
            if price_trend > 0 and mfi_trend < 0:
                divergence[i] = -1
            elif price_trend < 0 and mfi_trend > 0:
                divergence[i] = 1
        return divergence
    
    @staticmethod
    def calculate_rsi_divergence(close, rsi, window=10):
        """计算RSI背离"""
        divergence = np.zeros(len(close))
        for i in range(window, len(close)):
            price_trend = close[i] - close[i-window]
            rsi_trend = rsi[i] - rsi[i-window]
            if price_trend > 0 and rsi_trend < 0:
                divergence[i] = -1
            elif price_trend < 0 and rsi_trend > 0:
                divergence[i] = 1
        return divergence
    
    @staticmethod
    def calculate_macd_histogram(dif, dea):
        """计算MACD柱状图"""
        return (dif - dea) * 2
    
    @staticmethod
    def calculate_adl(high, low, close, volume):
        """计算累积/派发线ADL"""
        mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
        mfv = mfm * volume
        adl = np.cumsum(mfv)
        return adl
    
    @staticmethod
    def calculate_cm_f(close, volume, window=20):
        """计算Chaikin Money Flow"""
        mfm = ((close - pd.Series(close).rolling(window=window).min().values) - 
               (pd.Series(close).rolling(window=window).max().values - close)) / \
              (pd.Series(close).rolling(window=window).max().values - 
               pd.Series(close).rolling(window=window).min().values + 1e-10)
        mfv = mfm * volume
        cmf = pd.Series(mfv).rolling(window=window).sum().values / \
              (pd.Series(volume).rolling(window=window).sum().values + 1e-10)
        return cmf
    
    @staticmethod
    def calculate_trix(prices, window=14):
        """计算TRIX指标"""
        ema1 = pd.Series(prices).ewm(span=window, adjust=False).mean()
        ema2 = ema1.ewm(span=window, adjust=False).mean()
        ema3 = ema2.ewm(span=window, adjust=False).mean()
        trix = (ema3 - ema3.shift(1)) / (ema3.shift(1) + 1e-10) * 100
        return trix.values
    
    @staticmethod
    def calculate_uos(high, low, close, n1=7, n2=14, n3=28):
        """计算终极指标UOS"""
        th = np.maximum(high, np.roll(close, 1))
        tl = np.minimum(low, np.roll(close, 1))
        th[0] = high[0]
        tl[0] = low[0]
        
        xr = close - tl
        xh = th - tl
        
        uos1 = pd.Series(xr).rolling(window=n1).sum() / (pd.Series(xh).rolling(window=n1).sum() + 1e-10)
        uos2 = pd.Series(xr).rolling(window=n2).sum() / (pd.Series(xh).rolling(window=n2).sum() + 1e-10)
        uos3 = pd.Series(xr).rolling(window=n3).sum() / (pd.Series(xh).rolling(window=n3).sum() + 1e-10)
        
        uos = 100 * (uos1 * n1 * n3 + uos2 * n2 * n3 + uos3 * n1 * n2) / (n1 * n3 + n2 * n3 + n1 * n2)
        return uos.values
    
    @staticmethod
    def calculate_dpo(close, window=20):
        """计算DPO去趋势价格震荡"""
        ma = pd.Series(close).rolling(window=window).mean()
        dpo = close - ma.shift(int(window/2) + 1)
        return dpo.values
    
    @staticmethod
    def calculate_mom(close, window=10):
        """计算动量指标MOM"""
        return close - np.roll(close, window)
    
    @staticmethod
    def calculate_roc_ma(roc, window=10):
        """计算ROC的移动平均"""
        return pd.Series(roc).rolling(window=window).mean().values
    
    @staticmethod
    def calculate_price_rate(close, window=5):
        """计算价格变化率"""
        return (close - np.roll(close, window)) / (np.roll(close, window) + 1e-10) * 100
    
    @staticmethod
    def calculate_amplitude(high, low, close, window=20):
        """计算振幅"""
        amp = (high - low) / (close + 1e-10) * 100
        return pd.Series(amp).rolling(window=window).mean().values
    
    @staticmethod
    def calculate_turnover_rate(turnover, window=5):
        """计算换手率均值"""
        if turnover is not None and len(turnover) > 0:
            return pd.Series(turnover).rolling(window=window).mean().values
        return np.zeros(len(turnover) if turnover is not None else 1)
    
    @staticmethod
    def calculate_volume_trend(volume, window=10):
        """计算成交量趋势"""
        vol_ma = pd.Series(volume).rolling(window=window).mean()
        trend = volume / (vol_ma + 1e-10)
        return trend.values
    
    @staticmethod
    def calculate_price_volume_corr(close, volume, window=20):
        """计算量价相关性"""
        corr = np.zeros(len(close))
        for i in range(window, len(close)):
            if np.std(close[i-window:i]) > 0 and np.std(volume[i-window:i]) > 0:
                corr[i] = np.corrcoef(close[i-window:i], volume[i-window:i])[0, 1]
        return corr
    
    @staticmethod
    def calculate_max_drawdown(close, window=60):
        """计算滚动最大回撤"""
        drawdown = np.zeros(len(close))
        for i in range(window, len(close)):
            peak = np.max(close[i-window:i])
            drawdown[i] = (peak - close[i]) / (peak + 1e-10)
        return drawdown
    
    @staticmethod
    def calculate_sharpe_like(close, window=20):
        """计算类夏普比率"""
        returns = pd.Series(close).pct_change()
        mean_ret = returns.rolling(window=window).mean()
        std_ret = returns.rolling(window=window).std()
        sharpe = mean_ret / (std_ret + 1e-10) * np.sqrt(252)
        return sharpe.values
    
    @staticmethod
    def calculate_sortino_like(close, window=20):
        """计算类索提诺比率"""
        returns = pd.Series(close).pct_change()
        mean_ret = returns.rolling(window=window).mean()
        downside = returns.rolling(window=window).apply(lambda x: np.sqrt(np.mean(np.minimum(x, 0)**2)))
        sortino = mean_ret / (downside + 1e-10) * np.sqrt(252)
        return sortino.values
    
    @staticmethod
    def calculate_calmar_like(close, window=60):
        """计算类卡尔马比率"""
        returns = pd.Series(close).pct_change()
        ann_return = returns.rolling(window=window).mean() * 252
        
        max_dd = np.zeros(len(close))
        for i in range(window, len(close)):
            peak = np.max(close[i-window:i])
            max_dd[i] = (peak - close[i]) / (peak + 1e-10)
        
        calmar = ann_return / (max_dd + 1e-10)
        return calmar.values


# --------------------------------------------------------------------------------
# 2. 数据获取函数
# --------------------------------------------------------------------------------

class DataFetcher:
    """数据获取类"""
    
    def __init__(self):
        self.cache = {}
    
    def get_stock_list(self, date):
        """
        获取A股股票列表（排除科创板、创业板、北交所）
        直接使用沪深300成分股作为股票池
        """
        return self._get_default_stock_list()
    
    def _get_default_stock_list(self):
        """获取默认股票列表（沪深300成分股）"""
        default_stocks = [
            '600000', '600009', '600010', '600011', '600015',
            '600016', '600018', '600019', '600025', '600028',
            '600029', '600030', '600031', '600036', '600048',
            '600050', '600104', '600109', '600111', '600115',
            '600118', '600150', '600176', '600183', '600208',
            '600233', '600276', '600309', '600332', '600346',
            '600352', '600436', '600438', '600486', '600489',
            '600498', '600519', '600547', '600570', '600585',
            '600588', '600690', '600703', '600745', '600809',
            '600837', '600845', '600848', '600887', '600893',
            '600900', '600905', '600918', '600919', '600926',
            '600941', '601012', '601066', '601088', '601138',
            '601166', '601225', '601236', '601288', '601318',
            '601328', '601336', '601390', '601398', '601601',
            '601628', '601633', '601668', '601669', '601688',
            '601728', '601766', '601788', '601800', '601818',
            '601857', '601877', '601880', '601888', '601899',
            '601901', '601919', '601939', '601988', '601989',
            '000001', '000002', '000063', '000066', '000069',
            '000100', '000157', '000166', '000333', '000338',
            '000425', '000568', '000625', '000651', '000661',
            '000703', '000708', '000725', '000768', '000776',
            '000783', '000786', '000858', '000876', '000938',
            '000961', '000977', '001979', '002001', '002007',
            '002008', '002027', '002032', '002049', '002050',
            '002129', '002142', '202004', '002230', '002236',
            '002241', '002271', '002304', '002311', '002352',
            '002410', '002415', '002475', '002594', '002600',
            '002601', '002602', '002607', '002714', '002812',
            '002821', '002841', '002920', '003816',
        ]
        return default_stocks
    
    def get_stock_data(self, stock_code, start_date, end_date):
        """
        获取股票历史数据
        """
        try:
            df = ef.stock.get_quote_history(
                stock_code,
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
            return None
    
    def is_st_stock(self, stock_code, date):
        """
        判断是否为ST股票（简化版本）
        """
        try:
            stock_name = ef.stock.get_base_info(stock_code)
            if stock_name is not None and len(stock_name) > 0:
                name = str(stock_name.iloc[0].get('股票名称', '')) if len(stock_name) > 0 else ''
                if 'ST' in name or '*ST' in name:
                    return True
            return False
        except:
            return False
    
    def is_new_stock(self, stock_code, date, days=90):
        """
        判断是否为次新股（上市不足指定天数）
        """
        try:
            df = self.get_stock_data(stock_code, date - timedelta(days=days*2), date)
            if df is None or len(df) < days:
                return True
            return False
        except:
            return True


# --------------------------------------------------------------------------------
# 3. 因子数据获取与处理
# --------------------------------------------------------------------------------

def get_period_dates(period, start_date, end_date):
    """
    获取周期日期列表
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    
    if period == '1M':
        freq = 'MS'
    elif period == '2M':
        freq = '2MS'
    elif period == '3M':
        freq = 'QS'
    else:
        freq = 'MS'
    
    period_dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    date_list = [d.strftime('%Y-%m-%d') for d in period_dates]
    
    return date_list


def calculate_all_factors(df):
    """
    计算所有因子
    """
    if df is None or len(df) < 120:
        return None
    
    close = df['close'].values
    open_price = df['open'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    amount = df['amount'].values
    
    returns = np.diff(close) / close[:-1]
    returns = np.insert(returns, 0, 0)
    
    factors = {}
    
    try:
        factors['DAVOL5'] = FactorCalculator.calculate_std(volume, 5)[-1] / (FactorCalculator.calculate_std(volume, 10)[-1] + 1e-10)
    except:
        factors['DAVOL5'] = 0
    
    try:
        factors['VOSC'] = FactorCalculator.calculate_vosc(volume, 12, 26)[-1]
    except:
        factors['VOSC'] = 0
    
    try:
        factors['momentum'] = FactorCalculator.calculate_momentum(close, 20)[-1]
    except:
        factors['momentum'] = 0
    
    try:
        factors['Kurtosis60'] = FactorCalculator.calculate_kurtosis(returns, 60)[-1]
    except:
        factors['Kurtosis60'] = 0
    
    try:
        factors['Kurtosis20'] = FactorCalculator.calculate_kurtosis(returns, 20)[-1]
    except:
        factors['Kurtosis20'] = 0
    
    try:
        factors['Kurtosis120'] = FactorCalculator.calculate_kurtosis(returns, 120)[-1]
    except:
        factors['Kurtosis120'] = 0
    
    try:
        factors['Skewness60'] = FactorCalculator.calculate_skewness(returns, 60)[-1]
    except:
        factors['Skewness60'] = 0
    
    try:
        factors['Skewness20'] = FactorCalculator.calculate_skewness(returns, 20)[-1]
    except:
        factors['Skewness20'] = 0
    
    try:
        factors['MAWVAD'] = FactorCalculator.calculate_wvad(close, open_price, high, low, volume, 24)[-1]
    except:
        factors['MAWVAD'] = 0
    
    try:
        vol_returns = np.diff(volume) / (volume[:-1] + 1e-10)
        vol_returns = np.insert(vol_returns, 0, 0)
        factors['turnover_volatility'] = np.std(vol_returns[-20:]) if len(vol_returns) >= 20 else 0
    except:
        factors['turnover_volatility'] = 0
    
    try:
        factors['Variance20'] = np.var(returns[-20:]) if len(returns) >= 20 else 0
    except:
        factors['Variance20'] = 0
    
    try:
        factors['MASS'] = FactorCalculator.calculate_mass_index(high, low, 25)[-1]
    except:
        factors['MASS'] = 0
    
    try:
        _, _, vmacd = FactorCalculator.calculate_vmacd(volume, 12, 26, 9)
        factors['VMACD'] = vmacd[-1] if len(vmacd) > 0 else 0
    except:
        factors['VMACD'] = 0
    
    try:
        atr6 = FactorCalculator.calculate_atr(high, low, close, 6)
        factors['ATR6'] = atr6[-1] if len(atr6) > 0 else 0
    except:
        factors['ATR6'] = 0
    
    try:
        factors['MFI14'] = FactorCalculator.calculate_mfi(high, low, close, volume, 14)[-1]
    except:
        factors['MFI14'] = 0
    
    try:
        factors['CR20'] = FactorCalculator.calculate_cr(high, low, close, 20)[-1]
    except:
        factors['CR20'] = 0
    
    try:
        factors['ATR14'] = FactorCalculator.calculate_atr(high, low, close, 14)[-1]
    except:
        factors['ATR14'] = 0
    
    try:
        factors['money_flow_20'] = np.sum(amount[-20:]) if len(amount) >= 20 else 0
    except:
        factors['money_flow_20'] = 0
    
    try:
        factors['earnings_yield'] = 0.05
    except:
        factors['earnings_yield'] = 0
    
    try:
        factors['circulating_market_cap'] = amount[-1] / (df['turnover'].iloc[-1] / 100 + 1e-10) if 'turnover' in df.columns else 1e10
    except:
        factors['circulating_market_cap'] = 1e10
    
    try:
        factors['book_to_price_ratio'] = 0.8
    except:
        factors['book_to_price_ratio'] = 0.8
    
    try:
        factors['natural_log_of_market_cap'] = np.log(factors['circulating_market_cap'] + 1)
    except:
        factors['natural_log_of_market_cap'] = 20
    
    try:
        factors['cube_of_size'] = (factors['circulating_market_cap'] / 1e9) ** (1/3)
    except:
        factors['cube_of_size'] = 10
    
    try:
        factors['financial_assets'] = 0.3
    except:
        factors['financial_assets'] = 0.3
    
    try:
        vema5 = FactorCalculator.calculate_ema(volume, 5)
        factors['VEMA5'] = vema5[-1] if len(vema5) > 0 else 0
    except:
        factors['VEMA5'] = 0
    
    try:
        factors['PSY'] = FactorCalculator.calculate_psy(close, 12)[-1]
    except:
        factors['PSY'] = 50
    
    try:
        factors['daily_standard_deviation'] = np.std(returns[-20:]) if len(returns) >= 20 else 0
    except:
        factors['daily_standard_deviation'] = 0
    
    try:
        vpt = FactorCalculator.calculate_vpt(close, volume)
        factors['single_day_VPT_12'] = vpt[-1] - vpt[-13] if len(vpt) >= 13 else 0
        factors['single_day_VPT'] = vpt[-1] if len(vpt) > 0 else 0
    except:
        factors['single_day_VPT_12'] = 0
        factors['single_day_VPT'] = 0
    
    try:
        factors['ROC120'] = FactorCalculator.calculate_roc(close, 120)[-1]
    except:
        factors['ROC120'] = 0
    
    try:
        factors['BIAS60'] = FactorCalculator.calculate_bias(close, 60)[-1]
    except:
        factors['BIAS60'] = 0
    
    try:
        factors['price_no_fq'] = close[-1]
    except:
        factors['price_no_fq'] = 0
    
    try:
        aroon_up, aroon_down = FactorCalculator.calculate_arron(high, low, 25)
        factors['arron_down_25'] = aroon_down[-1] if len(aroon_down) > 0 else 50
        factors['arron_up_25'] = aroon_up[-1] if len(aroon_up) > 0 else 50
    except:
        factors['arron_down_25'] = 50
        factors['arron_up_25'] = 50
    
    try:
        if len(close) >= 20:
            factors['Rank1M'] = (close[-1] - np.min(close[-20:])) / (np.max(close[-20:]) - np.min(close[-20:]) + 1e-10)
        else:
            factors['Rank1M'] = 0.5
    except:
        factors['Rank1M'] = 0.5
    
    try:
        if len(close) >= 250:
            factors['fifty_two_week_close_rank'] = (close[-1] - np.min(close[-250:])) / (np.max(close[-250:]) - np.min(close[-250:]) + 1e-10)
        else:
            factors['fifty_two_week_close_rank'] = 0.5
    except:
        factors['fifty_two_week_close_rank'] = 0.5
    
    try:
        factors['bear_power'] = (low[-1] - FactorCalculator.calculate_ema(close, 13)[-1]) / close[-1] if close[-1] > 0 else 0
    except:
        factors['bear_power'] = 0
    
    try:
        factors['liquidity'] = np.mean(amount[-20:]) / np.mean(amount[-60:]) if len(amount) >= 60 and np.mean(amount[-60:]) > 0 else 1
    except:
        factors['liquidity'] = 1
    
    try:
        factors['WVAD'] = FactorCalculator.calculate_wvad(close, open_price, high, low, volume, 24)[-1]
    except:
        factors['WVAD'] = 0
    
    try:
        dif, dea, macd = FactorCalculator.calculate_macd(close, 12, 26, 9)
        factors['VDIFF'] = dif[-1] if len(dif) > 0 else 0
    except:
        factors['VDIFF'] = 0
    
    try:
        factors['leverage'] = 1.5
    except:
        factors['leverage'] = 1.5
    
    try:
        factors['sales_to_price_ratio'] = 0.5
    except:
        factors['sales_to_price_ratio'] = 0.5
    
    try:
        factors['cash_flow_to_price_ratio'] = 0.1
    except:
        factors['cash_flow_to_price_ratio'] = 0.1
    
    try:
        factors['interest_free_current_liability'] = 0.3
    except:
        factors['interest_free_current_liability'] = 0.3
    
    # ========== 新增因子 ==========
    
    # KDJ指标
    try:
        k, d, j = FactorCalculator.calculate_kdj(high, low, close, 9, 3, 3)
        factors['KDJ_K'] = k[-1] if len(k) > 0 else 50
        factors['KDJ_D'] = d[-1] if len(d) > 0 else 50
        factors['KDJ_J'] = j[-1] if len(j) > 0 else 50
    except:
        factors['KDJ_K'] = 50
        factors['KDJ_D'] = 50
        factors['KDJ_J'] = 50
    
    # CCI指标
    try:
        cci = FactorCalculator.calculate_cci(high, low, close, 14)
        factors['CCI14'] = cci[-1] if len(cci) > 0 else 0
    except:
        factors['CCI14'] = 0
    
    # OBV指标
    try:
        obv = FactorCalculator.calculate_obv(close, volume)
        factors['OBV'] = obv[-1] if len(obv) > 0 else 0
        factors['OBV_MA5'] = np.mean(obv[-5:]) if len(obv) >= 5 else 0
    except:
        factors['OBV'] = 0
        factors['OBV_MA5'] = 0
    
    # WR威廉指标
    try:
        wr = FactorCalculator.calculate_wr(high, low, close, 14)
        factors['WR14'] = wr[-1] if len(wr) > 0 else 50
    except:
        factors['WR14'] = 50
    
    # DMI指标
    try:
        plus_di, minus_di, dx, adx = FactorCalculator.calculate_dmi(high, low, close, 14)
        factors['DMI_PLUS_DI'] = plus_di[-1] if len(plus_di) > 0 else 0
        factors['DMI_MINUS_DI'] = minus_di[-1] if len(minus_di) > 0 else 0
        factors['DMI_DX'] = dx[-1] if len(dx) > 0 else 0
        factors['DMI_ADX'] = adx[-1] if len(adx) > 0 else 0
    except:
        factors['DMI_PLUS_DI'] = 0
        factors['DMI_MINUS_DI'] = 0
        factors['DMI_DX'] = 0
        factors['DMI_ADX'] = 0
    
    # VWAP
    try:
        vwap = FactorCalculator.calculate_vwap(high, low, close, volume)
        factors['VWAP'] = vwap[-1] if len(vwap) > 0 else close[-1]
        factors['VWAP_DIFF'] = (close[-1] - vwap[-1]) / (vwap[-1] + 1e-10) if len(vwap) > 0 else 0
    except:
        factors['VWAP'] = close[-1] if len(close) > 0 else 0
        factors['VWAP_DIFF'] = 0
    
    # 布林带宽度
    try:
        bb_width = FactorCalculator.calculate_bollinger_width(close, 20, 2)
        factors['BB_WIDTH'] = bb_width[-1] if len(bb_width) > 0 else 0
    except:
        factors['BB_WIDTH'] = 0
    
    # 价格相对位置
    try:
        price_pos = FactorCalculator.calculate_price_position(close, 20)
        factors['PRICE_POSITION_20'] = price_pos[-1] if len(price_pos) > 0 else 0.5
    except:
        factors['PRICE_POSITION_20'] = 0.5
    
    try:
        price_pos_60 = FactorCalculator.calculate_price_position(close, 60)
        factors['PRICE_POSITION_60'] = price_pos_60[-1] if len(price_pos_60) > 0 else 0.5
    except:
        factors['PRICE_POSITION_60'] = 0.5
    
    # 波动率比率
    try:
        vol_ratio = FactorCalculator.calculate_volatility_ratio(close, 5, 20)
        factors['VOLATILITY_RATIO'] = vol_ratio[-1] if len(vol_ratio) > 0 else 1
    except:
        factors['VOLATILITY_RATIO'] = 1
    
    # 量比
    try:
        volume_ratio = FactorCalculator.calculate_volume_ratio(volume, 5)
        factors['VOLUME_RATIO_5'] = volume_ratio[-1] if len(volume_ratio) > 0 else 1
    except:
        factors['VOLUME_RATIO_5'] = 1
    
    # 趋势强度
    try:
        trend, r_sq = FactorCalculator.calculate_trend_strength(close, 20)
        factors['TREND_STRENGTH'] = trend[-1] if len(trend) > 0 else 0
        factors['TREND_R_SQUARE'] = r_sq[-1] if len(r_sq) > 0 else 0
    except:
        factors['TREND_STRENGTH'] = 0
        factors['TREND_R_SQUARE'] = 0
    
    # RSI多周期
    try:
        rsi6 = FactorCalculator.calculate_rsi(close, 6)
        factors['RSI6'] = rsi6[-1] if len(rsi6) > 0 else 50
    except:
        factors['RSI6'] = 50
    
    try:
        rsi14 = FactorCalculator.calculate_rsi(close, 14)
        factors['RSI14'] = rsi14[-1] if len(rsi14) > 0 else 50
    except:
        factors['RSI14'] = 50
    
    try:
        rsi24 = FactorCalculator.calculate_rsi(close, 24)
        factors['RSI24'] = rsi24[-1] if len(rsi24) > 0 else 50
    except:
        factors['RSI24'] = 50
    
    # MACD详细
    try:
        dif, dea, macd = FactorCalculator.calculate_macd(close, 12, 26, 9)
        factors['MACD_DIF'] = dif[-1] if len(dif) > 0 else 0
        factors['MACD_DEA'] = dea[-1] if len(dea) > 0 else 0
        factors['MACD_HIST'] = macd[-1] if len(macd) > 0 else 0
    except:
        factors['MACD_DIF'] = 0
        factors['MACD_DEA'] = 0
        factors['MACD_HIST'] = 0
    
    # ADL累积派发线
    try:
        adl = FactorCalculator.calculate_adl(high, low, close, volume)
        factors['ADL'] = adl[-1] if len(adl) > 0 else 0
    except:
        factors['ADL'] = 0
    
    # CMF
    try:
        cmf = FactorCalculator.calculate_cm_f(close, volume, 20)
        factors['CMF'] = cmf[-1] if len(cmf) > 0 else 0
    except:
        factors['CMF'] = 0
    
    # TRIX
    try:
        trix = FactorCalculator.calculate_trix(close, 14)
        factors['TRIX'] = trix[-1] if len(trix) > 0 else 0
    except:
        factors['TRIX'] = 0
    
    # UOS终极指标
    try:
        uos = FactorCalculator.calculate_uos(high, low, close, 7, 14, 28)
        factors['UOS'] = uos[-1] if len(uos) > 0 else 50
    except:
        factors['UOS'] = 50
    
    # DPO
    try:
        dpo = FactorCalculator.calculate_dpo(close, 20)
        factors['DPO'] = dpo[-1] if len(dpo) > 0 else 0
    except:
        factors['DPO'] = 0
    
    # MOM动量
    try:
        mom = FactorCalculator.calculate_mom(close, 10)
        factors['MOM10'] = mom[-1] if len(mom) > 0 else 0
    except:
        factors['MOM10'] = 0
    
    try:
        mom20 = FactorCalculator.calculate_mom(close, 20)
        factors['MOM20'] = mom20[-1] if len(mom20) > 0 else 0
    except:
        factors['MOM20'] = 0
    
    # ROC多周期
    try:
        roc5 = FactorCalculator.calculate_roc(close, 5)
        factors['ROC5'] = roc5[-1] if len(roc5) > 0 else 0
    except:
        factors['ROC5'] = 0
    
    try:
        roc10 = FactorCalculator.calculate_roc(close, 10)
        factors['ROC10'] = roc10[-1] if len(roc10) > 0 else 0
    except:
        factors['ROC10'] = 0
    
    try:
        roc20 = FactorCalculator.calculate_roc(close, 20)
        factors['ROC20'] = roc20[-1] if len(roc20) > 0 else 0
    except:
        factors['ROC20'] = 0
    
    # 振幅
    try:
        amp = FactorCalculator.calculate_amplitude(high, low, close, 20)
        factors['AMPLITUDE_20'] = amp[-1] if len(amp) > 0 else 0
    except:
        factors['AMPLITUDE_20'] = 0
    
    # 成交量趋势
    try:
        vol_trend = FactorCalculator.calculate_volume_trend(volume, 10)
        factors['VOLUME_TREND'] = vol_trend[-1] if len(vol_trend) > 0 else 1
    except:
        factors['VOLUME_TREND'] = 1
    
    # 量价相关性
    try:
        pv_corr = FactorCalculator.calculate_price_volume_corr(close, volume, 20)
        factors['PRICE_VOLUME_CORR'] = pv_corr[-1] if len(pv_corr) > 0 else 0
    except:
        factors['PRICE_VOLUME_CORR'] = 0
    
    # 最大回撤
    try:
        max_dd = FactorCalculator.calculate_max_drawdown(close, 60)
        factors['MAX_DRAWDOWN_60'] = max_dd[-1] if len(max_dd) > 0 else 0
    except:
        factors['MAX_DRAWDOWN_60'] = 0
    
    # 类夏普比率
    try:
        sharpe = FactorCalculator.calculate_sharpe_like(close, 20)
        factors['SHARPE_LIKE'] = sharpe[-1] if len(sharpe) > 0 else 0
    except:
        factors['SHARPE_LIKE'] = 0
    
    # 类索提诺比率
    try:
        sortino = FactorCalculator.calculate_sortino_like(close, 20)
        factors['SORTINO_LIKE'] = sortino[-1] if len(sortino) > 0 else 0
    except:
        factors['SORTINO_LIKE'] = 0
    
    # 类卡尔马比率
    try:
        calmar = FactorCalculator.calculate_calmar_like(close, 60)
        factors['CALMAR_LIKE'] = calmar[-1] if len(calmar) > 0 else 0
    except:
        factors['CALMAR_LIKE'] = 0
    
    # BIAS多周期
    try:
        bias5 = FactorCalculator.calculate_bias(close, 5)
        factors['BIAS5'] = bias5[-1] if len(bias5) > 0 else 0
    except:
        factors['BIAS5'] = 0
    
    try:
        bias10 = FactorCalculator.calculate_bias(close, 10)
        factors['BIAS10'] = bias10[-1] if len(bias10) > 0 else 0
    except:
        factors['BIAS10'] = 0
    
    try:
        bias20 = FactorCalculator.calculate_bias(close, 20)
        factors['BIAS20'] = bias20[-1] if len(bias20) > 0 else 0
    except:
        factors['BIAS20'] = 0
    
    # ATR多周期
    try:
        atr10 = FactorCalculator.calculate_atr(high, low, close, 10)
        factors['ATR10'] = atr10[-1] if len(atr10) > 0 else 0
    except:
        factors['ATR10'] = 0
    
    try:
        atr20 = FactorCalculator.calculate_atr(high, low, close, 20)
        factors['ATR20'] = atr20[-1] if len(atr20) > 0 else 0
    except:
        factors['ATR20'] = 0
    
    # MA多周期
    try:
        ma5 = FactorCalculator.calculate_ma(close, 5)
        factors['MA5'] = ma5[-1] if len(ma5) > 0 else close[-1]
        factors['PRICE_MA5_RATIO'] = close[-1] / (ma5[-1] + 1e-10) - 1 if len(ma5) > 0 else 0
    except:
        factors['MA5'] = close[-1] if len(close) > 0 else 0
        factors['PRICE_MA5_RATIO'] = 0
    
    try:
        ma10 = FactorCalculator.calculate_ma(close, 10)
        factors['MA10'] = ma10[-1] if len(ma10) > 0 else close[-1]
        factors['PRICE_MA10_RATIO'] = close[-1] / (ma10[-1] + 1e-10) - 1 if len(ma10) > 0 else 0
    except:
        factors['MA10'] = close[-1] if len(close) > 0 else 0
        factors['PRICE_MA10_RATIO'] = 0
    
    try:
        ma20 = FactorCalculator.calculate_ma(close, 20)
        factors['MA20'] = ma20[-1] if len(ma20) > 0 else close[-1]
        factors['PRICE_MA20_RATIO'] = close[-1] / (ma20[-1] + 1e-10) - 1 if len(ma20) > 0 else 0
    except:
        factors['MA20'] = close[-1] if len(close) > 0 else 0
        factors['PRICE_MA20_RATIO'] = 0
    
    try:
        ma60 = FactorCalculator.calculate_ma(close, 60)
        factors['MA60'] = ma60[-1] if len(ma60) > 0 else close[-1]
        factors['PRICE_MA60_RATIO'] = close[-1] / (ma60[-1] + 1e-10) - 1 if len(ma60) > 0 else 0
    except:
        factors['MA60'] = close[-1] if len(close) > 0 else 0
        factors['PRICE_MA60_RATIO'] = 0
    
    # MA交叉信号
    try:
        ma5_val = FactorCalculator.calculate_ma(close, 5)[-1]
        ma10_val = FactorCalculator.calculate_ma(close, 10)[-1]
        ma20_val = FactorCalculator.calculate_ma(close, 20)[-1]
        factors['MA5_MA10_CROSS'] = 1 if ma5_val > ma10_val else -1
        factors['MA5_MA20_CROSS'] = 1 if ma5_val > ma20_val else -1
        factors['MA10_MA20_CROSS'] = 1 if ma10_val > ma20_val else -1
    except:
        factors['MA5_MA10_CROSS'] = 0
        factors['MA5_MA20_CROSS'] = 0
        factors['MA10_MA20_CROSS'] = 0
    
    # 换手率相关
    try:
        if 'turnover' in df.columns and len(df['turnover']) > 0:
            turnover = df['turnover'].values
            factors['TURNOVER_5'] = np.mean(turnover[-5:]) if len(turnover) >= 5 else 0
            factors['TURNOVER_20'] = np.mean(turnover[-20:]) if len(turnover) >= 20 else 0
        else:
            factors['TURNOVER_5'] = 0
            factors['TURNOVER_20'] = 0
    except:
        factors['TURNOVER_5'] = 0
        factors['TURNOVER_20'] = 0
    
    # 连续涨跌天数
    try:
        up_days = 0
        down_days = 0
        for i in range(len(returns) - 1, 0, -1):
            if returns[i] > 0:
                up_days += 1
            else:
                break
        for i in range(len(returns) - 1, 0, -1):
            if returns[i] < 0:
                down_days += 1
            else:
                break
        factors['CONSECUTIVE_UP'] = up_days
        factors['CONSECUTIVE_DOWN'] = down_days
    except:
        factors['CONSECUTIVE_UP'] = 0
        factors['CONSECUTIVE_DOWN'] = 0
    
    # 涨跌幅统计
    try:
        factors['UP_RATIO_20'] = np.sum(returns[-20:] > 0) / 20 if len(returns) >= 20 else 0.5
        factors['UP_RATIO_60'] = np.sum(returns[-60:] > 0) / 60 if len(returns) >= 60 else 0.5
    except:
        factors['UP_RATIO_20'] = 0.5
        factors['UP_RATIO_60'] = 0.5
    
    # 极端涨跌幅
    try:
        factors['MAX_RETURN_20'] = np.max(returns[-20:]) if len(returns) >= 20 else 0
        factors['MIN_RETURN_20'] = np.min(returns[-20:]) if len(returns) >= 20 else 0
    except:
        factors['MAX_RETURN_20'] = 0
        factors['MIN_RETURN_20'] = 0
    
    for key in factors:
        if np.isnan(factors[key]) or np.isinf(factors[key]):
            factors[key] = 0
    
    return factors


# --------------------------------------------------------------------------------
# 4. 主程序
# --------------------------------------------------------------------------------

def main():
    """
    主函数：数据下载、因子计算、模型训练
    """
    print("=" * 80)
    print("对探针法因子筛选多模型参数优化 - 本地版本")
    print("=" * 80)
    
    data_fetcher = DataFetcher()
    
    period = '2M'
    start_date = datetime(2015, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    date_list = get_period_dates(period, start_date, end_date)
    
    print(f"\n数据获取配置:")
    print(f"  周期: {period}")
    print(f"  开始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"  结束日期: {end_date.strftime('%Y-%m-%d')}")
    print(f"  调仓日期数: {len(date_list)}")
    
    DF = pd.DataFrame()
    
    lookback_days = 150
    
    for i, trade_date_str in enumerate(tqdm(date_list[:-1], desc='下载数据')):
        trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d')
        next_date_str = date_list[i + 1]
        next_date = datetime.strptime(next_date_str, '%Y-%m-%d')
        
        print(f"\n处理日期: {trade_date_str}")
        
        stock_list = data_fetcher.get_stock_list(trade_date)
        print(f"  股票数量: {len(stock_list)}")
        
        if not stock_list:
            continue
        
        factor_data_list = []
        
        for j, stock_code in enumerate(stock_list[:100]):
            try:
                data_start = trade_date - timedelta(days=lookback_days)
                df = data_fetcher.get_stock_data(stock_code, data_start, next_date)
                
                if df is None or len(df) < 120:
                    continue
                
                factors = calculate_all_factors(df)
                if factors is None:
                    continue
                
                df_period = df[(df['date'] >= trade_date) & (df['date'] < next_date)]
                if len(df_period) < 2:
                    continue
                
                pchg = df_period['close'].iloc[-1] / df_period['close'].iloc[0] - 1
                factors['pchg'] = pchg
                factors['trade_date'] = trade_date_str
                factors['stock_code'] = stock_code
                
                factor_data_list.append(factors)
                
                time.sleep(0.1)
                
            except Exception as e:
                continue
        
        if factor_data_list:
            df_batch = pd.DataFrame(factor_data_list)
            DF = pd.concat([DF, df_batch], ignore_index=True)
            print(f"  本批次有效股票: {len(factor_data_list)}")
        
        time.sleep(1)
    
    if len(DF) == 0:
        print("\n警告: 未获取到任何数据，请检查网络连接或数据源")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'train.csv')
    DF.to_csv(csv_path, index=False)
    print(f"\n数据已保存至: {csv_path}")
    print(f"总记录数: {len(DF)}")
    
    train_model(DF, script_dir)


def train_model(df, script_dir):
    """
    模型训练与特征筛选
    """
    print("\n" + "=" * 80)
    print("开始模型训练与因子筛选")
    print("=" * 80)
    
    df['label_class'] = (df['pchg'] > df.groupby('trade_date')['pchg'].transform('median')).astype(int)
    df['label_res'] = df.groupby('trade_date')['pchg'].transform(
        lambda s: (s.rank(method='first', ascending=True) - 1) / (len(s) - 1) if len(s) > 1 else 0.5
    )
    df['label_dir'] = (df['pchg'] > 0).astype(int)
    
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    
    exclude_cols = ['trade_date', 'pchg', 'label_class', 'label_res', 'label_dir', 'stock_code']
    feature_names = [col for col in df.columns if col not in exclude_cols]
    
    print(f"\n特征数量: {len(feature_names)}")
    print(f"特征列表: {feature_names}")
    
    train_df = df[df['trade_date'].dt.year < 2023].copy()
    test_df = df[df['trade_date'].dt.year >= 2023].copy()
    
    print(f"\n训练集大小: {len(train_df)}")
    print(f"测试集大小: {len(test_df)}")
    
    if len(train_df) < 100:
        print("训练数据不足，无法进行模型训练")
        return
    
    train_df = train_df.sort_values('trade_date')
    split_point = int(len(train_df) * 0.9)
    train_idx = train_df.index[:split_point]
    val_idx = train_df.index[split_point:]
    
    params_cls = {'objective': 'binary', 'metric': 'auc', 'seed': 42, 'verbose': -1}
    params_dir = {'objective': 'binary', 'metric': 'auc', 'seed': 42, 'verbose': -1}
    params_reg = {'objective': 'regression', 'metric': 'rmse', 'seed': 42, 'verbose': -1}
    
    print("\n开始增强探针法因子筛选...")
    N_ITER = 10
    N_NOISE = 10
    current_features = feature_names.copy()
    
    y_train_cls = df.loc[train_idx, 'label_class'].values
    y_val_cls = df.loc[val_idx, 'label_class'].values
    y_train_reg = df.loc[train_idx, 'label_res'].values
    y_val_reg = df.loc[val_idx, 'label_res'].values
    y_train_dir = df.loc[train_idx, 'label_dir'].values
    y_val_dir = df.loc[val_idx, 'label_dir'].values
    
    for iter_idx in range(1, N_ITER + 1):
        X_train_curr = df.loc[train_idx, current_features].values.astype('float32')
        X_val_curr = df.loc[val_idx, current_features].values.astype('float32')
        
        noise_train = np.random.randn(X_train_curr.shape[0], N_NOISE).astype('float32')
        noise_val = np.random.randn(X_val_curr.shape[0], N_NOISE).astype('float32')
        
        X_train_aug = np.hstack([X_train_curr, noise_train])
        X_val_aug = np.hstack([X_val_curr, noise_val])
        
        try:
            lgb_train_cls = lgb.Dataset(X_train_aug, y_train_cls)
            lgb_val_cls = lgb.Dataset(X_val_aug, y_val_cls, reference=lgb_train_cls)
            model_cls = lgb.train(params_cls, lgb_train_cls, valid_sets=[lgb_val_cls], 
                                  num_boost_round=100, callbacks=[lgb.log_evaluation(0)])
            
            lgb_train_reg = lgb.Dataset(X_train_aug, y_train_reg)
            lgb_val_reg = lgb.Dataset(X_val_aug, y_val_reg, reference=lgb_train_reg)
            model_reg = lgb.train(params_reg, lgb_train_reg, valid_sets=[lgb_val_reg],
                                  num_boost_round=100, callbacks=[lgb.log_evaluation(0)])
            
            lgb_train_dir = lgb.Dataset(X_train_aug, y_train_dir)
            lgb_val_dir = lgb.Dataset(X_val_aug, y_val_dir, reference=lgb_train_dir)
            model_dir = lgb.train(params_dir, lgb_train_dir, valid_sets=[lgb_val_dir],
                                  num_boost_round=100, callbacks=[lgb.log_evaluation(0)])
            
            imp_cls = model_cls.feature_importance(importance_type='gain')
            imp_reg = model_reg.feature_importance(importance_type='gain')
            imp_dir = model_dir.feature_importance(importance_type='gain')
            
            noise_imp_cls_max = np.max(imp_cls[-N_NOISE:])
            noise_imp_reg_max = np.max(imp_reg[-N_NOISE:])
            noise_imp_dir_max = np.max(imp_dir[-N_NOISE:])
            
            to_remove = []
            for idx, feat in enumerate(current_features):
                if (imp_cls[idx] < noise_imp_cls_max) and (imp_reg[idx] < noise_imp_reg_max) and (imp_dir[idx] < noise_imp_dir_max):
                    to_remove.append(feat)
            
            current_features = [f for f in current_features if f not in to_remove]
            print(f"轮次 {iter_idx}: 剩余特征 {len(current_features)}")
            
            if len(current_features) < 5:
                print("特征数量过少，停止筛选")
                break
                
        except Exception as e:
            print(f"轮次 {iter_idx} 训练失败: {e}")
            break
    
    df_selected_factors = pd.DataFrame(current_features, columns=['factor'])
    selected_path = os.path.join(script_dir, 'selected_factors.csv')
    df_selected_factors.to_csv(selected_path, index=False)
    print(f"\n筛选后的因子已保存至: {selected_path}")
    
    if len(current_features) < 3:
        print("筛选后特征数量不足，使用原始特征")
        current_features = feature_names
    
    print("\n训练最终模型...")
    X_train_final = df.loc[train_idx, current_features].values.astype('float32')
    X_val_final = df.loc[val_idx, current_features].values.astype('float32')
    
    try:
        lgb_train_cls_final = lgb.Dataset(X_train_final, y_train_cls)
        lgb_val_cls_final = lgb.Dataset(X_val_final, y_val_cls, reference=lgb_train_cls_final)
        model_cls_final = lgb.train(params_cls, lgb_train_cls_final, valid_sets=[lgb_val_cls_final], 
                                    num_boost_round=500, callbacks=[lgb.log_evaluation(0)])
        
        lgb_train_reg_final = lgb.Dataset(X_train_final, y_train_reg)
        lgb_val_reg_final = lgb.Dataset(X_val_final, y_val_reg, reference=lgb_train_reg_final)
        model_reg_final = lgb.train(params_reg, lgb_train_reg_final, valid_sets=[lgb_val_reg_final],
                                    num_boost_round=500, callbacks=[lgb.log_evaluation(0)])
        
        lgb_train_dir_final = lgb.Dataset(X_train_final, y_train_dir)
        lgb_val_dir_final = lgb.Dataset(X_val_final, y_val_dir, reference=lgb_train_dir_final)
        model_dir_final = lgb.train(params_dir, lgb_train_dir_final, valid_sets=[lgb_val_dir_final],
                                    num_boost_round=500, callbacks=[lgb.log_evaluation(0)])
        
        model_cls_path = os.path.join(script_dir, 'model_cls_final.pkl')
        model_reg_path = os.path.join(script_dir, 'model_reg_final.pkl')
        model_dir_path = os.path.join(script_dir, 'model_dir_final.pkl')
        
        with open(model_cls_path, 'wb') as f:
            pickle.dump(model_cls_final, f)
        with open(model_reg_path, 'wb') as f:
            pickle.dump(model_reg_final, f)
        with open(model_dir_path, 'wb') as f:
            pickle.dump(model_dir_final, f)
        
        print(f"\n模型已保存:")
        print(f"  分类模型: {model_cls_path}")
        print(f"  回归模型: {model_reg_path}")
        print(f"  方向模型: {model_dir_path}")
        
    except Exception as e:
        print(f"最终模型训练失败: {e}")
    
    print("\n" + "=" * 80)
    print("训练与保存完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
