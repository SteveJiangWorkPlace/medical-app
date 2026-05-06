"""add rag document metadata

Revision ID: c7a31f2e4b90
Revises: 8b4f1a2c9d6e
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7a31f2e4b90"
down_revision: Union[str, None] = "8b4f1a2c9d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("parsed_documents", sa.Column("source_name", sa.Text(), nullable=True))
    op.add_column("parsed_documents", sa.Column("medical_device_field", sa.Text(), nullable=True))
    op.add_column("parsed_documents", sa.Column("company_name", sa.Text(), nullable=True))
    op.add_column("parsed_documents", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("parsed_documents", sa.Column("confidentiality", sa.Text(), nullable=True))

    op.add_column("document_chunks", sa.Column("source_name", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("medical_device_field", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("company_name", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("document_chunks", sa.Column("confidentiality", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "confidentiality")
    op.drop_column("document_chunks", "tags")
    op.drop_column("document_chunks", "company_name")
    op.drop_column("document_chunks", "medical_device_field")
    op.drop_column("document_chunks", "source_name")

    op.drop_column("parsed_documents", "confidentiality")
    op.drop_column("parsed_documents", "tags")
    op.drop_column("parsed_documents", "company_name")
    op.drop_column("parsed_documents", "medical_device_field")
    op.drop_column("parsed_documents", "source_name")
