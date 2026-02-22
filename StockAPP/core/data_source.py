"""
数据源模块
==========
统一的数据获取接口，封装efinance API，支持本地缓存

特性:
- 统一的股票/ETF/基金数据接口
- 自动本地缓存
- 批量数据获取
- 异常重试机制
"""

import os
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import efinance as ef
except ImportError:
    raise ImportError("请安装efinance: pip install efinance")


@dataclass
class DataConfig:
    """数据配置"""
    cache_dir: str = ""
    cache_expire_hours: int = 4  # 缓存4小时，确保数据相对新鲜
    retry_times: int = 3
    retry_delay: float = 1.0
    request_delay: float = 0.3


class DataSource:
    """
    统一数据源
    
    封装efinance API，提供统一的股票/ETF/基金数据获取接口
    
    Example:
        >>> ds = DataSource()
        >>> df = ds.get_etf_history("510300", "2023-01-01", "2024-01-01")
        >>> quote = ds.get_realtime_quote("510300")
    """
    
    ETF_TYPE = "etf"
    STOCK_TYPE = "stock"
    FUND_TYPE = "fund"
    INDEX_TYPE = "index"
    
    def __init__(self, config: Optional[DataConfig] = None):
        """
        初始化数据源
        
        Args:
            config: 数据配置，为None时使用默认配置
        """
        self.config = config or DataConfig()
        
        if not self.config.cache_dir:
            self.config.cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "data", ".cache"
            )
        
        os.makedirs(self.config.cache_dir, exist_ok=True)
        
        self._last_request_time = 0
        self._request_interval = self.config.request_delay
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.config.cache_dir, f"{key_hash}.pkl")
    
    def _load_cache(self, key: str) -> Optional[pd.DataFrame]:
        """
        加载缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的DataFrame，如果不存在或过期则返回None
        """
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            cache_time = os.path.getmtime(cache_path)
            expire_seconds = self.config.cache_expire_hours * 3600
            
            if time.time() - cache_time > expire_seconds:
                return None
            
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def _save_cache(self, key: str, data: pd.DataFrame) -> None:
        """
        保存数据到缓存
        
        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception:
            pass
    
    def _rate_limit(self) -> None:
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            time.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _retry_request(self, func, *args, **kwargs) -> Any:
        """
        带重试的请求
        
        Args:
            func: 请求函数
            *args, **kwargs: 函数参数
            
        Returns:
            请求结果
        """
        last_error = None
        
        for i in range(self.config.retry_times):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if i < self.config.retry_times - 1:
                    time.sleep(self.config.retry_delay * (i + 1))
        
        raise last_error
    
    def _parse_date(self, date: Union[str, datetime]) -> str:
        """解析日期为字符串格式"""
        if isinstance(date, datetime):
            return date.strftime("%Y%m%d")
        elif isinstance(date, str):
            return date.replace("-", "").replace("/", "")
        return str(date)
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "换手率": "turnover",
        }
        
        df = df.rename(columns=column_mapping)
        
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
        
        return df
    
    def get_history(
        self,
        code: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        data_type: str = "etf",
        klt: int = 101,
        fqt: int = 1,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取历史数据（通用接口）
        
        Args:
            code: 证券代码
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型 (etf/stock/fund/index)
            klt: K线类型 (101=日线, 102=周线, 103=月线)
            fqt: 复权类型 (0=不复权, 1=前复权, 2=后复权)
            use_cache: 是否使用缓存
            
        Returns:
            历史数据DataFrame，包含date, open, close, high, low, volume等列
        """
        start_str = self._parse_date(start_date)
        end_str = self._parse_date(end_date)
        
        cache_key = f"{code}_{start_str}_{end_str}_{data_type}_{klt}_{fqt}"
        
        if use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached
        
        try:
            df = self._retry_request(
                ef.stock.get_quote_history,
                code,
                beg=start_str,
                end=end_str,
                klt=klt,
                fqt=fqt
            )
            
            if df is None or len(df) == 0:
                return None
            
            df = self._standardize_columns(df)
            
            if use_cache:
                self._save_cache(cache_key, df)
            
            return df
            
        except Exception as e:
            print(f"获取{code}历史数据失败: {e}")
            return None
    
    def get_etf_history(
        self,
        code: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取ETF历史数据
        
        Args:
            code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
            
        Returns:
            历史数据DataFrame
        """
        return self.get_history(code, start_date, end_date, self.ETF_TYPE, use_cache=use_cache)
    
    def get_stock_history(
        self,
        code: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        fqt: int = 1,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fqt: 复权类型 (0=不复权, 1=前复权, 2=后复权)
            use_cache: 是否使用缓存
            
        Returns:
            历史数据DataFrame
        """
        return self.get_history(code, start_date, end_date, self.STOCK_TYPE, fqt=fqt, use_cache=use_cache)
    
    def get_index_history(
        self,
        code: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取指数历史数据
        
        Args:
            code: 指数代码 (如 "000300" 沪深300)
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
            
        Returns:
            历史数据DataFrame
        """
        return self.get_history(code, start_date, end_date, self.INDEX_TYPE, use_cache=use_cache)
    
    def get_realtime_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情
        
        Args:
            code: 证券代码
            
        Returns:
            实时行情字典
        """
        try:
            df = self._retry_request(
                ef.stock.get_quote_history,
                code,
                beg=(datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                end=datetime.now().strftime("%Y%m%d"),
                klt=101,
                fqt=1
            )
            
            if df is not None and len(df) > 0:
                row = df.iloc[-1]
                return {
                    "code": code,
                    "date": row.get("日期", ""),
                    "open": float(row.get("开盘", 0)),
                    "close": float(row.get("收盘", 0)),
                    "high": float(row.get("最高", 0)),
                    "low": float(row.get("最低", 0)),
                    "volume": float(row.get("成交量", 0)),
                    "amount": float(row.get("成交额", 0)),
                    "pct_change": float(row.get("涨跌幅", 0)),
                }
            return None
            
        except Exception as e:
            print(f"获取{code}实时行情失败: {e}")
            return None
    
    def get_latest_price(self, code: str) -> float:
        """
        获取最新价格
        
        Args:
            code: 证券代码
            
        Returns:
            最新价格
        """
        quote = self.get_realtime_quote(code)
        return quote["close"] if quote else 0.0
    
    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF列表
        
        Returns:
            ETF列表DataFrame
        """
        try:
            df = self._retry_request(ef.stock.get_base_info, "ETF")
            return df
        except Exception:
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        
        Returns:
            股票列表DataFrame
        """
        try:
            df = self._retry_request(ef.stock.get_base_info, "A股")
            return df
        except Exception:
            return pd.DataFrame()
    
    def batch_get_history(
        self,
        codes: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        data_type: str = "etf",
        show_progress: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取历史数据
        
        Args:
            codes: 证券代码列表
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
            show_progress: 是否显示进度
            
        Returns:
            字典，键为代码，值为DataFrame
        """
        results = {}
        total = len(codes)
        
        for i, code in enumerate(codes):
            if show_progress:
                print(f"获取数据 [{i+1}/{total}]: {code}")
            
            df = self.get_history(code, start_date, end_date, data_type)
            if df is not None:
                results[code] = df
        
        return results
    
    def clear_cache(self, older_than_hours: int = 0) -> int:
        """
        清理缓存
        
        Args:
            older_than_hours: 清理多少小时前的缓存，0表示清理全部
            
        Returns:
            清理的文件数量
        """
        count = 0
        cache_dir = Path(self.config.cache_dir)
        
        for cache_file in cache_dir.glob("*.pkl"):
            if older_than_hours == 0:
                cache_file.unlink()
                count += 1
            else:
                cache_time = cache_file.stat().st_mtime
                if time.time() - cache_time > older_than_hours * 3600:
                    cache_file.unlink()
                    count += 1
        
        return count
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小（字节）
        
        Returns:
            缓存总大小
        """
        total_size = 0
        cache_dir = Path(self.config.cache_dir)
        
        for cache_file in cache_dir.glob("*.pkl"):
            total_size += cache_file.stat().st_size
        
        return total_size
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        cache_dir = Path(self.config.cache_dir)
        files = list(cache_dir.glob("*.pkl"))
        
        return {
            "cache_dir": str(cache_dir),
            "file_count": len(files),
            "total_size_mb": self.get_cache_size() / (1024 * 1024),
            "expire_hours": self.config.cache_expire_hours,
        }
