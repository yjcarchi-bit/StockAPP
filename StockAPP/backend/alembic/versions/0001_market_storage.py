"""create market storage tables

Revision ID: 0001_market_storage
Revises:
Create Date: 2026-03-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_market_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("market", sa.String(length=8), nullable=False),
        sa.Column("security_type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("industry", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", "market", "security_type", name="uq_instrument_code_market_type"),
    )
    op.create_index("idx_instruments_name", "instruments", ["name"])

    op.create_table(
        "daily_bars",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("instrument_id", sa.BigInteger(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False, server_default="1d"),
        sa.Column("adjust_type", sa.String(length=8), nullable=False, server_default="qfq"),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("amplitude", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("pct_change", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("change_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("turnover", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("instrument_id", "trade_date", "adjust_type", "period", name="uq_daily_bars"),
    )
    op.create_index("idx_daily_bars_instrument_trade_date", "daily_bars", ["instrument_id", "trade_date"])
    op.create_index("idx_daily_bars_trade_date", "daily_bars", ["trade_date"])

    op.create_table(
        "index_components",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("index_instrument_id", sa.BigInteger(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_instrument_id", sa.BigInteger(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("weight", sa.Numeric(12, 6), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "index_instrument_id",
            "component_instrument_id",
            "trade_date",
            name="uq_index_components",
        ),
    )

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index("idx_sync_jobs_job_type_status", "sync_jobs", ["job_type", "status"])

    op.create_table(
        "sync_checkpoints",
        sa.Column("instrument_id", sa.BigInteger(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_synced_date", sa.Date(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("instrument_id", "source", name="pk_sync_checkpoints"),
    )


def downgrade() -> None:
    op.drop_table("sync_checkpoints")
    op.drop_index("idx_sync_jobs_job_type_status", table_name="sync_jobs")
    op.drop_table("sync_jobs")
    op.drop_table("index_components")
    op.drop_index("idx_daily_bars_trade_date", table_name="daily_bars")
    op.drop_index("idx_daily_bars_instrument_trade_date", table_name="daily_bars")
    op.drop_table("daily_bars")
    op.drop_index("idx_instruments_name", table_name="instruments")
    op.drop_table("instruments")
