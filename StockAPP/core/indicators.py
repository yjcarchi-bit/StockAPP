"""
技术指标库
==========
常用的技术分析指标计算函数

包含:
- 趋势指标: SMA, EMA, MACD, BOLL
- 动量指标: RSI, KDJ, CCI
- 波动指标: ATR, STD
- 成交量指标: OBV, VOL_MA
"""

from typing import Tuple, Optional, Union
import numpy as np
import pandas as pd


class Indicators:
    """
    技术指标计算类
    
    所有方法都是静态方法，可直接调用
    
    Example:
        >>> closes = np.array([10, 11, 12, 11, 13])
        >>> ma5 = Indicators.SMA(closes, 5)
        >>> macd, signal, hist = Indicators.MACD(closes)
    """
    
    @staticmethod
    def SMA(data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
        """
        简单移动平均线
        
        Args:
            data: 价格数据
            period: 周期
            
        Returns:
            SMA数组，前period-1个值为NaN
        """
        data = np.asarray(data, dtype=float)
        result = np.full_like(data, np.nan)
        
        if len(data) < period:
            return result
        
        cumsum = np.cumsum(data)
        cumsum = np.insert(cumsum, 0, 0)
        result[period-1:] = (cumsum[period:] - cumsum[:-period]) / period
        
        return result
    
    @staticmethod
    def EMA(data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
        """
        指数移动平均线
        
        Args:
            data: 价格数据
            period: 周期
            
        Returns:
            EMA数组
        """
        data = np.asarray(data, dtype=float)
        result = np.zeros_like(data)
        
        if len(data) == 0:
            return result
        
        alpha = 2 / (period + 1)
        result[0] = data[0]
        
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        
        return result
    
    @staticmethod
    def MACD(
        close: Union[np.ndarray, pd.Series],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        MACD指标
        
        Args:
            close: 收盘价数据
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            (DIF, DEA, MACD柱) 元组
        """
        close = np.asarray(close, dtype=float)
        
        ema_fast = Indicators.EMA(close, fast_period)
        ema_slow = Indicators.EMA(close, slow_period)
        
        dif = ema_fast - ema_slow
        dea = Indicators.EMA(dif, signal_period)
        macd_bar = 2 * (dif - dea)
        
        return dif, dea, macd_bar
    
    @staticmethod
    def BOLL(
        close: Union[np.ndarray, pd.Series],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        布林带
        
        Args:
            close: 收盘价数据
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            (中轨, 上轨, 下轨) 元组
        """
        close = np.asarray(close, dtype=float)
        
        middle = Indicators.SMA(close, period)
        std = Indicators.STD(close, period)
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return middle, upper, lower
    
    @staticmethod
    def STD(data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
        """
        滚动标准差
        
        Args:
            data: 数据
            period: 周期
            
        Returns:
            标准差数组
        """
        data = np.asarray(data, dtype=float)
        result = np.full_like(data, np.nan)
        
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            result[i] = np.std(data[i-period+1:i+1], ddof=0)
        
        return result
    
    @staticmethod
    def RSI(
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> np.ndarray:
        """
        相对强弱指标
        
        Args:
            close: 收盘价数据
            period: 周期
            
        Returns:
            RSI数组 (0-100)
        """
        close = np.asarray(close, dtype=float)
        
        if len(close) < period + 1:
            return np.full_like(close, 50.0)
        
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.zeros(len(close))
        avg_losses = np.zeros(len(close))
        
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        result = np.full(len(close), 50.0)
        
        for i in range(period + 1, len(close)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
            
            if avg_losses[i] == 0:
                result[i] = 100.0
            else:
                rs = avg_gains[i] / avg_losses[i]
                result[i] = 100 - (100 / (1 + rs))
        
        return result
    
    @staticmethod
    def KDJ(
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        KDJ指标
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            n: RSV周期
            m1: K值平滑周期
            m2: D值平滑周期
            
        Returns:
            (K, D, J) 元组
        """
        high = np.asarray(high, dtype=float)
        low = np.asarray(low, dtype=float)
        close = np.asarray(close, dtype=float)
        
        rsv = np.zeros(len(close))
        
        for i in range(n - 1, len(close)):
            high_n = np.max(high[i-n+1:i+1])
            low_n = np.min(low[i-n+1:i+1])
            
            if high_n == low_n:
                rsv[i] = 50
            else:
                rsv[i] = (close[i] - low_n) / (high_n - low_n) * 100
        
        k = np.zeros(len(close))
        d = np.zeros(len(close))
        
        k[:n-1] = 50
        d[:n-1] = 50
        
        for i in range(n - 1, len(close)):
            k[i] = (m1 - 1) / m1 * k[i-1] + 1 / m1 * rsv[i]
            d[i] = (m2 - 1) / m2 * d[i-1] + 1 / m2 * k[i]
        
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def ATR(
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> np.ndarray:
        """
        平均真实波幅
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期
            
        Returns:
            ATR数组
        """
        high = np.asarray(high, dtype=float)
        low = np.asarray(low, dtype=float)
        close = np.asarray(close, dtype=float)
        
        if len(close) < period + 1:
            return np.zeros(len(close))
        
        tr = np.zeros(len(close))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr[i] = max(tr1, tr2, tr3)
        
        atr = np.zeros(len(close))
        atr[period-1] = np.mean(tr[:period])
        
        for i in range(period, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    @staticmethod
    def OBV(
        close: Union[np.ndarray, pd.Series],
        volume: Union[np.ndarray, pd.Series]
    ) -> np.ndarray:
        """
        能量潮指标
        
        Args:
            close: 收盘价
            volume: 成交量
            
        Returns:
            OBV数组
        """
        close = np.asarray(close, dtype=float)
        volume = np.asarray(volume, dtype=float)
        
        obv = np.zeros(len(close))
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        
        return obv
    
    @staticmethod
    def VOL_MA(
        volume: Union[np.ndarray, pd.Series],
        short_period: int = 5,
        long_period: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        成交量均线
        
        Args:
            volume: 成交量
            short_period: 短周期
            long_period: 长周期
            
        Returns:
            (短期均线, 长期均线) 元组
        """
        volume = np.asarray(volume, dtype=float)
        
        ma_short = Indicators.SMA(volume, short_period)
        ma_long = Indicators.SMA(volume, long_period)
        
        return ma_short, ma_long
    
    @staticmethod
    def CCI(
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        period: int = 20
    ) -> np.ndarray:
        """
        顺势指标
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期
            
        Returns:
            CCI数组
        """
        high = np.asarray(high, dtype=float)
        low = np.asarray(low, dtype=float)
        close = np.asarray(close, dtype=float)
        
        tp = (high + low + close) / 3
        
        result = np.full_like(close, np.nan)
        
        for i in range(period - 1, len(close)):
            tp_ma = np.mean(tp[i-period+1:i+1])
            md = np.mean(np.abs(tp[i-period+1:i+1] - tp_ma))
            
            if md != 0:
                result[i] = (tp[i] - tp_ma) / (0.015 * md)
        
        return result
    
    @staticmethod
    def WILLR(
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> np.ndarray:
        """
        威廉指标
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期
            
        Returns:
            Williams %R数组
        """
        high = np.asarray(high, dtype=float)
        low = np.asarray(low, dtype=float)
        close = np.asarray(close, dtype=float)
        
        result = np.full_like(close, np.nan)
        
        for i in range(period - 1, len(close)):
            high_n = np.max(high[i-period+1:i+1])
            low_n = np.min(low[i-period+1:i+1])
            
            if high_n == low_n:
                result[i] = -50
            else:
                result[i] = (high_n - close[i]) / (high_n - low_n) * -100
        
        return result
    
    @staticmethod
    def DMI(
        high: Union[np.ndarray, pd.Series],
        low: Union[np.ndarray, pd.Series],
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        动向指标
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期
            
        Returns:
            (PDI, MDI, ADX) 元组
        """
        high = np.asarray(high, dtype=float)
        low = np.asarray(low, dtype=float)
        close = np.asarray(close, dtype=float)
        
        plus_dm = np.zeros(len(close))
        minus_dm = np.zeros(len(close))
        tr = np.zeros(len(close))
        
        for i in range(1, len(close)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0
            
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr[i] = max(tr1, tr2, tr3)
        
        atr = Indicators.ATR(high, low, close, period)
        
        smooth_plus_dm = Indicators.EMA(plus_dm, period)
        smooth_minus_dm = Indicators.EMA(minus_dm, period)
        
        pdi = np.zeros(len(close))
        mdi = np.zeros(len(close))
        
        for i in range(len(close)):
            if atr[i] != 0:
                pdi[i] = smooth_plus_dm[i] / atr[i] * 100
                mdi[i] = smooth_minus_dm[i] / atr[i] * 100
        
        dx = np.zeros(len(close))
        for i in range(len(close)):
            if pdi[i] + mdi[i] != 0:
                dx[i] = abs(pdi[i] - mdi[i]) / (pdi[i] + mdi[i]) * 100
        
        adx = Indicators.EMA(dx, period)
        
        return pdi, mdi, adx
    
    @staticmethod
    def MOMENTUM(
        close: Union[np.ndarray, pd.Series],
        period: int = 10
    ) -> np.ndarray:
        """
        动量指标
        
        Args:
            close: 收盘价
            period: 周期
            
        Returns:
            动量数组
        """
        close = np.asarray(close, dtype=float)
        result = np.full_like(close, np.nan)
        
        for i in range(period, len(close)):
            result[i] = close[i] - close[i-period]
        
        return result
    
    @staticmethod
    def ROC(
        close: Union[np.ndarray, pd.Series],
        period: int = 10
    ) -> np.ndarray:
        """
        变动率指标
        
        Args:
            close: 收盘价
            period: 周期
            
        Returns:
            ROC数组（百分比）
        """
        close = np.asarray(close, dtype=float)
        result = np.full_like(close, np.nan)
        
        for i in range(period, len(close)):
            if close[i-period] != 0:
                result[i] = (close[i] - close[i-period]) / close[i-period] * 100
        
        return result
    
    @staticmethod
    def TRIX(
        close: Union[np.ndarray, pd.Series],
        period: int = 14
    ) -> np.ndarray:
        """
        三重指数平滑移动平均
        
        Args:
            close: 收盘价
            period: 周期
            
        Returns:
            TRIX数组
        """
        close = np.asarray(close, dtype=float)
        
        ema1 = Indicators.EMA(close, period)
        ema2 = Indicators.EMA(ema1, period)
        ema3 = Indicators.EMA(ema2, period)
        
        result = np.full_like(close, np.nan)
        
        for i in range(1, len(close)):
            if ema3[i-1] != 0:
                result[i] = (ema3[i] - ema3[i-1]) / ema3[i-1] * 100
        
        return result
    
    @staticmethod
    def linear_regression_slope(
        data: Union[np.ndarray, pd.Series],
        period: int = 20
    ) -> np.ndarray:
        """
        线性回归斜率
        
        Args:
            data: 数据
            period: 回归周期
            
        Returns:
            斜率数组
        """
        data = np.asarray(data, dtype=float)
        result = np.full_like(data, np.nan)
        
        x = np.arange(period)
        
        for i in range(period - 1, len(data)):
            y = data[i-period+1:i+1]
            
            if not np.any(np.isnan(y)):
                slope, _ = np.polyfit(x, y, 1)
                result[i] = slope
        
        return result
    
    @staticmethod
    def r_squared(
        data: Union[np.ndarray, pd.Series],
        period: int = 20
    ) -> np.ndarray:
        """
        R²决定系数
        
        Args:
            data: 数据
            period: 计算周期
            
        Returns:
            R²数组
        """
        data = np.asarray(data, dtype=float)
        result = np.full_like(data, np.nan)
        
        x = np.arange(period)
        
        for i in range(period - 1, len(data)):
            y = data[i-period+1:i+1]
            
            if not np.any(np.isnan(y)):
                slope, intercept = np.polyfit(x, y, 1)
                y_pred = slope * x + intercept
                
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                
                if ss_tot != 0:
                    result[i] = 1 - ss_res / ss_tot
        
        return result
    
    @staticmethod
    def annualized_return(
        close: Union[np.ndarray, pd.Series],
        period: int = 20,
        trading_days: int = 250
    ) -> np.ndarray:
        """
        年化收益率（基于线性回归斜率）
        
        Args:
            close: 收盘价
            period: 计算周期
            trading_days: 年交易日数
            
        Returns:
            年化收益率数组
        """
        close = np.asarray(close, dtype=float)
        slopes = Indicators.linear_regression_slope(np.log(close), period)
        
        result = np.full_like(close, np.nan)
        
        for i in range(len(close)):
            if not np.isnan(slopes[i]):
                result[i] = np.exp(slopes[i] * trading_days) - 1
        
        return result
