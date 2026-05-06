from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.embeddings.base import EmbeddingProvider
from app.ingestion.chunking import chunk_text
from app.models import DocumentChunk, ParsedDocument


def create_chunks_for_document(
    db: Session,
    document: ParsedDocument,
    max_chars: int = 800,
    overlap_chars: int = 80,
    replace_existing: bool = True,
) -> list[DocumentChunk]:
    if replace_existing:
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    text = document.clean_text or ""
    chunks = [
        DocumentChunk(
            document_id=document.id,
            chunk_text=value,
            section_title=None,
            chunk_index=index,
            province=document.province,
            publish_date=document.publish_date,
            effective_date=document.effective_date,
            policy_type=document.document_type,
            source_name=document.source_name,
            medical_device_field=document.medical_device_field,
            company_name=document.company_name,
            tags=document.tags,
            confidentiality=document.confidentiality,
        )
        for index, value in enumerate(chunk_text(text, max_chars=max_chars, overlap_chars=overlap_chars))
    ]

    db.add_all(chunks)
    db.commit()
    for chunk in chunks:
        db.refresh(chunk)
    return chunks


def list_document_chunks(db: Session, document_id: int, limit: int = 100, offset: int = 0) -> tuple[list[DocumentChunk], int]:
    total = db.execute(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).scalar_one()
    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return chunks, total


def embed_chunks_for_document(db: Session, document_id: int, provider: EmbeddingProvider) -> int:
    chunks = db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index.asc())
    ).scalars().all()

    for chunk in chunks:
        chunk.embedding = provider.embed_document(chunk.chunk_text)

    db.commit()
    return len(chunks)


def vector_search_chunks(
    db: Session,
    query_embedding: list[float],
    limit: int = 5,
    province: str | None = None,
    policy_type: str | None = None,
    medical_device_field: str | None = None,
    company_name: str | None = None,
):
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    statement = select(DocumentChunk, distance).where(DocumentChunk.embedding.is_not(None))
    if province:
        statement = statement.where(DocumentChunk.province == province)
    if policy_type:
        statement = statement.where(DocumentChunk.policy_type == policy_type)
    if medical_device_field:
        statement = statement.where(DocumentChunk.medical_device_field == medical_device_field)
    if company_name:
        statement = statement.where(DocumentChunk.company_name == company_name)
    statement = statement.order_by(distance).limit(limit)
    return db.execute(statement).all()
