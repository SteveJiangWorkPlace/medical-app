from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.embeddings.factory import get_embedding_provider
from app.schemas import VectorSearchRequest, VectorSearchResponse, VectorSearchResult
from app.services.document_chunks import vector_search_chunks


router = APIRouter(prefix="/search", tags=["search"])


@router.post("/vector", response_model=VectorSearchResponse)
def vector_search_endpoint(payload: VectorSearchRequest, db: Session = Depends(get_db)) -> VectorSearchResponse:
    provider = get_embedding_provider()
    query_embedding = provider.embed_query(payload.query)
    rows = vector_search_chunks(
        db,
        query_embedding=query_embedding,
        limit=payload.limit,
        province=payload.province,
        policy_type=payload.policy_type,
        medical_device_field=payload.medical_device_field,
        company_name=payload.company_name,
    )
    items = [
        VectorSearchResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_text=chunk.chunk_text,
            distance=float(distance),
            province=chunk.province,
            policy_type=chunk.policy_type,
            source_name=chunk.source_name,
            medical_device_field=chunk.medical_device_field,
            company_name=chunk.company_name,
            publish_date=chunk.publish_date,
        )
        for chunk, distance in rows
    ]
    return VectorSearchResponse(items=items, total=len(items))
