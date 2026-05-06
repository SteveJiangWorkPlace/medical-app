"""add medical device field metadata

Revision ID: 8b4f1a2c9d6e
Revises: 4d1734fe9136
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b4f1a2c9d6e"
down_revision: Union[str, None] = "4d1734fe9136"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("procurement_projects", sa.Column("medical_device_field", sa.Text(), nullable=True))
    op.add_column("bid_results", sa.Column("medical_device_field", sa.Text(), nullable=True))
    op.add_column("device_price_catalogs", sa.Column("medical_device_field", sa.Text(), nullable=True))

    op.execute(
        """
        update procurement_projects
        set medical_device_field = '吻合器'
        where project_name like '%吻合器%'
           or project_name like '%缝合器%'
           or project_name like '%腔镜切割吻%'
        """
    )
    op.execute(
        """
        update bid_results
        set medical_device_field = '吻合器'
        where project_name like '%吻合器%'
           or project_name like '%缝合器%'
           or procurement_unit like '%吻合器%'
           or procurement_unit like '%缝合器%'
        """
    )
    op.execute(
        """
        update device_price_catalogs
        set medical_device_field = '吻合器'
        where project_name like '%吻合器%'
           or project_name like '%缝合器%'
           or procurement_unit like '%吻合器%'
           or procurement_unit like '%缝合器%'
        """
    )


def downgrade() -> None:
    op.drop_column("device_price_catalogs", "medical_device_field")
    op.drop_column("bid_results", "medical_device_field")
    op.drop_column("procurement_projects", "medical_device_field")
