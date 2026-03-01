"""create financial observations table

Revision ID: 0003_financial_observations
Revises: 0002_macro_observations
Create Date: 2026-03-01 23:45:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_financial_observations"
down_revision = "0002_macro_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_observations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("api_name", sa.String(length=64), nullable=False),
        sa.Column("ts_code", sa.String(length=16), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=191), nullable=False, server_default=""),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("api_name", "ts_code", "period_key", "dimension_key", name="uq_financial_observations"),
    )
    op.create_index(
        "idx_financial_obs_api_code_period",
        "financial_observations",
        ["api_name", "ts_code", "period_key"],
    )
    op.create_index("idx_financial_obs_ts_code", "financial_observations", ["ts_code"])
    op.create_index("idx_financial_obs_ann_date", "financial_observations", ["ann_date"])
    op.create_index("idx_financial_obs_end_date", "financial_observations", ["end_date"])


def downgrade() -> None:
    op.drop_index("idx_financial_obs_end_date", table_name="financial_observations")
    op.drop_index("idx_financial_obs_ann_date", table_name="financial_observations")
    op.drop_index("idx_financial_obs_ts_code", table_name="financial_observations")
    op.drop_index("idx_financial_obs_api_code_period", table_name="financial_observations")
    op.drop_table("financial_observations")
