"""财务数据服务：Tushare 拉取 + MySQL 缓存读写。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
import time
from typing import Any, Dict, List, Optional

from ..config import settings
from ..db import MarketDataRepository, is_mysql_enabled
from ..db.settings import settings as db_settings
from .providers import TushareMacroClient


class FinancialApiNotSupportedError(ValueError):
    """请求了未在白名单中的财务接口。"""


@dataclass(frozen=True)
class FinancialApiSpec:
    api_name: str
    name_zh: str
    mode: str  # standard_range | disclosure_range | ts_only | period_only | dividend


SUPPORTED_FINANCIAL_APIS: Dict[str, FinancialApiSpec] = {
    "income": FinancialApiSpec("income", "利润表", "standard_range"),
    "balancesheet": FinancialApiSpec("balancesheet", "资产负债表", "standard_range"),
    "cashflow": FinancialApiSpec("cashflow", "现金流量表", "standard_range"),
    "forecast": FinancialApiSpec("forecast", "业绩预告", "standard_range"),
    "express": FinancialApiSpec("express", "业绩快报", "standard_range"),
    "dividend": FinancialApiSpec("dividend", "分红送股", "dividend"),
    "fina_indicator": FinancialApiSpec("fina_indicator", "财务指标", "standard_range"),
    "fina_audit": FinancialApiSpec("fina_audit", "财务审计意见", "standard_range"),
    "fina_mainbz": FinancialApiSpec("fina_mainbz", "主营业务构成", "period_only"),
    "disclosure_date": FinancialApiSpec("disclosure_date", "财报披露日期", "disclosure_range"),
}


class FinancialDataService:
    """财务数据业务服务。"""

    def __init__(self, client: Optional[TushareMacroClient] = None):
        self._client = client
        self.storage_backend = db_settings.storage_backend
        self.repo: Optional[MarketDataRepository] = MarketDataRepository() if is_mysql_enabled() else None
        self.structured_log_json = str(os.getenv("DATA_LOG_JSON", "false")).strip().lower() in {"1", "true", "yes", "on"}

    @property
    def _db_read_enabled(self) -> bool:
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    @property
    def _db_write_enabled(self) -> bool:
        return self.repo is not None and self.storage_backend in {"dual", "mysql"}

    def list_supported_apis(self) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for api_name, spec in SUPPORTED_FINANCIAL_APIS.items():
            default_start, default_end = self._default_range(spec)
            items.append(
                {
                    "api_name": api_name,
                    "name_zh": spec.name_zh,
                    "mode": spec.mode,
                    "default_start": default_start,
                    "default_end": default_end,
                }
            )
        return items

    def fetch_financial(
        self,
        api_name: str,
        ts_code: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        spec = self._get_spec(api_name)
        code = self._normalize_ts_code(ts_code)
        query_params, start_key, end_key = self._build_query_params(spec, code, start, end)
        local_keys: set[str] = set()
        local_count_in_range = 0
        if self._db_read_enabled and self.repo:
            local_keys = set(
                self._safe_repo_call(
                    self.repo.get_financial_observation_keys,
                    spec.api_name,
                    code,
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
            f"请求准备完成：ts_code={code}，范围 {start_key}~{end_key}，本地MySQL已有 {local_count_in_range} 条",
        )
        self._log_progress(spec.api_name, 30, f"开始请求Tushare，参数={query_params}")
        fetch_started_at = time.perf_counter()
        rows = self._get_client().query(spec.api_name, **query_params)
        fetch_cost = time.perf_counter() - fetch_started_at
        self._log_progress(spec.api_name, 70, f"Tushare返回 {len(rows)} 条，耗时 {fetch_cost:.2f}s")
        if not rows and spec.mode in {"disclosure_range", "period_only"}:
            # 这两类接口在部分参数组合下可能返回空，回退为 ts_code 全量查询兜底。
            self._log_progress(spec.api_name, 72, "当前参数无数据，回退为 ts_code 全量查询")
            fallback_started_at = time.perf_counter()
            rows = self._get_client().query(spec.api_name, ts_code=code)
            fallback_cost = time.perf_counter() - fallback_started_at
            self._log_progress(spec.api_name, 78, f"回退查询返回 {len(rows)} 条，耗时 {fallback_cost:.2f}s")

        api_keys = {
            MarketDataRepository.financial_observation_identity(row, code)
            for row in rows
            if isinstance(row, dict)
        }
        api_unique_count = len(api_keys)
        overlap_count = len(api_keys & local_keys) if local_keys else 0
        need_via_api_count = max(api_unique_count - overlap_count, 0)
        self._log_progress(
            spec.api_name,
            82,
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
                    self.repo.upsert_financial_observations,
                    spec.api_name,
                    code,
                    rows,
                    source="tushare_financial",
                    progress_cb=_on_db_progress,
                    default=0,
                )
                or 0
            )
            self._log_progress(spec.api_name, 100, f"MySQL落库完成，affected_rows={stored_count}")
        else:
            self._log_progress(spec.api_name, 100, "本次无需落库（无返回数据或MySQL写入关闭）")

        returned = rows[: max(limit, 1)]
        return {
            "api_name": spec.api_name,
            "name_zh": spec.name_zh,
            "mode": spec.mode,
            "ts_code": code,
            "params": query_params,
            "range_start": start_key,
            "range_end": end_key,
            "source": "tushare",
            "fetched_count": len(rows),
            "stored_count": stored_count,
            "returned_count": len(returned),
            "data": returned,
        }

    def get_cached_financial(
        self,
        api_name: str,
        ts_code: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        spec = self._get_spec(api_name)
        code = self._normalize_ts_code(ts_code)
        _, start_key, end_key = self._build_query_params(spec, code, start, end)

        cached_rows: List[Dict[str, Any]] = []
        if self._db_read_enabled and self.repo:
            cached_rows = self._safe_repo_call(
                self.repo.get_financial_observations,
                spec.api_name,
                code,
                start_key=start_key,
                end_key=end_key,
                limit=max(limit, 1),
                default=[],
            ) or []

        payloads = [item.get("payload_json", {}) for item in cached_rows]
        self._log_progress(
            spec.api_name,
            100,
            f"缓存读取完成：ts_code={code}，范围 {start_key}~{end_key}，返回 {len(payloads)} 条",
        )
        return {
            "api_name": spec.api_name,
            "name_zh": spec.name_zh,
            "mode": spec.mode,
            "ts_code": code,
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
        if self._client is None:
            self._client = TushareMacroClient(timeout=settings.tushare_timeout)
        return self._client

    @staticmethod
    def _get_spec(api_name: str) -> FinancialApiSpec:
        key = (api_name or "").strip().lower()
        spec = SUPPORTED_FINANCIAL_APIS.get(key)
        if spec is None:
            raise FinancialApiNotSupportedError(f"不支持的财务API: {api_name}")
        return spec

    def _build_query_params(
        self,
        spec: FinancialApiSpec,
        ts_code: str,
        start: Optional[str],
        end: Optional[str],
    ) -> tuple[Dict[str, str], str, str]:
        default_start, default_end = self._default_range(spec)
        start_key = self._normalize_date_key(start) if start else default_start
        end_key = self._normalize_date_key(end) if end else default_end

        if spec.mode == "standard_range":
            return {"ts_code": ts_code, "start_date": start_key, "end_date": end_key}, start_key, end_key

        if spec.mode == "disclosure_range":
            return {"ts_code": ts_code, "pre_date": start_key, "end_date": end_key}, start_key, end_key

        if spec.mode == "period_only":
            params = {"ts_code": ts_code}
            if end:
                params["period"] = end_key
            return params, start_key, end_key

        if spec.mode == "dividend":
            params = {"ts_code": ts_code}
            if end:
                params["end_date"] = end_key
            return params, start_key, end_key

        return {"ts_code": ts_code}, start_key, end_key

    @staticmethod
    def _default_range(spec: FinancialApiSpec) -> tuple[str, str]:
        today = date.today()
        end_key = today.strftime("%Y%m%d")
        start_key = (today - timedelta(days=365 * 3)).strftime("%Y%m%d")
        if spec.mode in {"period_only", "dividend"}:
            # 这两类接口通常不强依赖时间范围，保留近一年窗口仅用于展示。
            start_key = (today - timedelta(days=365)).strftime("%Y%m%d")
        return start_key, end_key

    @staticmethod
    def _normalize_date_key(value: Optional[str]) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("日期不能为空")
        text = text.replace("-", "").replace("/", "")
        if len(text) != 8 or not text.isdigit():
            raise ValueError(f"日期格式错误: {value}，应为 YYYYMMDD 或 YYYY-MM-DD")
        datetime.strptime(text, "%Y%m%d")
        return text

    @staticmethod
    def _normalize_ts_code(value: str) -> str:
        code = (value or "").strip().upper()
        if not code:
            raise ValueError("ts_code 不能为空")
        if "." in code:
            parts = code.split(".", 1)
            if len(parts[0]) == 6 and parts[1] in {"SH", "SZ", "BJ"}:
                return f"{parts[0]}.{parts[1]}"
            raise ValueError(f"ts_code 格式错误: {value}，应类似 600519.SH")
        if len(code) == 6 and code.isdigit():
            suffix = "SH" if code.startswith(("5", "6", "9")) else "SZ"
            return f"{code}.{suffix}"
        raise ValueError(f"ts_code 格式错误: {value}，应类似 600519.SH")

    def _safe_repo_call(self, func, *args, default=None, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self._log_progress("db", 0, f"财务数据DB操作失败: {exc}")
            return default

    def _log_progress(self, api_name: str, pct: int, message: str) -> None:
        """统一输出财务拉取进度日志，便于终端实时观察。"""
        progress_pct = max(0, min(int(pct), 100))
        if self.structured_log_json:
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "module": "financial_data",
                "event": "progress",
                "api_name": str(api_name),
                "progress_pct": progress_pct,
                "message": str(message),
            }
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return
        print(f"[财务数据][{api_name}] {progress_pct:>3}% {message}")
