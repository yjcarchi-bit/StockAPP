"""PKL cache migration service (idempotent)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..db import MarketDataRepository


def infer_security_type(code: str) -> str:
    code = str(code).strip().zfill(6)
    if code in {"000300", "000905", "000852", "399300"}:
        return "INDEX"
    if code.startswith(("51", "15", "16", "58", "56", "50", "52")):
        return "ETF"
    return "STOCK"


def _extract_code(df: pd.DataFrame) -> Optional[str]:
    if "股票代码" in df.columns:
        series = df["股票代码"].dropna().astype(str)
        if not series.empty:
            return series.iloc[0].strip().zfill(6)
    if "code" in df.columns:
        series = df["code"].dropna().astype(str)
        if not series.empty:
            return series.iloc[0].strip().zfill(6)
    return None


def _extract_name(df: pd.DataFrame, default: str) -> str:
    if "股票名称" in df.columns:
        series = df["股票名称"].dropna().astype(str)
        if not series.empty:
            return series.iloc[0].strip()
    if "name" in df.columns:
        series = df["name"].dropna().astype(str)
        if not series.empty:
            return series.iloc[0].strip()
    return default


def _to_float(value: Any) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _normalize_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, row in df.reset_index(drop=True).iterrows():
        raw_date = row.get("date", row.get("日期"))
        if raw_date is None:
            continue
        try:
            dt = pd.to_datetime(raw_date).date().isoformat()
        except Exception:
            continue

        open_v = _to_float(row.get("open", row.get("开盘", 0)))
        high_v = _to_float(row.get("high", row.get("最高", 0)))
        low_v = _to_float(row.get("low", row.get("最低", 0)))
        close_v = _to_float(row.get("close", row.get("收盘", 0)))
        if high_v < low_v:
            continue
        if high_v < max(open_v, close_v) or low_v > min(open_v, close_v):
            continue

        rows.append(
            {
                "date": dt,
                "open": open_v,
                "high": high_v,
                "low": low_v,
                "close": close_v,
                "volume": max(int(_to_float(row.get("volume", row.get("成交量", 0)))), 0),
                "amount": max(_to_float(row.get("amount", row.get("成交额", 0))), 0.0),
                "amplitude": _to_float(row.get("amplitude", row.get("振幅", 0))),
                "pct_change": _to_float(row.get("pct_change", row.get("涨跌幅", 0))),
                "change_amount": _to_float(row.get("change", row.get("涨跌额", row.get("change_amount", 0)))),
                "turnover": _to_float(row.get("turnover", row.get("换手率", 0))),
            }
        )

    rows.sort(key=lambda x: x["date"])
    return rows


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"processed": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("processed"), list):
            return data
    except Exception:
        pass
    return {"processed": []}


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def migrate_pkl_cache(
    cache_dir: Optional[str] = None,
    resume_file: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    resolved_cache_dir = Path(cache_dir) if cache_dir else root / "data" / ".cache"
    resolved_resume_file = Path(resume_file) if resume_file else root / "backend" / "scripts" / ".migrate_pkl_state.json"

    if not resolved_cache_dir.exists():
        return {
            "success": False,
            "message": f"缓存目录不存在: {resolved_cache_dir}",
            "files_total": 0,
            "files_processed": 0,
            "rows_written": 0,
            "errors": [],
        }

    files = sorted(resolved_cache_dir.glob("*.pkl"))
    state = _load_state(resolved_resume_file)
    processed = set(state.get("processed", []))

    repo = MarketDataRepository()
    job_id: Optional[str] = None
    try:
        job_id = repo.start_sync_job(
            "migrate_pkl",
            {
                "cache_dir": str(resolved_cache_dir),
                "resume_file": str(resolved_resume_file),
                "force": force,
            },
        )
    except Exception as exc:
        return {
            "success": False,
            "message": f"MySQL不可用，无法执行迁移: {exc}",
            "files_total": len(files),
            "files_processed": 0,
            "rows_written": 0,
            "errors": [str(exc)],
        }

    files_processed = 0
    rows_written = 0
    errors: List[str] = []

    try:
        for file_path in files:
            file_key = file_path.name
            if (not force) and file_key in processed:
                continue

            try:
                df = pd.read_pickle(file_path)
                if not isinstance(df, pd.DataFrame) or df.empty:
                    processed.add(file_key)
                    continue

                code = _extract_code(df)
                if not code:
                    errors.append(f"{file_key}: 缺失股票代码")
                    continue

                name = _extract_name(df, code)
                rows = _normalize_rows(df)
                if not rows:
                    processed.add(file_key)
                    continue

                security_type = infer_security_type(code)
                written = repo.upsert_daily_bars(
                    code=code,
                    security_type=security_type,
                    bars=rows,
                    name=name,
                    source="pkl_migration",
                )
                rows_written += int(written)

                repo.upsert_checkpoint(
                    code=code,
                    security_type=security_type,
                    last_synced_date=rows[-1]["date"],
                    source="pkl_migration",
                    name=name,
                )

                processed.add(file_key)
                files_processed += 1
                state["processed"] = sorted(processed)
                _save_state(resolved_resume_file, state)
            except Exception as exc:
                errors.append(f"{file_key}: {exc}")

        result = {
            "success": len(errors) == 0,
            "message": "迁移完成" if len(errors) == 0 else "迁移完成（含错误）",
            "files_total": len(files),
            "files_processed": files_processed,
            "rows_written": rows_written,
            "errors": errors,
            "job_id": job_id,
        }
        if job_id:
            repo.finish_sync_job(
                job_id=job_id,
                status="success" if len(errors) == 0 else "partial",
                stats={
                    "files_total": len(files),
                    "files_processed": files_processed,
                    "rows_written": rows_written,
                    "error_count": len(errors),
                },
                error_text="\n".join(errors[:20]) if errors else None,
            )
        return result

    except Exception as exc:
        if job_id:
            repo.finish_sync_job(job_id=job_id, status="failed", stats={}, error_text=str(exc))
        return {
            "success": False,
            "message": f"迁移失败: {exc}",
            "files_total": len(files),
            "files_processed": files_processed,
            "rows_written": rows_written,
            "errors": errors,
            "job_id": job_id,
        }
