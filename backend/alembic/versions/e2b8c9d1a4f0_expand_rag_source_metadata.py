"""expand rag source metadata

Revision ID: e2b8c9d1a4f0
Revises: c7a31f2e4b90
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2b8c9d1a4f0"
down_revision: Union[str, None] = "c7a31f2e4b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


METADATA_COLUMNS = [
    "source_category",
    "source_channel",
    "publisher",
    "publisher_type",
    "author",
    "source_url",
    "content_scope",
    "research_type",
    "evidence_level",
    "geographic_scope",
]


def upgrade() -> None:
    for table_name in ("parsed_documents", "document_chunks"):
        for column_name in METADATA_COLUMNS:
            op.add_column(table_name, sa.Column(column_name, sa.Text(), nullable=True))

    op.create_index("idx_parsed_documents_source_category", "parsed_documents", ["source_category"])
    op.create_index("idx_parsed_documents_content_scope", "parsed_documents", ["content_scope"])
    op.create_index("idx_document_chunks_source_category", "document_chunks", ["source_category"])
    op.create_index("idx_document_chunks_content_scope", "document_chunks", ["content_scope"])
    op.create_index("idx_document_chunks_research_type", "document_chunks", ["research_type"])
    op.create_index("idx_document_chunks_evidence_level", "document_chunks", ["evidence_level"])

    op.execute(
        """
        update parsed_documents
        set source_category = case
                when coalesce(title, '') like '%访谈%' or coalesce(source_name, '') like '%访谈%' then 'expert_interview'
                when coalesce(title, '') like '%新闻%' or coalesce(source_name, '') like '%新闻%' then 'industry_news'
                when coalesce(company_name, '') <> '' then 'company_report'
                else 'industry_report'
            end,
            source_channel = case
                when coalesce(title, '') like '%访谈%' or coalesce(source_name, '') like '%访谈%' then 'internal_note'
                when coalesce(title, '') like '%新闻%' or coalesce(source_name, '') like '%新闻%' then 'news_media'
                else 'manual_upload'
            end,
            publisher_type = case
                when coalesce(company_name, '') <> '' then 'brand'
                else 'internal'
            end,
            content_scope = case
                when coalesce(company_name, '') <> '' then 'brand'
                else 'industry'
            end,
            research_type = case
                when coalesce(title, '') like '%访谈%' or coalesce(source_name, '') like '%访谈%' then 'primary'
                when coalesce(title, '') like '%新闻%' or coalesce(source_name, '') like '%新闻%' then 'news'
                else 'secondary'
            end,
            evidence_level = case
                when coalesce(title, '') like '%官网%' or coalesce(source_name, '') like '%官网%' then 'official'
                when coalesce(title, '') like '%访谈%' or coalesce(source_name, '') like '%访谈%' then 'medium'
                else 'unknown'
            end
        where source_category is null
        """
    )
    op.execute(
        """
        update document_chunks as chunk
        set source_category = document.source_category,
            source_channel = document.source_channel,
            publisher = document.publisher,
            publisher_type = document.publisher_type,
            author = document.author,
            source_url = document.source_url,
            content_scope = document.content_scope,
            research_type = document.research_type,
            evidence_level = document.evidence_level,
            geographic_scope = document.geographic_scope
        from parsed_documents as document
        where chunk.document_id = document.id
        """
    )


def downgrade() -> None:
    op.drop_index("idx_document_chunks_evidence_level", table_name="document_chunks")
    op.drop_index("idx_document_chunks_research_type", table_name="document_chunks")
    op.drop_index("idx_document_chunks_content_scope", table_name="document_chunks")
    op.drop_index("idx_document_chunks_source_category", table_name="document_chunks")
    op.drop_index("idx_parsed_documents_content_scope", table_name="parsed_documents")
    op.drop_index("idx_parsed_documents_source_category", table_name="parsed_documents")

    for table_name in ("document_chunks", "parsed_documents"):
        for column_name in reversed(METADATA_COLUMNS):
            op.drop_column(table_name, column_name)
