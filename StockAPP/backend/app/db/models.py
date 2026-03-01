"""Database models for market storage."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    security_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("code", "market", "security_type", name="uq_instrument_code_market_type"),
        Index("idx_instruments_name", "name"),
    )


class DailyBar(Base):
    __tablename__ = "daily_bars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    trade_date: Mapped[Date] = mapped_column(Date, nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False, default="1d")
    adjust_type: Mapped[str] = mapped_column(String(8), nullable=False, default="qfq")

    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    amplitude: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    pct_change: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    change_amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    turnover: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    ingested_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("instrument_id", "trade_date", "adjust_type", "period", name="uq_daily_bars"),
        Index("idx_daily_bars_instrument_trade_date", "instrument_id", "trade_date"),
        Index("idx_daily_bars_trade_date", "trade_date"),
    )


class IndexComponent(Base):
    __tablename__ = "index_components"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    index_instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    trade_date: Mapped[Date] = mapped_column(Date, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(12, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    ingested_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "index_instrument_id",
            "component_instrument_id",
            "trade_date",
            name="uq_index_components",
        ),
    )


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    ended_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    stats_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_sync_jobs_job_type_status", "job_type", "status"),)


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"

    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source: Mapped[str] = mapped_column(String(32), primary_key=True, default="update_service")
    last_synced_date: Mapped[Date] = mapped_column(Date, nullable=True)
    last_success_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)


__all__ = [
    "Instrument",
    "DailyBar",
    "IndexComponent",
    "SyncJob",
    "SyncCheckpoint",
]
