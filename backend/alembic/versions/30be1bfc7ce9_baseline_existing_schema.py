"""baseline existing schema

Revision ID: 30be1bfc7ce9
Revises: 
Create Date: 2026-04-28 17:56:08.342339
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '30be1bfc7ce9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
