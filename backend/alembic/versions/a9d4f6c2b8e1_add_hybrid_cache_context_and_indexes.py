"""add hybrid cache context and indexes

Revision ID: a9d4f6c2b8e1
Revises: f4c2a1b7e9d3
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a9d4f6c2b8e1"
down_revision: Union[str, None] = "f4c2a1b7e9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hybrid_session_contexts",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("last_enterprise_name", sa.Text(), nullable=True),
        sa.Column("last_project_name", sa.Text(), nullable=True),
        sa.Column("last_procurement_unit", sa.Text(), nullable=True),
        sa.Column("last_structured_rows", postgresql.JSONB(), nullable=True),
        sa.Column("last_citations", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "hybrid_qa_cache",
        sa.Column("cache_key", sa.Text(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "api_rate_limits",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("bucket_key", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bucket_key", "window_start", name="uq_api_rate_limits_bucket_window"),
    )

    create_index_if_not_exists("idx_device_price_catalogs_project_name", "device_price_catalogs", "project_name")
    create_index_if_not_exists("idx_device_price_catalogs_procurement_unit", "device_price_catalogs", "procurement_unit")
    create_index_if_not_exists("idx_device_price_catalogs_linked_price", "device_price_catalogs", "linked_price")
    create_index_if_not_exists(
        "idx_device_price_catalogs_applicant_enterprise_id",
        "device_price_catalogs",
        "applicant_enterprise_id",
    )
    create_index_if_not_exists("idx_device_price_catalogs_manufacturer_id", "device_price_catalogs", "manufacturer_id")
    create_index_if_not_exists("idx_device_price_catalogs_medical_device_field", "device_price_catalogs", "medical_device_field")
    create_index_if_not_exists("idx_document_chunks_source_category", "document_chunks", "source_category")
    create_index_if_not_exists("idx_document_chunks_medical_device_field", "document_chunks", "medical_device_field")
    create_index_if_not_exists("idx_parsed_documents_source_category", "parsed_documents", "source_category")
    create_index_if_not_exists("idx_parsed_documents_medical_device_field", "parsed_documents", "medical_device_field")
    create_index_if_not_exists("idx_hybrid_qa_cache_expires_at", "hybrid_qa_cache", "expires_at")
    create_index_if_not_exists("idx_api_rate_limits_bucket_key", "api_rate_limits", "bucket_key")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_api_rate_limits_bucket_key")
    op.execute("DROP INDEX IF EXISTS idx_hybrid_qa_cache_expires_at")
    op.execute("DROP INDEX IF EXISTS idx_parsed_documents_medical_device_field")
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_medical_device_field")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_medical_device_field")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_manufacturer_id")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_applicant_enterprise_id")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_linked_price")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_procurement_unit")
    op.execute("DROP INDEX IF EXISTS idx_device_price_catalogs_project_name")
    op.drop_table("api_rate_limits")
    op.drop_table("hybrid_qa_cache")
    op.drop_table("hybrid_session_contexts")


def create_index_if_not_exists(index_name: str, table_name: str, column_name: str) -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})")
