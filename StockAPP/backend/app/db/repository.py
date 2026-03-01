"""Repository layer for market data persistence."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from .models import DailyBar, IndexComponent, Instrument, SyncCheckpoint, SyncJob
from .session import session_scope


def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    return None


def infer_market(code: str) -> str:
    code = str(code).strip().replace("sh", "").replace("sz", "")
    if code.startswith(("6", "5", "9")):
        return "SH"
    if code.startswith(("0", "1", "2", "3")):
        return "SZ"
    return ""


def normalize_security_type(security_type: str) -> str:
    st = (security_type or "").strip().upper()
    if st in {"ETF", "STOCK", "INDEX"}:
        return st
    return "STOCK"


class MarketDataRepository:
    """Encapsulates all SQL writes/reads for market data."""

    def _upsert_instrument(
        self,
        code: str,
        security_type: str,
        name: str = "",
        market: Optional[str] = None,
        industry: str = "",
        source: str = "unknown",
    ) -> int:
        security_type = normalize_security_type(security_type)
        code = str(code).strip().zfill(6)
        market = (market or infer_market(code)).upper()

        with session_scope() as session:
            stmt = mysql_insert(Instrument).values(
                code=code,
                market=market,
                security_type=security_type,
                name=name or "",
                industry=industry or "",
                source=source,
                is_active=True,
            )
            stmt = stmt.on_duplicate_key_update(
                name=stmt.inserted.name,
                industry=stmt.inserted.industry,
                source=stmt.inserted.source,
                is_active=True,
                updated_at=func.now(),
            )
            session.execute(stmt)

            instrument_id = session.execute(
                select(Instrument.id).where(
                    and_(
                        Instrument.code == code,
                        Instrument.market == market,
                        Instrument.security_type == security_type,
                    )
                )
            ).scalar_one()
            return int(instrument_id)

    def find_instrument(
        self,
        code: str,
        security_type: str,
        market: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        code = str(code).strip().zfill(6)
        security_type = normalize_security_type(security_type)
        market = (market or infer_market(code)).upper()
        with session_scope() as session:
            row = session.execute(
                select(Instrument).where(
                    and_(
                        Instrument.code == code,
                        Instrument.market == market,
                        Instrument.security_type == security_type,
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return {
                "id": int(row.id),
                "code": row.code,
                "market": row.market,
                "security_type": row.security_type,
                "name": row.name,
                "industry": row.industry,
                "source": row.source,
            }

    def get_or_create_instrument(
        self,
        code: str,
        security_type: str,
        name: str = "",
        market: Optional[str] = None,
        industry: str = "",
        source: str = "unknown",
    ) -> int:
        return self._upsert_instrument(
            code=code,
            security_type=security_type,
            name=name,
            market=market,
            industry=industry,
            source=source,
        )

    def upsert_instruments(self, rows: Sequence[Dict[str, Any]], source: str = "unknown") -> int:
        if not rows:
            return 0
        values: List[Dict[str, Any]] = []
        for row in rows:
            code = str(row.get("code", "")).strip()
            if not code:
                continue
            code = code.zfill(6)
            security_type = normalize_security_type(str(row.get("security_type", "STOCK")))
            market = str(row.get("market") or infer_market(code)).upper()
            values.append(
                {
                    "code": code,
                    "market": market,
                    "security_type": security_type,
                    "name": str(row.get("name", "") or ""),
                    "industry": str(row.get("industry", "") or ""),
                    "source": str(row.get("source") or source),
                    "is_active": bool(row.get("is_active", True)),
                }
            )

        if not values:
            return 0

        with session_scope() as session:
            stmt = mysql_insert(Instrument).values(values)
            stmt = stmt.on_duplicate_key_update(
                name=stmt.inserted.name,
                industry=stmt.inserted.industry,
                source=stmt.inserted.source,
                is_active=stmt.inserted.is_active,
                updated_at=func.now(),
            )
            result = session.execute(stmt)
            return int(result.rowcount or 0)

    def get_daily_bars(
        self,
        code: str,
        security_type: str,
        start_date: str,
        end_date: str,
        period: str = "1d",
        adjust_type: str = "qfq",
    ) -> List[Dict[str, Any]]:
        security_type = normalize_security_type(security_type)
        start = _to_date(start_date)
        end = _to_date(end_date)
        if start is None or end is None:
            return []

        market = infer_market(code)
        with session_scope() as session:
            instrument = session.execute(
                select(Instrument).where(
                    and_(
                        Instrument.code == str(code).strip().zfill(6),
                        Instrument.market == market,
                        Instrument.security_type == security_type,
                    )
                )
            ).scalar_one_or_none()
            if instrument is None:
                return []

            rows = session.execute(
                select(DailyBar, Instrument.name)
                .join(Instrument, Instrument.id == DailyBar.instrument_id)
                .where(
                    and_(
                        DailyBar.instrument_id == instrument.id,
                        DailyBar.trade_date >= start,
                        DailyBar.trade_date <= end,
                        DailyBar.period == period,
                        DailyBar.adjust_type == adjust_type,
                    )
                )
                .order_by(DailyBar.trade_date.asc())
            ).all()

            result: List[Dict[str, Any]] = []
            for bar, name in rows:
                result.append(
                    {
                        "date": bar.trade_date.isoformat(),
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": int(bar.volume or 0),
                        "amount": float(bar.amount or 0),
                        "amplitude": float(bar.amplitude or 0),
                        "pct_change": float(bar.pct_change or 0),
                        "change_amount": float(bar.change_amount or 0),
                        "turnover": float(bar.turnover or 0),
                        "name": name or "",
                    }
                )
            return result

    def get_daily_bar_bounds(
        self,
        code: str,
        security_type: str,
        period: str = "1d",
        adjust_type: str = "qfq",
    ) -> Optional[Dict[str, Any]]:
        security_type = normalize_security_type(security_type)
        market = infer_market(code)
        with session_scope() as session:
            instrument = session.execute(
                select(Instrument.id).where(
                    and_(
                        Instrument.code == str(code).strip().zfill(6),
                        Instrument.market == market,
                        Instrument.security_type == security_type,
                    )
                )
            ).scalar_one_or_none()
            if instrument is None:
                return None

            row = session.execute(
                select(
                    func.min(DailyBar.trade_date),
                    func.max(DailyBar.trade_date),
                    func.count(DailyBar.id),
                ).where(
                    and_(
                        DailyBar.instrument_id == instrument,
                        DailyBar.period == period,
                        DailyBar.adjust_type == adjust_type,
                    )
                )
            ).one()
            if row[2] == 0:
                return None
            return {
                "min_date": row[0].isoformat() if row[0] else None,
                "max_date": row[1].isoformat() if row[1] else None,
                "count": int(row[2] or 0),
            }

    def upsert_daily_bars(
        self,
        code: str,
        security_type: str,
        bars: Sequence[Dict[str, Any]],
        name: str = "",
        market: Optional[str] = None,
        industry: str = "",
        period: str = "1d",
        adjust_type: str = "qfq",
        source: str = "unknown",
    ) -> int:
        if not bars:
            return 0

        instrument_id = self._upsert_instrument(
            code=code,
            security_type=security_type,
            name=name,
            market=market,
            industry=industry,
            source=source,
        )

        values: List[Dict[str, Any]] = []
        for bar in bars:
            trade_date = _to_date(bar.get("date"))
            if trade_date is None:
                continue
            values.append(
                {
                    "instrument_id": instrument_id,
                    "trade_date": trade_date,
                    "period": period,
                    "adjust_type": adjust_type,
                    "open": Decimal(str(bar.get("open", 0))),
                    "high": Decimal(str(bar.get("high", 0))),
                    "low": Decimal(str(bar.get("low", 0))),
                    "close": Decimal(str(bar.get("close", 0))),
                    "volume": int(float(bar.get("volume", 0) or 0)),
                    "amount": Decimal(str(bar.get("amount", 0) or 0)),
                    "amplitude": Decimal(str(bar.get("amplitude", 0) or 0)),
                    "pct_change": Decimal(str(bar.get("pct_change", 0) or 0)),
                    "change_amount": Decimal(str(bar.get("change_amount", bar.get("change", 0) or 0))),
                    "turnover": Decimal(str(bar.get("turnover", 0) or 0)),
                    "source": source,
                    "ingested_at": datetime.now(),
                }
            )

        if not values:
            return 0

        with session_scope() as session:
            stmt = mysql_insert(DailyBar).values(values)
            stmt = stmt.on_duplicate_key_update(
                open=stmt.inserted.open,
                high=stmt.inserted.high,
                low=stmt.inserted.low,
                close=stmt.inserted.close,
                volume=stmt.inserted.volume,
                amount=stmt.inserted.amount,
                amplitude=stmt.inserted.amplitude,
                pct_change=stmt.inserted.pct_change,
                change_amount=stmt.inserted.change_amount,
                turnover=stmt.inserted.turnover,
                source=stmt.inserted.source,
                ingested_at=stmt.inserted.ingested_at,
            )
            result = session.execute(stmt)
            return int(result.rowcount or 0)

    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        with session_scope() as session:
            rows = session.execute(
                select(Instrument)
                .where(
                    and_(
                        Instrument.security_type == "STOCK",
                        or_(
                            Instrument.code == kw,
                            Instrument.code.like(f"{kw}%"),
                            Instrument.name.like(f"%{kw}%"),
                        ),
                    )
                )
                .order_by(Instrument.code.asc())
                .limit(limit)
            ).scalars().all()

            return [
                {
                    "code": row.code,
                    "name": row.name,
                    "market": row.market,
                    "industry": row.industry,
                }
                for row in rows
            ]

    def start_sync_job(self, job_type: str, payload: Optional[Dict[str, Any]] = None) -> str:
        job_id = uuid.uuid4().hex
        with session_scope() as session:
            session.execute(
                mysql_insert(SyncJob).values(
                    job_id=job_id,
                    job_type=job_type,
                    status="running",
                    payload_json=payload or {},
                    started_at=datetime.now(),
                )
            )
        return job_id

    def finish_sync_job(
        self,
        job_id: str,
        status: str,
        stats: Optional[Dict[str, Any]] = None,
        error_text: Optional[str] = None,
    ) -> None:
        with session_scope() as session:
            session.execute(
                SyncJob.__table__.update()
                .where(SyncJob.job_id == job_id)
                .values(
                    status=status,
                    ended_at=datetime.now(),
                    stats_json=stats or {},
                    error_text=error_text,
                )
            )

    def get_last_success_sync_time(self) -> Optional[str]:
        with session_scope() as session:
            value = session.execute(
                select(func.max(SyncJob.ended_at)).where(SyncJob.status == "success")
            ).scalar_one_or_none()
            return value.isoformat() if value else None

    def get_cache_stats(self) -> Dict[str, Any]:
        with session_scope() as session:
            row_count = int(session.execute(select(func.count(DailyBar.id))).scalar_one() or 0)
            symbol_count = int(session.execute(select(func.count(func.distinct(DailyBar.instrument_id)))).scalar_one() or 0)
            last_bar_time = session.execute(select(func.max(DailyBar.ingested_at))).scalar_one_or_none()
            last_sync = session.execute(
                select(func.max(SyncJob.ended_at)).where(SyncJob.status == "success")
            ).scalar_one_or_none()
            return {
                "row_count": row_count,
                "symbol_count": symbol_count,
                "last_sync_at": (last_sync or last_bar_time).isoformat() if (last_sync or last_bar_time) else None,
            }

    def get_checkpoint(self, code: str, security_type: str, source: str = "update_service") -> Optional[str]:
        security_type = normalize_security_type(security_type)
        market = infer_market(code)
        with session_scope() as session:
            instrument_id = session.execute(
                select(Instrument.id).where(
                    and_(
                        Instrument.code == str(code).strip().zfill(6),
                        Instrument.market == market,
                        Instrument.security_type == security_type,
                    )
                )
            ).scalar_one_or_none()
            if instrument_id is None:
                return None
            row = session.execute(
                select(SyncCheckpoint.last_synced_date).where(
                    and_(
                        SyncCheckpoint.instrument_id == instrument_id,
                        SyncCheckpoint.source == source,
                    )
                )
            ).scalar_one_or_none()
            return row.isoformat() if row else None

    def upsert_checkpoint(
        self,
        code: str,
        security_type: str,
        last_synced_date: str,
        source: str = "update_service",
        name: str = "",
    ) -> None:
        instrument_id = self._upsert_instrument(
            code=code,
            security_type=security_type,
            name=name,
            source=source,
        )
        last_date = _to_date(last_synced_date)
        with session_scope() as session:
            stmt = mysql_insert(SyncCheckpoint).values(
                instrument_id=instrument_id,
                source=source,
                last_synced_date=last_date,
                last_success_at=datetime.now(),
            )
            stmt = stmt.on_duplicate_key_update(
                last_synced_date=stmt.inserted.last_synced_date,
                last_success_at=stmt.inserted.last_success_at,
            )
            session.execute(stmt)

    def upsert_index_components(
        self,
        index_code: str,
        component_codes: Sequence[str],
        trade_date: Optional[str] = None,
        source: str = "unknown",
    ) -> int:
        if not component_codes:
            return 0

        resolved_date = _to_date(trade_date) or date.today()
        index_id = self._upsert_instrument(
            code=index_code,
            security_type="INDEX",
            name=index_code,
            source=source,
        )
        component_ids: List[int] = []
        for code in component_codes:
            component_ids.append(
                self._upsert_instrument(
                    code=str(code).strip().zfill(6),
                    security_type="STOCK",
                    name=str(code).strip().zfill(6),
                    source=source,
                )
            )

        values = [
            {
                "index_instrument_id": index_id,
                "component_instrument_id": component_id,
                "trade_date": resolved_date,
                "weight": None,
                "source": source,
                "ingested_at": datetime.now(),
            }
            for component_id in component_ids
        ]

        with session_scope() as session:
            stmt = mysql_insert(IndexComponent).values(values)
            stmt = stmt.on_duplicate_key_update(
                weight=stmt.inserted.weight,
                source=stmt.inserted.source,
                ingested_at=stmt.inserted.ingested_at,
            )
            result = session.execute(stmt)
            return int(result.rowcount or 0)
