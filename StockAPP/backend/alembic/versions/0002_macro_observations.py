"""create macro observations table

Revision ID: 0002_macro_observations
Revises: 0001_market_storage
Create Date: 2026-03-01 00:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_macro_observations"
down_revision = "0001_market_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "macro_observations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("api_name", sa.String(length=64), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=191), nullable=False, server_default=""),
        sa.Column("obs_date", sa.Date(), nullable=True),
        sa.Column("obs_month", sa.String(length=6), nullable=True),
        sa.Column("obs_quarter", sa.String(length=8), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("api_name", "period_key", "dimension_key", name="uq_macro_observations"),
    )
    op.create_index("idx_macro_obs_api_period", "macro_observations", ["api_name", "period_key"])
    op.create_index("idx_macro_obs_date", "macro_observations", ["obs_date"])
    op.create_index("idx_macro_obs_month", "macro_observations", ["obs_month"])
    op.create_index("idx_macro_obs_quarter", "macro_observations", ["obs_quarter"])


def downgrade() -> None:
    op.drop_index("idx_macro_obs_quarter", table_name="macro_observations")
    op.drop_index("idx_macro_obs_month", table_name="macro_observations")
    op.drop_index("idx_macro_obs_date", table_name="macro_observations")
    op.drop_index("idx_macro_obs_api_period", table_name="macro_observations")
    op.drop_table("macro_observations")
