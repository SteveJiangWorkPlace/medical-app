from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import QALog
from app.schemas import (
    AnalysisQuestionRequest,
    AnalysisQuestionResponse,
    FreeformQuestionRequest,
    FreeformQuestionResponse,
    HybridQuestionRequest,
    HybridQuestionResponse,
    QueryPlanRequest,
    QueryPlanResponse,
    StructuredQuestionRequest,
    StructuredQuestionResponse,
)
from app.llm.factory import get_llm_provider
from app.query_planning.planner import plan_query
from app.query_planning.validator import QueryPlanValidationError, validate_query_plan
from app.services.analysis_qa import answer_analysis_question
from app.services.freeform_qa import answer_freeform_question
from app.services.hybrid_qa import answer_hybrid_question
from app.services.structured_qa import answer_structured_question


router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/structured", response_model=StructuredQuestionResponse)
def structured_qa_endpoint(
    payload: StructuredQuestionRequest,
    db: Session = Depends(get_db),
) -> StructuredQuestionResponse:
    result = answer_structured_question(db, payload.question)
    log = QALog(
        question=payload.question,
        route_type=result.route_type,
        answer=result.answer,
        sources={"tables": result.sources, "confidence": result.confidence},
    )
    db.add(log)
    db.commit()
    return result


@router.post("/analysis", response_model=AnalysisQuestionResponse)
def analysis_qa_endpoint(
    payload: AnalysisQuestionRequest,
    db: Session = Depends(get_db),
) -> AnalysisQuestionResponse:
    result = answer_analysis_question(db, payload.question, payload.session_id)
    log = QALog(
        question=payload.question,
        route_type=result.intent,
        answer=result.answer,
        sources={"tables": result.sources, "confidence": result.confidence, "session_id": payload.session_id},
    )
    db.add(log)
    db.commit()
    return result


@router.post("/query-plan", response_model=QueryPlanResponse)
def query_plan_endpoint(payload: QueryPlanRequest) -> QueryPlanResponse:
    llm = get_llm_provider()
    plan, raw = plan_query(payload.question, llm)
    try:
        plan = validate_query_plan(plan)
    except QueryPlanValidationError as exc:
        plan.intent = "clarify"
        plan.clarification_question = str(exc)
    return QueryPlanResponse(
        question=payload.question,
        session_id=payload.session_id,
        query_plan=plan,
        raw_response=raw,
    )


@router.post("/freeform", response_model=FreeformQuestionResponse)
def freeform_qa_endpoint(
    payload: FreeformQuestionRequest,
    db: Session = Depends(get_db),
) -> FreeformQuestionResponse:
    result = answer_freeform_question(db, payload.question, payload.session_id)
    log = QALog(
        question=payload.question,
        route_type=f"freeform:{result.query_plan.intent}",
        answer=result.answer,
        sources={
            "tables": result.sources,
            "confidence": result.confidence,
            "session_id": payload.session_id,
            "query_plan": result.query_plan.model_dump(),
        },
    )
    db.add(log)
    db.commit()
    return result


@router.post("/hybrid", response_model=HybridQuestionResponse)
def hybrid_qa_endpoint(
    payload: HybridQuestionRequest,
    db: Session = Depends(get_db),
) -> HybridQuestionResponse:
    result = answer_hybrid_question(db, payload.question, payload.session_id, payload.limit)
    log = QALog(
        question=payload.question,
        route_type=f"hybrid:{result.query_plan.intent}",
        answer=result.answer,
        sources={
            "tables": result.sources,
            "confidence": result.confidence,
            "session_id": payload.session_id,
            "query_plan": result.query_plan.model_dump(),
            "citations": [citation.model_dump() for citation in result.citations],
            "context": result.context,
        },
    )
    db.add(log)
    db.commit()
    return result
