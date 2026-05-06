"""add continuation procurement flag

Revision ID: f4c2a1b7e9d3
Revises: e2b8c9d1a4f0
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c2a1b7e9d3"
down_revision: Union[str, None] = "e2b8c9d1a4f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bid_results",
        sa.Column("is_continuation_procurement", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "device_price_catalogs",
        sa.Column("is_continuation_procurement", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(
        "idx_bid_results_is_continuation_procurement",
        "bid_results",
        ["is_continuation_procurement"],
    )
    op.create_index(
        "idx_device_price_catalogs_is_continuation_procurement",
        "device_price_catalogs",
        ["is_continuation_procurement"],
    )


def downgrade() -> None:
    op.drop_index("idx_device_price_catalogs_is_continuation_procurement", table_name="device_price_catalogs")
    op.drop_index("idx_bid_results_is_continuation_procurement", table_name="bid_results")
    op.drop_column("device_price_catalogs", "is_continuation_procurement")
    op.drop_column("bid_results", "is_continuation_procurement")
