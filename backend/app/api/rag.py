from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RAGQuestionRequest, RAGQuestionResponse
from app.security import require_admin_api_key
from app.services.rag_qa import answer_rag_question


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RAGQuestionResponse)
def rag_ask_endpoint(
    payload: RAGQuestionRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> RAGQuestionResponse:
    return answer_rag_question(
        db,
        question=payload.question,
        session_id=payload.session_id,
        limit=payload.limit,
        document_type=payload.document_type,
        source_category=payload.source_category,
        content_scope=payload.content_scope,
        research_type=payload.research_type,
        evidence_level=payload.evidence_level,
        medical_device_field=payload.medical_device_field,
        company_name=payload.company_name,
    )
