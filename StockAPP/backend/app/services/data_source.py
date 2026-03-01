"""Unified data source service with MySQL market storage support."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import DataSource

from ..db import MarketDataRepository, is_mysql_enabled
from ..db.settings import settings as db_settings

try:
    import efinance as ef
except ImportError:
    ef = None


ETF_LIST = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "159980", "name": "有色ETF", "type": "商品"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "501018", "name": "南方原油LOF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513500", "name": "标普500ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "513080", "name": "法国ETF", "type": "海外"},
    {"code": "159920", "name": "恒生ETF", "type": "海外"},
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    {"code": "510500", "name": "中证500ETF", "type": "宽基"},
    {"code": "510050", "name": "上证50ETF", "type": "宽基"},
    {"code": "510210", "name": "上证指数ETF", "type": "宽基"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "588080", "name": "科创板50ETF", "type": "宽基"},
    {"code": "159995", "name": "芯片ETF", "type": "行业"},
    {"code": "513050", "name": "中概互联ETF", "type": "行业"},
    {"code": "159852", "name": "半导体ETF", "type": "行业"},
    {"code": "159845", "name": "新能源ETF", "type": "行业"},
    {"code": "515030", "name": "新能源车ETF", "type": "行业"},
    {"code": "159806", "name": "光伏ETF", "type": "行业"},
    {"code": "159928", "name": "消费ETF", "type": "行业"},
    {"code": "512670", "name": "国防军工ETF", "type": "行业"},
    {"code": "511010", "name": "国债ETF", "type": "债券"},
    {"code": "511880", "name": "银华日利", "type": "货币"},
]


DEFAULT_HS300 = [
    {"code": "600519", "name": "贵州茅台", "market": "SH", "industry": "白酒"},
    {"code": "601318", "name": "中国平安", "market": "SH", "industry": "保险"},
    {"code": "600036", "name": "招商银行", "market": "SH", "industry": "银行"},
    {"code": "601166", "name": "兴业银行", "market": "SH", "industry": "银行"},
    {"code": "600887", "name": "伊利股份", "market": "SH", "industry": "食品"},
    {"code": "601398", "name": "工商银行", "market": "SH", "industry": "银行"},
    {"code": "600030", "name": "中信证券", "market": "SH", "industry": "证券"},
    {"code": "601288", "name": "农业银行", "market": "SH", "industry": "银行"},
    {"code": "600276", "name": "恒瑞医药", "market": "SH", "industry": "医药"},
    {"code": "600000", "name": "浦发银行", "market": "SH", "industry": "银行"},
]


class DataSourceService:
    """Data service with DB-first read and source fallback."""

    def __init__(self):
        self.data_source = DataSource()
        self.storage_backend = db_settings.storage_backend
        self.repo: Optional[MarketDataRepository] = MarketDataRepository() if is_mysql_enabled() else None

    @property
    def _db_read_enabled(self) -> bool:
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    @property
    def _db_write_enabled(self) -> bool:
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    @property
    def _source_cache_enabled(self) -> bool:
        return self.storage_backend == "dual"

    def get_etf_list(self) -> List[Dict[str, str]]:
        if self._db_write_enabled and self.repo:
            rows = [
                {
                    "code": item["code"],
                    "market": self._infer_market(item["code"]),
                    "security_type": "ETF",
                    "name": item["name"],
                    "industry": item["type"],
                    "source": "etf_list",
                }
                for item in ETF_LIST
            ]
            self._safe_repo_call(self.repo.upsert_instruments, rows, source="etf_list")
        return ETF_LIST

    def get_etf_info(self, code: str) -> Dict[str, str]:
        code = str(code).strip().zfill(6)
        for etf in ETF_LIST:
            if etf["code"] == code:
                return etf
        return {"code": code, "name": "未知", "type": "其他"}

    def get_etf_history(self, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return self._get_history("ETF", code, start_date, end_date)

    def get_stock_history(self, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return self._get_history("STOCK", code, start_date, end_date)

    def _get_history(self, security_type: str, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        code = str(code).strip().zfill(6)
        start_norm = self._normalize_date(start_date)
        end_norm = self._normalize_date(end_date)

        db_rows: List[Dict[str, Any]] = []
        if self._db_read_enabled and self.repo:
            db_rows = self._safe_repo_call(
                self.repo.get_daily_bars,
                code,
                security_type,
                start_norm,
                end_norm,
                default=[],
            )
            if self._has_full_coverage(db_rows, start_norm, end_norm):
                return self._project_history_rows(db_rows)

        source_rows = self._fetch_from_source(security_type, code, start_norm, end_norm)
        if source_rows:
            info_name = self.get_etf_info(code).get("name", code) if security_type == "ETF" else code
            self._upsert_bars(security_type, code, source_rows, info_name)
            return self._project_history_rows(source_rows)

        return self._project_history_rows(db_rows)

    def _fetch_from_source(self, security_type: str, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        try:
            if security_type == "ETF":
                df = self.data_source.get_etf_history(
                    code,
                    start_date,
                    end_date,
                    use_cache=self._source_cache_enabled,
                )
            elif security_type == "STOCK":
                df = self.data_source.get_stock_history(
                    code,
                    start_date,
                    end_date,
                    use_cache=self._source_cache_enabled,
                )
            else:
                df = self.data_source.get_index_history(
                    code,
                    start_date,
                    end_date,
                    use_cache=self._source_cache_enabled,
                )

            if df is None or df.empty:
                return []
            return self._dataframe_to_rows(df)
        except Exception as exc:
            print(f"获取{security_type}数据失败[{code}]: {exc}")
            return []

    def _dataframe_to_rows(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.reset_index(drop=True).iterrows():
            trade_date = self._row_date(row)
            if trade_date is None:
                continue

            open_v = self._to_float(row.get("open", row.get("开盘", 0)))
            high_v = self._to_float(row.get("high", row.get("最高", 0)))
            low_v = self._to_float(row.get("low", row.get("最低", 0)))
            close_v = self._to_float(row.get("close", row.get("收盘", 0)))

            if not self._is_valid_ohlc(open_v, high_v, low_v, close_v):
                continue

            volume = max(int(self._to_float(row.get("volume", row.get("成交量", 0)))), 0)
            amount = max(self._to_float(row.get("amount", row.get("成交额", 0))), 0.0)

            rows.append(
                {
                    "date": trade_date,
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                    "volume": volume,
                    "amount": amount,
                    "amplitude": self._to_float(row.get("amplitude", row.get("振幅", 0))),
                    "pct_change": self._to_float(row.get("pct_change", row.get("涨跌幅", 0))),
                    "change_amount": self._to_float(row.get("change", row.get("涨跌额", row.get("change_amount", 0)))),
                    "turnover": self._to_float(row.get("turnover", row.get("换手率", 0))),
                }
            )

        rows.sort(key=lambda x: x["date"])
        return rows

    def _upsert_bars(self, security_type: str, code: str, rows: List[Dict[str, Any]], name: str) -> None:
        if not rows or not self._db_write_enabled or not self.repo:
            return
        self._safe_repo_call(
            self.repo.upsert_daily_bars,
            code,
            security_type,
            rows,
            name=name,
            market=self._infer_market(code),
            source="datasource",
        )

    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, str]]:
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        if self._db_read_enabled and self.repo:
            db_hits = self._safe_repo_call(self.repo.search_stocks, keyword, limit, default=[])
            if db_hits:
                return db_hits[:limit]

        all_stocks = self._fetch_all_stocks_from_source()
        if not all_stocks:
            return self._get_default_stocks()[:limit]

        key = keyword.lower()
        exact_matches = []
        code_prefix_matches = []
        name_contains_matches = []

        for stock in all_stocks:
            code = stock["code"].lower()
            name = stock["name"].lower()

            if code == key or name == key:
                exact_matches.append(stock)
            elif code.startswith(key):
                code_prefix_matches.append(stock)
            elif key in name:
                name_contains_matches.append(stock)

        result = (exact_matches + code_prefix_matches + name_contains_matches)[:limit]
        if result and self._db_write_enabled and self.repo:
            rows = [
                {
                    "code": item["code"],
                    "market": item.get("market", self._infer_market(item["code"])),
                    "security_type": "STOCK",
                    "name": item["name"],
                    "industry": item.get("industry", ""),
                    "source": "efinance_stock_list",
                }
                for item in result
            ]
            self._safe_repo_call(self.repo.upsert_instruments, rows, source="efinance_stock_list")

        return result

    def get_hs300_constituents(self) -> List[Dict[str, str]]:
        code_name_map = self._fetch_quote_name_map()
        try:
            components = self.data_source.get_index_components(
                index_code="000300",
                date=None,
                use_cache=self._source_cache_enabled,
            )
            if components:
                result: List[Dict[str, str]] = []
                for code in components:
                    norm_code = str(code).strip().zfill(6)
                    result.append(
                        {
                            "code": norm_code,
                            "name": code_name_map.get(norm_code, norm_code),
                            "market": self._infer_market(norm_code),
                            "industry": "",
                        }
                    )

                if self._db_write_enabled and self.repo:
                    rows = [
                        {
                            "code": item["code"],
                            "market": item["market"],
                            "security_type": "STOCK",
                            "name": item["name"],
                            "industry": "",
                            "source": "hs300",
                        }
                        for item in result
                    ]
                    self._safe_repo_call(self.repo.upsert_instruments, rows, source="hs300")
                    self._safe_repo_call(
                        self.repo.upsert_index_components,
                        "000300",
                        [item["code"] for item in result],
                        datetime.now().date().isoformat(),
                        "hs300",
                    )
                return result
        except Exception as exc:
            print(f"获取沪深300成分失败: {exc}")

        return DEFAULT_HS300

    def clear_cache(self) -> Dict[str, Any]:
        removed_files = self.data_source.clear_cache()
        return {
            "removed_files": int(removed_files or 0),
            "message": f"已清除 {int(removed_files or 0)} 个缓存文件",
        }

    def get_cache_info(self) -> Dict[str, Any]:
        legacy_info = self.data_source.get_cache_info()
        stats = {"symbol_count": 0, "row_count": 0, "last_sync_at": None}
        if self._db_read_enabled and self.repo:
            stats = self._safe_repo_call(self.repo.get_cache_stats, default=stats)

        # mysql单栈后兼容字段归零，避免继续暴露pkl状态
        legacy_cache_dir = legacy_info.get("cache_dir", "")
        legacy_file_count = legacy_info.get("file_count", 0)
        legacy_total_size_mb = legacy_info.get("total_size_mb", 0)
        legacy_expire_hours = legacy_info.get("expire_hours", 0)
        if self.storage_backend == "mysql":
            legacy_cache_dir = ""
            legacy_file_count = 0
            legacy_total_size_mb = 0
            legacy_expire_hours = 0

        return {
            "cache_dir": legacy_cache_dir,
            "file_count": legacy_file_count,
            "total_size_mb": legacy_total_size_mb,
            "expire_hours": legacy_expire_hours,
            "storage_backend": self.storage_backend,
            "symbol_count": int(stats.get("symbol_count", 0)),
            "row_count": int(stats.get("row_count", 0)),
            "last_sync_at": stats.get("last_sync_at"),
        }

    def _fetch_all_stocks_from_source(self) -> List[Dict[str, str]]:
        if ef is None:
            return []
        try:
            df = ef.stock.get_base_info("A股")
            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                code = str(row.get("股票代码", "")).strip().zfill(6)
                name = str(row.get("股票名称", "")).strip()
                if code and name:
                    result.append(
                        {
                            "code": code,
                            "name": name,
                            "market": self._infer_market(code),
                            "industry": "",
                        }
                    )
            return result
        except Exception:
            return []

    def _fetch_quote_name_map(self) -> Dict[str, str]:
        if ef is None:
            return {}
        try:
            df = ef.stock.get_realtime_quotes()
            if df is None or df.empty:
                return {}
            mapping = {}
            for _, row in df.iterrows():
                code = str(row.get("股票代码", "")).strip().zfill(6)
                name = str(row.get("股票名称", "")).strip()
                if code and name:
                    mapping[code] = name
            return mapping
        except Exception:
            return {}

    @staticmethod
    def _project_history_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        projected: List[Dict[str, Any]] = []
        for row in rows:
            projected.append(
                {
                    "date": str(row.get("date", ""))[:10],
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(float(row.get("volume", 0) or 0)),
                    "amount": float(row.get("amount", 0) or 0),
                    "amplitude": float(row.get("amplitude", 0) or 0),
                    "pct_change": float(row.get("pct_change", 0) or 0),
                    "change_amount": float(row.get("change_amount", row.get("change", 0)) or 0),
                    "turnover": float(row.get("turnover", 0) or 0),
                }
            )
        projected.sort(key=lambda x: x["date"])
        return projected

    @staticmethod
    def _normalize_date(value: str) -> str:
        return datetime.strptime(value[:10], "%Y-%m-%d").date().isoformat()

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _row_date(row: pd.Series) -> Optional[str]:
        raw = row.get("date", row.get("日期"))
        if raw is None:
            return None
        if isinstance(raw, str):
            return raw[:10]
        if isinstance(raw, datetime):
            return raw.date().isoformat()
        if isinstance(raw, date):
            return raw.isoformat()
        try:
            return pd.to_datetime(raw).date().isoformat()
        except Exception:
            return None

    @staticmethod
    def _is_valid_ohlc(open_v: float, high_v: float, low_v: float, close_v: float) -> bool:
        if min(open_v, high_v, low_v, close_v) < 0:
            return False
        if high_v < max(open_v, close_v) or low_v > min(open_v, close_v):
            return False
        if high_v < low_v:
            return False
        return True

    @staticmethod
    def _has_full_coverage(rows: List[Dict[str, Any]], start_date: str, end_date: str) -> bool:
        if not rows:
            return False
        try:
            start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
            first = datetime.strptime(str(rows[0].get("date", ""))[:10], "%Y-%m-%d").date()
            last = datetime.strptime(str(rows[-1].get("date", ""))[:10], "%Y-%m-%d").date()
        except Exception:
            return False

        # 允许交易日边界偏移（周末/节假日），避免无意义回源
        tolerance = timedelta(days=10)
        return first <= (start + tolerance) and last >= (end - tolerance)

    @staticmethod
    def _infer_market(code: str) -> str:
        code = str(code).strip().zfill(6)
        if code.startswith(("6", "5", "9")):
            return "SH"
        return "SZ"

    @staticmethod
    def _safe_repo_call(func, *args, default=None, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            print(f"DB操作失败: {exc}")
            return default

    @staticmethod
    def _get_default_stocks() -> List[Dict[str, str]]:
        return [
            {"code": "600519", "name": "贵州茅台", "market": "SH", "industry": "白酒"},
            {"code": "000858", "name": "五粮液", "market": "SZ", "industry": "白酒"},
            {"code": "601318", "name": "中国平安", "market": "SH", "industry": "保险"},
            {"code": "000333", "name": "美的集团", "market": "SZ", "industry": "家电"},
            {"code": "600036", "name": "招商银行", "market": "SH", "industry": "银行"},
            {"code": "300750", "name": "宁德时代", "market": "SZ", "industry": "电池"},
        ]
