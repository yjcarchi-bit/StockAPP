"""
数据源模块
==========
统一的数据获取接口，封装efinance API，支持本地缓存

特性:
- 统一的股票/ETF/基金数据接口
- 自动本地缓存
- 批量数据获取
- 异常重试机制
- 支持akshare_proxy_patch代理补丁（可选）
- 支持故障转移机制（efinance失败时自动切换akshare）
"""

import os
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import efinance as ef
except ImportError:
    raise ImportError("请安装efinance: pip install efinance")

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

try:
    import akshare_proxy_patch
    HAS_AKSHARE_PROXY_PATCH = True
except ImportError:
    HAS_AKSHARE_PROXY_PATCH = False


def _load_project_env() -> None:
    """从项目根目录加载 .env（不覆盖已存在环境变量）"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        
        if not key:
            continue
        
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        
        os.environ.setdefault(key, value)


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


_load_project_env()


@dataclass
class DataConfig:
    """数据配置"""
    cache_dir: str = ""
    cache_expire_hours: int = field(default_factory=lambda: _env_int("DATA_CACHE_EXPIRE_HOURS", 4))  # 缓存4小时，确保数据相对新鲜
    retry_times: int = 3
    retry_delay: float = 1.0
    request_delay: float = 0.3
    proxy_host: str = field(default_factory=lambda: os.getenv("AKSHARE_PROXY_HOST", "101.201.173.125"))
    proxy_auth_code: str = field(default_factory=lambda: os.getenv("PROXY_AUTH_CODE", ""))
    proxy_timeout: int = field(default_factory=lambda: _env_int("AKSHARE_PROXY_TIMEOUT", 30))
    enable_proxy: bool = field(default_factory=lambda: _env_bool("AKSHARE_ENABLE_PROXY", False))
    enable_fallback: bool = field(default_factory=lambda: _env_bool("DATA_ENABLE_FALLBACK", True))
    tushare_token: str = field(default_factory=lambda: os.getenv("TUSHARE_TOKEN", ""))


class DataSource:
    """
    统一数据源
    
    封装efinance API，提供统一的股票/ETF/基金数据获取接口
    
    支持故障转移机制：
        当efinance获取数据失败时，自动切换到akshare备用数据源。
        可通过配置 enable_fallback=False 禁用此功能。
    
    支持akshare_proxy_patch代理补丁，用于解决东方财富API连接问题。
    使用方法：
        # 方式1：通过配置启用代理
        config = DataConfig(
            proxy_host="101.201.173.125",
            proxy_auth_code="your_auth_code",
            proxy_timeout=30,
            enable_proxy=True
        )
        ds = DataSource(config)
        
        # 方式2：禁用故障转移
        config = DataConfig(enable_fallback=False)
        ds = DataSource(config)
    
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
        
        self._init_proxy_patch()
        
        if not self.config.cache_dir:
            self.config.cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "data", ".cache"
            )
        
        os.makedirs(self.config.cache_dir, exist_ok=True)
        
        self._last_request_time = 0
        self._request_interval = self.config.request_delay
    
    def _init_proxy_patch(self) -> None:
        """
        初始化akshare代理补丁
        
        根据配置决定是否启用代理补丁，用于解决东方财富API连接问题。
        如果akshare_proxy_patch未安装，会打印警告但不会中断程序。
        """
        if not self.config.enable_proxy:
            return
        
        if not self.config.proxy_host or not self.config.proxy_auth_code:
            print("⚠️ 代理已启用但缺少proxy_host或proxy_auth_code配置，跳过代理初始化")
            return
        
        if not HAS_AKSHARE_PROXY_PATCH:
            print("⚠️ akshare-proxy-patch未安装，将使用直接连接方式")
            print("   安装方法: pip install akshare-proxy-patch")
            return
        
        try:
            akshare_proxy_patch.install_patch(
                self.config.proxy_host,
                self.config.proxy_auth_code,
                self.config.proxy_timeout
            )
            print(f"✅ akshare代理补丁已启用: {self.config.proxy_host}")
        except Exception as e:
            print(f"⚠️ akshare代理补丁初始化失败: {e}")
            print("   将使用直接连接方式")
    
    def _resolve_tushare_token(self, token: Optional[str]) -> Optional[str]:
        """
        解析 tushare token
        优先级: 显式传参 > DataConfig.tushare_token(.env) > None
        """
        if token and token.strip():
            return token.strip()
        if self.config.tushare_token and self.config.tushare_token.strip():
            return self.config.tushare_token.strip()
        return None
    
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
    
    def _try_efinance(
        self,
        code: str,
        start_str: str,
        end_str: str,
        klt: int,
        fqt: int
    ) -> Optional[pd.DataFrame]:
        """
        尝试使用efinance获取数据
        
        Args:
            code: 证券代码
            start_str: 开始日期字符串
            end_str: 结束日期字符串
            klt: K线类型
            fqt: 复权类型
            
        Returns:
            历史数据DataFrame，失败返回None
        """
        try:
            df = self._retry_request(
                ef.stock.get_quote_history,
                code,
                beg=start_str,
                end=end_str,
                klt=klt,
                fqt=fqt
            )
            
            if df is not None and len(df) > 0:
                return self._standardize_columns(df)
            return None
            
        except Exception as e:
            print(f"efinance获取{code}数据失败: {e}")
            return None
    
    def _try_akshare_fallback(
        self,
        code: str,
        start_str: str,
        end_str: str,
        klt: int,
        fqt: int
    ) -> Optional[pd.DataFrame]:
        """
        尝试使用akshare作为备用数据源
        
        Args:
            code: 证券代码
            start_str: 开始日期字符串
            end_str: 结束日期字符串
            klt: K线类型
            fqt: 复权类型
            
        Returns:
            历史数据DataFrame，失败返回None
        """
        if not HAS_AKSHARE:
            print("⚠️ akshare未安装，无法使用备用数据源")
            return None
        
        try:
            self._rate_limit()
            
            market_code = self._get_market_code(code)
            
            if klt == 101:
                period = "daily"
            elif klt == 102:
                period = "weekly"
            elif klt == 103:
                period = "monthly"
            else:
                period = "daily"
            
            adjust = "qfq" if fqt == 1 else ("hfq" if fqt == 2 else "")
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_str,
                end_date=end_str,
                adjust=adjust
            )
            
            if df is not None and len(df) > 0:
                column_mapping = {
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                    "换手率": "turnover",
                }
                df = df.rename(columns=column_mapping)
                
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)
                
                return df
            return None
            
        except Exception as e:
            print(f"akshare备用数据源获取{code}数据失败: {e}")
            return None
    
    def _to_tushare_code(self, code: str, data_type: str) -> str:
        """将本地代码格式转换为 tushare ts_code"""
        raw = code.strip()
        if "." in raw:
            left, right = raw.split(".", 1)
            if right.upper() in {"SH", "SZ"}:
                return f"{left}.{right.upper()}"
            raw = left
        
        if raw.lower().startswith(("sh", "sz")) and len(raw) > 2:
            market_prefix = raw[:2].upper()
            return f"{raw[2:]}.{market_prefix}"
        
        if data_type == self.INDEX_TYPE:
            market = "SZ" if raw.startswith("399") else "SH"
            return f"{raw}.{market}"
        
        market = "SH" if raw.startswith(("5", "6", "9")) else "SZ"
        return f"{raw}.{market}"
    
    def _try_tushare_fallback(
        self,
        code: str,
        start_str: str,
        end_str: str,
        data_type: str,
        klt: int,
        fqt: int
    ) -> Optional[pd.DataFrame]:
        """
        尝试使用 tushare 作为第二备用数据源
        
        顺序中位于 efinance 之后、akshare 之前。
        """
        if not HAS_TUSHARE:
            print("⚠️ tushare未安装，跳过tushare备用数据源")
            return None
        
        token = self._resolve_tushare_token(None)
        if not token:
            print("⚠️ 未配置TUSHARE_TOKEN，跳过tushare备用数据源")
            return None
        
        freq_map = {101: "D", 102: "W", 103: "M"}
        freq = freq_map.get(klt, "D")
        adj_map = {0: None, 1: "qfq", 2: "hfq"}
        adj = adj_map.get(fqt)
        
        ts_code = self._to_tushare_code(code, data_type)
        
        if data_type == self.INDEX_TYPE:
            candidate_assets = ["I", "E"]
        elif data_type in {self.ETF_TYPE, self.FUND_TYPE}:
            candidate_assets = ["FD", "E"]
        else:
            candidate_assets = ["E"]
        
        try:
            ts.set_token(token)
        except Exception as e:
            print(f"⚠️ tushare token初始化失败: {e}")
            return None
        
        for asset in candidate_assets:
            try:
                self._rate_limit()
                call_kwargs = {
                    "ts_code": ts_code,
                    "start_date": start_str,
                    "end_date": end_str,
                    "freq": freq,
                    "asset": asset,
                }
                if adj and asset in {"E", "FD"}:
                    call_kwargs["adj"] = adj
                
                df = ts.pro_bar(**call_kwargs)
                if df is None or len(df) == 0:
                    continue
                
                df = df.rename(
                    columns={
                        "trade_date": "date",
                        "vol": "volume",
                        "pct_chg": "pct_change",
                    }
                )
                
                if "date" not in df.columns:
                    continue
                
                df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
                
                if len(df) > 0:
                    return df
            except Exception as e:
                print(f"tushare备用数据源获取{code}数据失败(asset={asset}): {e}")
                continue
        
        return None
    
    def _get_market_code(self, code: str) -> str:
        """
        获取市场代码
        
        Args:
            code: 证券代码
            
        Returns:
            市场代码 (sh/sz前缀)
        """
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
        
        支持故障转移机制，数据源顺序：
        1) efinance
        2) tushare
        3) akshare（若启用了代理补丁则通过代理）
        
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
        
        df = self._try_efinance(code, start_str, end_str, klt, fqt)
        
        if df is not None:
            if use_cache:
                self._save_cache(cache_key, df)
            return df
        
        if self.config.enable_fallback:
            print(f"🔄 efinance获取失败，尝试tushare备用数据源: {code}")
            df = self._try_tushare_fallback(code, start_str, end_str, data_type, klt, fqt)
            
            if df is not None:
                print(f"✅ 故障转移成功，使用tushare获取数据: {code}")
                if use_cache:
                    self._save_cache(cache_key, df)
                return df
            
            print(f"🔄 tushare获取失败，尝试akshare备用数据源: {code}")
            df = self._try_akshare_fallback(code, start_str, end_str, klt, fqt)
            
            if df is not None:
                print(f"✅ 故障转移成功，使用akshare获取数据: {code}")
                if use_cache:
                    self._save_cache(cache_key, df)
                return df
        
        print(f"❌ 获取{code}历史数据失败，所有数据源均不可用")
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
            if df is not None and not df.empty:
                return df
            return pd.DataFrame()
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
            if df is not None and not df.empty:
                return df
            return pd.DataFrame()
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
    
    def get_index_components(
        self,
        index_code: str = "000300",
        date: Optional[Union[str, datetime]] = None,
        use_cache: bool = True,
        tushare_token: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        获取指数成分股列表
        
        Args:
            index_code: 指数代码 (如 "000300" 沪深300, "000905" 中证500)
            date: 查询日期，None表示最新成分股
            use_cache: 是否使用缓存
            tushare_token: tushare token（获取历史成分股需要）
            
        Returns:
            成分股代码列表
        """
        date_str = ""
        if date is not None:
            if isinstance(date, datetime):
                date_str = date.strftime("%Y%m%d")
            else:
                date_str = date.replace("-", "").replace("/", "")
        
        cache_key = f"index_components_{index_code}_{date_str}"
        
        if use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached.tolist() if hasattr(cached, 'tolist') else list(cached)
        
        resolved_tushare_token = self._resolve_tushare_token(tushare_token)
        
        if date is not None and HAS_TUSHARE and resolved_tushare_token:
            try:
                pro = ts.pro_api(resolved_tushare_token)
                ts_code = f"{index_code}.SH" if index_code.startswith('0') or index_code.startswith('3') else index_code
                df = pro.index_weight(index_code=ts_code, start_date=date_str, end_date=date_str)
                
                if df is not None and len(df) > 0:
                    codes = df['con_code'].str[:6].tolist()
                    codes = [str(c).zfill(6) for c in codes]
                    
                    if use_cache:
                        self._save_cache(cache_key, pd.Series(codes))
                    
                    return codes
            except Exception as e:
                print(f"tushare获取{index_code}历史成分股失败: {e}")
        
        if HAS_AKSHARE:
            try:
                self._rate_limit()
                df = ak.index_stock_cons_weight_csindex(symbol=index_code)
                
                if df is None or len(df) == 0:
                    return None
                
                if '成分券代码' in df.columns:
                    codes = df['成分券代码'].tolist()
                elif '股票代码' in df.columns:
                    codes = df['股票代码'].tolist()
                elif 'code' in df.columns:
                    codes = df['code'].tolist()
                else:
                    codes = df.iloc[:, 0].tolist()
                
                codes = [str(c).zfill(6) for c in codes]
                
                if use_cache:
                    self._save_cache(cache_key, pd.Series(codes))
                
                return codes
                
            except Exception as e:
                print(f"akshare获取{index_code}成分股失败: {e}")
        
        if not HAS_AKSHARE and not HAS_TUSHARE:
            print("警告: akshare和tushare都未安装，请运行: pip install akshare 或 pip install tushare")
        
        return None
    
    def get_index_components_history(
        self,
        index_code: str = "000300",
        start_date: Union[str, datetime] = None,
        end_date: Union[str, datetime] = None,
        freq: str = "M",
        use_cache: bool = True,
        tushare_token: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        获取指数历史成分股（按月或季度）
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            freq: 频率 "M"=月度, "Q"=季度
            use_cache: 是否使用缓存
            tushare_token: tushare token（获取历史成分股需要）
            
        Returns:
            字典 {日期字符串: 成分股代码列表}
        """
        if start_date is None:
            start_date = datetime(2020, 1, 1)
        if end_date is None:
            end_date = datetime.now()
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        result = {}
        
        resolved_tushare_token = self._resolve_tushare_token(tushare_token)
        
        if HAS_TUSHARE and resolved_tushare_token:
            try:
                print(f"使用tushare获取{index_code}历史成分股...")
                pro = ts.pro_api(resolved_tushare_token)
                ts_code = f"{index_code}.SH" if index_code.startswith('0') or index_code.startswith('3') else index_code
                
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                
                df = pro.index_weight(index_code=ts_code, start_date=start_str, end_date=end_str)
                
                if df is not None and len(df) > 0:
                    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                    
                    df_sorted = df.sort_values('trade_date')
                    
                    if freq == "M":
                        df['month'] = df['trade_date'].dt.to_period('M')
                        grouped = df.groupby('month')
                    elif freq == "Q":
                        df['quarter'] = df['trade_date'].dt.to_period('Q')
                        grouped = df.groupby('quarter')
                    else:
                        df['month'] = df['trade_date'].dt.to_period('M')
                        grouped = df.groupby('month')
                    
                    for period, group in grouped:
                        last_date = group['trade_date'].max()
                        date_str = last_date.strftime("%Y-%m-%d")
                        codes = group['con_code'].str[:6].tolist()
                        codes = [str(c).zfill(6) for c in codes]
                        result[date_str] = codes
                        
                        cache_key = f"index_components_{index_code}_{last_date.strftime('%Y%m%d')}"
                        if use_cache:
                            self._save_cache(cache_key, pd.Series(codes))
                    
                    print(f"  成功获取 {len(result)} 期历史成分股数据")
                    return result
                    
            except Exception as e:
                print(f"tushare获取历史成分股失败: {e}")
        
        print("警告: 未配置tushare token，无法获取历史成分股")
        print("  可在项目根目录 .env 中配置: TUSHARE_TOKEN=你的token")
        print("  请注册tushare账号并获取token: https://tushare.pro/")
        print("  回测将使用当前成分股，可能存在前视偏差")
        
        current_components = self.get_index_components(index_code, None, use_cache, resolved_tushare_token)
        if current_components:
            result[start_date.strftime("%Y-%m-%d")] = current_components
        
        return result
