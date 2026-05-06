"""baseline existing schema

Revision ID: 30be1bfc7ce9
Revises: 
Create Date: 2026-04-28 17:56:08.342339
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector



revision: str = '30be1bfc7ce9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_records",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_type", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "source_type in ('file', 'url', 'manual')",
            name="source_records_source_type_check",
        ),
    )
    op.create_index("idx_source_records_source_type", "source_records", ["source_type"])

    op.create_table(
        "parsed_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_record_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("clean_text", sa.Text(), nullable=True),
        sa.Column("parse_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_parsed_documents_province", "parsed_documents", ["province"])
    op.create_index("idx_parsed_documents_publish_date", "parsed_documents", ["publish_date"])

    op.create_table(
        "procurement_projects",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_name", sa.Text(), nullable=False),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("alliance_name", sa.Text(), nullable=True),
        sa.Column("batch_no", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("standard_name", sa.Text(), nullable=False),
        sa.Column("alias_name", sa.Text(), nullable=True),
        sa.Column("category_level_1", sa.Text(), nullable=True),
        sa.Column("category_level_2", sa.Text(), nullable=True),
        sa.Column("category_level_3", sa.Text(), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("registration_no", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "enterprises",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("standard_name", sa.Text(), nullable=False),
        sa.Column("alias_name", sa.Text(), nullable=True),
        sa.Column("enterprise_type", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "bid_results",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("product_id", sa.BigInteger(), nullable=True),
        sa.Column("enterprise_id", sa.BigInteger(), nullable=True),
        sa.Column("source_record_id", sa.BigInteger(), nullable=True),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("winning_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("planned_volume", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_volume", sa.Numeric(18, 4), nullable=True),
        sa.Column("price_unit", sa.Text(), nullable=True),
        sa.Column("volume_unit", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("execution_start_date", sa.Date(), nullable=True),
        sa.Column("execution_end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enterprise_id"], ["enterprises.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["procurement_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_bid_results_province", "bid_results", ["province"])
    op.create_index("idx_bid_results_publish_date", "bid_results", ["publish_date"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("policy_type", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["parsed_documents.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("idx_document_chunks_province", "document_chunks", ["province"])

    op.create_table(
        "qa_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("route_type", sa.Text(), nullable=True),
        sa.Column("sql_query", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("qa_logs")
    op.drop_index("idx_document_chunks_province", table_name="document_chunks")
    op.drop_index("idx_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("idx_bid_results_publish_date", table_name="bid_results")
    op.drop_index("idx_bid_results_province", table_name="bid_results")
    op.drop_table("bid_results")
    op.drop_table("enterprises")
    op.drop_table("products")
    op.drop_table("procurement_projects")
    op.drop_index("idx_parsed_documents_publish_date", table_name="parsed_documents")
    op.drop_index("idx_parsed_documents_province", table_name="parsed_documents")
    op.drop_table("parsed_documents")
    op.drop_index("idx_source_records_source_type", table_name="source_records")
    op.drop_table("source_records")
