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

    op.create_index("idx_device_price_catalogs_project_name", "device_price_catalogs", ["project_name"])
    op.create_index("idx_device_price_catalogs_procurement_unit", "device_price_catalogs", ["procurement_unit"])
    op.create_index("idx_device_price_catalogs_linked_price", "device_price_catalogs", ["linked_price"])
    op.create_index("idx_device_price_catalogs_applicant_enterprise_id", "device_price_catalogs", ["applicant_enterprise_id"])
    op.create_index("idx_device_price_catalogs_manufacturer_id", "device_price_catalogs", ["manufacturer_id"])
    op.create_index("idx_device_price_catalogs_medical_device_field", "device_price_catalogs", ["medical_device_field"])
    op.create_index("idx_document_chunks_source_category", "document_chunks", ["source_category"])
    op.create_index("idx_document_chunks_medical_device_field", "document_chunks", ["medical_device_field"])
    op.create_index("idx_parsed_documents_source_category", "parsed_documents", ["source_category"])
    op.create_index("idx_parsed_documents_medical_device_field", "parsed_documents", ["medical_device_field"])
    op.create_index("idx_hybrid_qa_cache_expires_at", "hybrid_qa_cache", ["expires_at"])
    op.create_index("idx_api_rate_limits_bucket_key", "api_rate_limits", ["bucket_key"])


def downgrade() -> None:
    op.drop_index("idx_api_rate_limits_bucket_key", table_name="api_rate_limits")
    op.drop_index("idx_hybrid_qa_cache_expires_at", table_name="hybrid_qa_cache")
    op.drop_index("idx_parsed_documents_medical_device_field", table_name="parsed_documents")
    op.drop_index("idx_parsed_documents_source_category", table_name="parsed_documents")
    op.drop_index("idx_document_chunks_medical_device_field", table_name="document_chunks")
    op.drop_index("idx_document_chunks_source_category", table_name="document_chunks")
    op.drop_index("idx_device_price_catalogs_medical_device_field", table_name="device_price_catalogs")
    op.drop_index("idx_device_price_catalogs_manufacturer_id", table_name="device_price_catalogs")
    op.drop_index("idx_device_price_catalogs_applicant_enterprise_id", table_name="device_price_catalogs")
    op.drop_index("idx_device_price_catalogs_linked_price", table_name="device_price_catalogs")
    op.drop_index("idx_device_price_catalogs_procurement_unit", table_name="device_price_catalogs")
    op.drop_index("idx_device_price_catalogs_project_name", table_name="device_price_catalogs")
    op.drop_table("api_rate_limits")
    op.drop_table("hybrid_qa_cache")
    op.drop_table("hybrid_session_contexts")
