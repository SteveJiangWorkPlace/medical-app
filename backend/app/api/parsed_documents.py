from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import get_settings
from app.embeddings.factory import get_embedding_provider
from app.security import require_admin_api_key
from app.schemas import (
    ChunkDocumentRequest,
    DocumentChunkList,
    EmbedDocumentRequest,
    EmbedDocumentResponse,
    ParsedDocumentCreate,
    ParsedDocumentList,
    ParsedDocumentRead,
)
from app.services.document_chunks import create_chunks_for_document, embed_chunks_for_document, list_document_chunks
from app.services.parsed_documents import create_parsed_document, get_parsed_document, list_parsed_documents


router = APIRouter(prefix="/parsed-documents", tags=["parsed documents"])


@router.post("", response_model=ParsedDocumentRead, status_code=status.HTTP_201_CREATED)
def create_parsed_document_endpoint(
    payload: ParsedDocumentCreate,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> ParsedDocumentRead:
    return create_parsed_document(db, payload)


@router.get("", response_model=ParsedDocumentList)
def list_parsed_documents_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> ParsedDocumentList:
    documents, total = list_parsed_documents(db, limit=limit, offset=offset)
    return ParsedDocumentList(items=documents, total=total)


@router.get("/{document_id}", response_model=ParsedDocumentRead)
def get_parsed_document_endpoint(
    document_id: int,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> ParsedDocumentRead:
    document = get_parsed_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")
    return document


@router.post("/{document_id}/chunks", response_model=DocumentChunkList, status_code=status.HTTP_201_CREATED)
def create_document_chunks_endpoint(
    document_id: int,
    payload: ChunkDocumentRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> DocumentChunkList:
    document = get_parsed_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")
    chunks = create_chunks_for_document(
        db,
        document,
        max_chars=payload.max_chars,
        overlap_chars=payload.overlap_chars,
        replace_existing=payload.replace_existing,
    )
    return DocumentChunkList(items=chunks, total=len(chunks))


@router.get("/{document_id}/chunks", response_model=DocumentChunkList)
def list_document_chunks_endpoint(
    document_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> DocumentChunkList:
    if get_parsed_document(db, document_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")
    chunks, total = list_document_chunks(db, document_id=document_id, limit=limit, offset=offset)
    return DocumentChunkList(items=chunks, total=total)


@router.post("/{document_id}/embed", response_model=EmbedDocumentResponse)
def embed_document_chunks_endpoint(
    document_id: int,
    _: EmbedDocumentRequest,
    __: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> EmbedDocumentResponse:
    if get_parsed_document(db, document_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")
    provider = get_embedding_provider()
    embedded_count = embed_chunks_for_document(db, document_id=document_id, provider=provider)
    settings = get_settings()
    return EmbedDocumentResponse(
        document_id=document_id,
        embedded_chunks=embedded_count,
        provider=settings.embedding_provider,
        dimensions=provider.dimensions,
    )
