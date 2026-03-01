"""Data update service with DB checkpoints and sync job audit."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .data_source import DataSourceService, ETF_LIST
from ..db import MarketDataRepository


class DataUpdateService:
    """Periodic market data updater with incremental checkpoints."""

    DEFAULT_ETF_CODES = [item["code"] for item in ETF_LIST]

    def __init__(self, update_time: str = "16:00", update_callback: Optional[Callable] = None):
        self.data_service = DataSourceService()
        self.repo = MarketDataRepository() if self.data_service.repo else None
        self.update_time = update_time
        self.update_callback = update_callback

        self.etf_codes: List[str] = self.DEFAULT_ETF_CODES.copy()
        self.stock_codes: List[str] = []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update: Optional[datetime] = None

    def add_etf_codes(self, codes: List[str]) -> None:
        for code in codes:
            norm = str(code).strip().zfill(6)
            if norm not in self.etf_codes:
                self.etf_codes.append(norm)

    def add_stock_codes(self, codes: List[str]) -> None:
        for code in codes:
            norm = str(code).strip().zfill(6)
            if norm not in self.stock_codes:
                self.stock_codes.append(norm)

    def set_etf_codes(self, codes: List[str]) -> None:
        self.etf_codes = [str(code).strip().zfill(6) for code in codes]

    def set_stock_codes(self, codes: List[str]) -> None:
        self.stock_codes = [str(code).strip().zfill(6) for code in codes]

    def _resolve_start_date(self, code: str, security_type: str) -> str:
        if self.repo is None:
            return (datetime.now() - timedelta(days=365 * 10)).date().isoformat()

        checkpoint = self._safe_repo_call(
            self.repo.get_checkpoint,
            code=code,
            security_type=security_type,
            source="update_service",
            default=None,
        )
        if checkpoint:
            cp_date = datetime.strptime(checkpoint[:10], "%Y-%m-%d").date()
            return (cp_date + timedelta(days=1)).isoformat()
        return (datetime.now() - timedelta(days=365 * 10)).date().isoformat()

    @staticmethod
    def _resolve_end_date() -> str:
        return datetime.now().date().isoformat()

    def update_etf_data(self) -> Dict[str, object]:
        results: Dict[str, object] = {
            "total": len(self.etf_codes),
            "success": 0,
            "failed": 0,
            "errors": [],
            "updated_rows": 0,
        }

        end_date = self._resolve_end_date()
        for code in self.etf_codes:
            try:
                start_date = self._resolve_start_date(code, "ETF")
                if start_date > end_date:
                    continue

                rows = self.data_service.get_etf_history(code, start_date, end_date)
                if rows:
                    results["success"] = int(results["success"]) + 1
                    results["updated_rows"] = int(results["updated_rows"]) + len(rows)
                    if self.repo:
                        self._safe_repo_call(
                            self.repo.upsert_checkpoint,
                            code=code,
                            security_type="ETF",
                            last_synced_date=rows[-1]["date"],
                            source="update_service",
                            name=self.data_service.get_etf_info(code).get("name", code),
                        )
                else:
                    results["failed"] = int(results["failed"]) + 1
                    cast_errors = results["errors"]
                    assert isinstance(cast_errors, list)
                    cast_errors.append(f"{code}: 无新增数据")
            except Exception as exc:
                results["failed"] = int(results["failed"]) + 1
                cast_errors = results["errors"]
                assert isinstance(cast_errors, list)
                cast_errors.append(f"{code}: {exc}")

        return results

    def update_stock_data(self) -> Dict[str, object]:
        results: Dict[str, object] = {
            "total": len(self.stock_codes),
            "success": 0,
            "failed": 0,
            "errors": [],
            "updated_rows": 0,
        }
        if not self.stock_codes:
            return results

        end_date = self._resolve_end_date()
        for code in self.stock_codes:
            try:
                start_date = self._resolve_start_date(code, "STOCK")
                if start_date > end_date:
                    continue

                rows = self.data_service.get_stock_history(code, start_date, end_date)
                if rows:
                    results["success"] = int(results["success"]) + 1
                    results["updated_rows"] = int(results["updated_rows"]) + len(rows)
                    if self.repo:
                        self._safe_repo_call(
                            self.repo.upsert_checkpoint,
                            code=code,
                            security_type="STOCK",
                            last_synced_date=rows[-1]["date"],
                            source="update_service",
                            name=code,
                        )
                else:
                    results["failed"] = int(results["failed"]) + 1
                    cast_errors = results["errors"]
                    assert isinstance(cast_errors, list)
                    cast_errors.append(f"{code}: 无新增数据")
            except Exception as exc:
                results["failed"] = int(results["failed"]) + 1
                cast_errors = results["errors"]
                assert isinstance(cast_errors, list)
                cast_errors.append(f"{code}: {exc}")

        return results

    def update_now(self) -> Dict[str, object]:
        job_id: Optional[str] = None
        if self.repo:
            job_id = self._safe_repo_call(
                self.repo.start_sync_job,
                "update_now",
                {"etf_codes": self.etf_codes, "stock_codes": self.stock_codes},
                default=None,
            )

        try:
            etf_results = self.update_etf_data()
            stock_results = self.update_stock_data()

            self._last_update = datetime.now()
            result: Dict[str, object] = {
                "etf": etf_results,
                "stock": stock_results,
                "update_time": self._last_update.isoformat(),
                "job_id": job_id,
            }
            if self.repo and job_id:
                self._safe_repo_call(
                    self.repo.finish_sync_job,
                    job_id,
                    status="success",
                    stats={
                        "etf": {
                            "success": etf_results.get("success", 0),
                            "failed": etf_results.get("failed", 0),
                            "updated_rows": etf_results.get("updated_rows", 0),
                        },
                        "stock": {
                            "success": stock_results.get("success", 0),
                            "failed": stock_results.get("failed", 0),
                            "updated_rows": stock_results.get("updated_rows", 0),
                        },
                    },
                )

            if self.update_callback:
                self.update_callback(result)
            return result
        except Exception as exc:
            if self.repo and job_id:
                self._safe_repo_call(
                    self.repo.finish_sync_job,
                    job_id=job_id,
                    status="failed",
                    stats={},
                    error_text=str(exc),
                )
            raise

    def _schedule_loop(self) -> None:
        while self._running:
            now = datetime.now()
            try:
                hour, minute = map(int, self.update_time.split(":"))
                next_update = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_update <= now:
                    next_update += timedelta(days=1)

                wait_seconds = int((next_update - now).total_seconds())

                if self._last_update is None or self._last_update.date() < now.date():
                    if now.hour >= hour:
                        self.update_now()

                time.sleep(min(wait_seconds, 60))
            except Exception:
                time.sleep(60)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def get_status(self) -> Dict[str, object]:
        stats = self.data_service.get_cache_info()
        return {
            "running": self._running,
            "update_time": self.update_time,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "etf_codes_count": len(self.etf_codes),
            "stock_codes_count": len(self.stock_codes),
            "storage_backend": stats.get("storage_backend", "pkl"),
            "last_sync_at": stats.get("last_sync_at"),
        }

    @staticmethod
    def _safe_repo_call(func, *args, default=None, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            print(f"更新服务DB操作失败: {exc}")
            return default


_service_instance: Optional[DataUpdateService] = None


def get_update_service() -> DataUpdateService:
    global _service_instance
    if _service_instance is None:
        _service_instance = DataUpdateService()
    return _service_instance
