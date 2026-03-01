"""宏观数据服务：Tushare 拉取 + MySQL 缓存读写。

该服务在系统中的职责：
1. 统一维护“支持的宏观接口清单”
2. 根据接口粒度（日/月/季）规范化输入时间参数
3. 调用 provider 拉取实时数据，并执行落库
4. 支持只读缓存模式（`cache_only=true`）
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import settings
from ..db import MarketDataRepository, is_mysql_enabled
from ..db.settings import settings as db_settings
from .providers import TushareMacroClient


class MacroApiNotSupportedError(ValueError):
    """请求了未在白名单中的宏观接口。"""


@dataclass(frozen=True)
class MacroApiSpec:
    """宏观接口元信息。"""

    api_name: str
    name_zh: str
    granularity: str  # date | month | quarter


# 白名单方式管理可调用接口，避免将任意字符串透传到第三方接口。
SUPPORTED_MACRO_APIS: Dict[str, MacroApiSpec] = {
    "shibor": MacroApiSpec("shibor", "Shibor利率", "date"),
    "shibor_quote": MacroApiSpec("shibor_quote", "Shibor报价明细", "date"),
    "shibor_lpr": MacroApiSpec("shibor_lpr", "LPR贷款市场报价利率", "date"),
    "libor": MacroApiSpec("libor", "Libor利率", "date"),
    "hibor": MacroApiSpec("hibor", "Hibor利率", "date"),
    "wz_index": MacroApiSpec("wz_index", "温州民间借贷利率", "date"),
    "gz_index": MacroApiSpec("gz_index", "广州民间借贷利率", "date"),
    "cn_gdp": MacroApiSpec("cn_gdp", "中国GDP季度数据", "quarter"),
    "cn_cpi": MacroApiSpec("cn_cpi", "中国CPI月度数据", "month"),
    "cn_ppi": MacroApiSpec("cn_ppi", "中国PPI月度数据", "month"),
    "cn_m": MacroApiSpec("cn_m", "中国货币供应量月度数据", "month"),
    "sf_month": MacroApiSpec("sf_month", "中国社融增量月度数据", "month"),
    "cn_pmi": MacroApiSpec("cn_pmi", "中国PMI月度数据", "month"),
    "us_tycr": MacroApiSpec("us_tycr", "美国国债收益率曲线", "date"),
    "us_trycr": MacroApiSpec("us_trycr", "美国实际收益率曲线", "date"),
    "us_tbr": MacroApiSpec("us_tbr", "美国短期国债利率", "date"),
    "us_tltr": MacroApiSpec("us_tltr", "美国长期国债利率", "date"),
    "us_trltr": MacroApiSpec("us_trltr", "美国长期国债平均利率", "date"),
    "eco_cal": MacroApiSpec("eco_cal", "全球经济日历", "date"),
}


class MacroDataService:
    """宏观数据业务服务。

    读写路径：
    - 实时查询：Tushare -> 结果清洗 -> MySQL upsert -> 返回
    - 缓存查询：MySQL -> payload_json -> 返回
    """

    def __init__(self, client: Optional[TushareMacroClient] = None):
        """初始化服务。

        参数说明：
        - client: 可注入 provider（便于测试）；为空时使用默认 `TushareMacroClient`
        """
        self._client = client
        self.storage_backend = db_settings.storage_backend
        self.repo: Optional[MarketDataRepository] = MarketDataRepository() if is_mysql_enabled() else None
        self.structured_log_json = str(os.getenv("DATA_LOG_JSON", "false")).strip().lower() in {"1", "true", "yes", "on"}

    @property
    def _db_read_enabled(self) -> bool:
        """当前配置是否允许从 MySQL 读取宏观缓存。"""
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    @property
    def _db_write_enabled(self) -> bool:
        """当前配置是否允许将宏观数据写入 MySQL。"""
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    def list_supported_apis(self) -> List[Dict[str, str]]:
        """返回接口清单及默认查询窗口，供前端做下拉与默认值展示。"""
        items: List[Dict[str, str]] = []
        for api_name, spec in SUPPORTED_MACRO_APIS.items():
            default_start, default_end = self._default_range(spec)
            items.append(
                {
                    "api_name": api_name,
                    "name_zh": spec.name_zh,
                    "granularity": spec.granularity,
                    "default_start": default_start,
                    "default_end": default_end,
                }
            )
        return items

    def fetch_macro(
        self,
        api_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """实时拉取宏观数据并尝试落库。

        处理流程：
        1. 校验接口名（白名单）
        2. 按粒度格式化时间参数
        3. 调用 Tushare 拉取
        4. 若开启 MySQL 写入，则 upsert 到 `macro_observations`
        5. 返回前端所需结构（含 fetched/stored 统计）
        """
        spec = self._get_spec(api_name)
        query_params, start_key, end_key = self._build_query_params(spec, start, end)
        local_keys: set[str] = set()
        local_count_in_range = 0
        if self._db_read_enabled and self.repo:
            local_keys = set(
                self._safe_repo_call(
                    self.repo.get_macro_observation_keys,
                    spec.api_name,
                    start_key=start_key,
                    end_key=end_key,
                    default=[],
                )
                or []
            )
            local_count_in_range = len(local_keys)

        self._log_progress(
            spec.api_name,
            10,
            f"请求准备完成：范围 {start_key}~{end_key}，本地MySQL已有 {local_count_in_range} 条",
        )
        self._log_progress(spec.api_name, 30, f"开始请求Tushare，参数={query_params}")
        fetch_started_at = time.perf_counter()
        rows = self._get_client().query(spec.api_name, **query_params)
        fetch_cost = time.perf_counter() - fetch_started_at
        self._log_progress(spec.api_name, 70, f"Tushare返回 {len(rows)} 条，耗时 {fetch_cost:.2f}s")

        api_keys = {
            MarketDataRepository.macro_observation_identity(row)
            for row in rows
            if isinstance(row, dict)
        }
        api_unique_count = len(api_keys)
        overlap_count = len(api_keys & local_keys) if local_keys else 0
        need_via_api_count = max(api_unique_count - overlap_count, 0)
        self._log_progress(
            spec.api_name,
            80,
            (
                f"数据评估：接口候选 {api_unique_count} 条，"
                f"本地已命中 {overlap_count} 条，需通过接口补齐 {need_via_api_count} 条"
            ),
        )

        stored_count = 0
        if rows and self._db_write_enabled and self.repo:
            def _on_db_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                pct = 90 + int((done / total) * 9)
                self._log_progress(spec.api_name, min(pct, 99), f"MySQL落库进度 {done}/{total}")

            stored_count = int(
                self._safe_repo_call(
                    self.repo.upsert_macro_observations,
                    spec.api_name,
                    rows,
                    source="tushare_macro",
                    progress_cb=_on_db_progress,
                    default=0,
                )
                or 0
            )
            self._log_progress(spec.api_name, 100, f"MySQL落库完成，affected_rows={stored_count}")
        else:
            self._log_progress(spec.api_name, 100, "本次无需落库（无返回数据或MySQL写入关闭）")

        # 返回层做一次截断，避免单次响应过大。
        returned = rows[: max(limit, 1)]
        return {
            "api_name": spec.api_name,
            "name_zh": spec.name_zh,
            "granularity": spec.granularity,
            "params": query_params,
            "range_start": start_key,
            "range_end": end_key,
            "source": "tushare",
            "fetched_count": len(rows),
            "stored_count": stored_count,
            "returned_count": len(returned),
            "data": returned,
        }

    def get_cached_macro(
        self,
        api_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """仅从 MySQL 缓存读取宏观数据，不触发 Tushare 请求。"""
        spec = self._get_spec(api_name)
        _, start_key, end_key = self._build_query_params(spec, start, end)

        cached_rows: List[Dict[str, Any]] = []
        if self._db_read_enabled and self.repo:
            cached_rows = self._safe_repo_call(
                self.repo.get_macro_observations,
                spec.api_name,
                start_key=start_key,
                end_key=end_key,
                limit=max(limit, 1),
                default=[],
            ) or []

        # 缓存表保存的原始记录在 payload_json 字段，这里直接透传给上层。
        payloads = [item.get("payload_json", {}) for item in cached_rows]
        self._log_progress(
            spec.api_name,
            100,
            f"缓存读取完成：范围 {start_key}~{end_key}，返回 {len(payloads)} 条",
        )
        return {
            "api_name": spec.api_name,
            "name_zh": spec.name_zh,
            "granularity": spec.granularity,
            "params": {"start_key": start_key, "end_key": end_key},
            "range_start": start_key,
            "range_end": end_key,
            "source": "mysql_cache",
            "fetched_count": 0,
            "stored_count": 0,
            "returned_count": len(payloads),
            "data": payloads,
        }

    def _get_client(self) -> TushareMacroClient:
        """延迟初始化 provider，避免服务创建时即发起外部依赖初始化。"""
        if self._client is None:
            self._client = TushareMacroClient(timeout=settings.tushare_timeout)
        return self._client

    @staticmethod
    def _get_spec(api_name: str) -> MacroApiSpec:
        """按接口名获取规格定义；不存在时抛业务异常。"""
        key = (api_name or "").strip().lower()
        spec = SUPPORTED_MACRO_APIS.get(key)
        if spec is None:
            raise MacroApiNotSupportedError(f"不支持的宏观API: {api_name}")
        return spec

    def _build_query_params(
        self,
        spec: MacroApiSpec,
        start: Optional[str],
        end: Optional[str],
    ) -> tuple[Dict[str, str], str, str]:
        """根据粒度组装 Tushare 参数，并返回标准化后的起止 key。"""
        default_start, default_end = self._default_range(spec)

        if spec.granularity == "date":
            start_key = self._normalize_date_key(start) if start else default_start
            end_key = self._normalize_date_key(end) if end else default_end
            return {"start_date": start_key, "end_date": end_key}, start_key, end_key

        if spec.granularity == "month":
            start_key = self._normalize_month_key(start) if start else default_start
            end_key = self._normalize_month_key(end) if end else default_end
            return {"start_m": start_key, "end_m": end_key}, start_key, end_key

        start_key = self._normalize_quarter_key(start) if start else default_start
        end_key = self._normalize_quarter_key(end) if end else default_end
        return {"start_q": start_key, "end_q": end_key}, start_key, end_key

    @staticmethod
    def _default_range(spec: MacroApiSpec) -> tuple[str, str]:
        """给每种粒度生成默认查询区间（近 1 年/24 月/8 季）。"""
        today = date.today()
        if spec.granularity == "date":
            end_key = today.strftime("%Y%m%d")
            start_key = (today - timedelta(days=365)).strftime("%Y%m%d")
            return start_key, end_key

        if spec.granularity == "month":
            end_key = today.strftime("%Y%m")
            start_year, start_month = MacroDataService._shift_month(today.year, today.month, -23)
            start_key = f"{start_year:04d}{start_month:02d}"
            return start_key, end_key

        end_quarter = ((today.month - 1) // 3) + 1
        start_year, start_quarter = MacroDataService._shift_quarter(today.year, end_quarter, -7)
        return f"{start_year:04d}Q{start_quarter}", f"{today.year:04d}Q{end_quarter}"

    @staticmethod
    def _normalize_date_key(value: Optional[str]) -> str:
        """规范化日级参数，输出 `YYYYMMDD`。"""
        text = (value or "").strip()
        if not text:
            raise ValueError("日期不能为空")
        text = text.replace("-", "").replace("/", "")
        if len(text) != 8 or not text.isdigit():
            raise ValueError(f"日期格式错误: {value}，应为 YYYYMMDD 或 YYYY-MM-DD")
        datetime.strptime(text, "%Y%m%d")
        return text

    @staticmethod
    def _normalize_month_key(value: Optional[str]) -> str:
        """规范化月级参数，输出 `YYYYMM`。"""
        text = (value or "").strip()
        if not text:
            raise ValueError("月份不能为空")
        text = text.replace("-", "").replace("/", "")
        if len(text) != 6 or not text.isdigit():
            raise ValueError(f"月份格式错误: {value}，应为 YYYYMM 或 YYYY-MM")
        datetime.strptime(f"{text}01", "%Y%m%d")
        return text

    @staticmethod
    def _normalize_quarter_key(value: Optional[str]) -> str:
        """规范化季级参数，输出 `YYYYQn`。"""
        text = (value or "").strip().upper().replace(" ", "")
        matched = re.fullmatch(r"(\d{4})Q([1-4])", text)
        if not matched:
            raise ValueError(f"季度格式错误: {value}，应为 YYYYQn（如 2025Q4）")
        return f"{matched.group(1)}Q{matched.group(2)}"

    @staticmethod
    def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
        """按“月”进行偏移，返回新年月。"""
        total = (year * 12) + (month - 1) + delta
        new_year = total // 12
        new_month = (total % 12) + 1
        return new_year, new_month

    @staticmethod
    def _shift_quarter(year: int, quarter: int, delta: int) -> tuple[int, int]:
        """按“季度”进行偏移，返回新年季。"""
        total = (year * 4) + (quarter - 1) + delta
        new_year = total // 4
        new_quarter = (total % 4) + 1
        return new_year, new_quarter

    def _safe_repo_call(self, func, *args, default=None, **kwargs):
        """DB 调用保护：数据库不可用时降级返回默认值，避免影响主流程。"""
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self._log_progress("db", 0, f"宏观数据DB操作失败: {exc}")
            return default

    def _log_progress(self, api_name: str, pct: int, message: str) -> None:
        """统一输出宏观拉取进度日志，便于终端实时观察。"""
        progress_pct = max(0, min(int(pct), 100))
        if self.structured_log_json:
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "module": "macro_data",
                "event": "progress",
                "api_name": str(api_name),
                "progress_pct": progress_pct,
                "message": str(message),
            }
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return
        print(f"[宏观数据][{api_name}] {progress_pct:>3}% {message}")
