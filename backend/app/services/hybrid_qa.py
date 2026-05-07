import json
import hashlib
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.factory import get_llm_provider
from app.models import Enterprise, HybridQACache, HybridSessionContext
from app.schemas import HybridQuestionResponse, QueryExecutionResult, QueryPlan, RAGCitation
from app.services.freeform_qa import answer_freeform_question
from app.services.rag_qa import retrieve_relevant_chunks


@dataclass
class HybridContext:
    last_enterprise_name: str | None = None
    last_project_name: str | None = None
    last_procurement_unit: str | None = None
    last_structured_rows: list[dict] = field(default_factory=list)
    last_citations: list[dict] = field(default_factory=list)


def answer_hybrid_question(db: Session, question: str, session_id: str, limit: int = 6) -> HybridQuestionResponse:
    context = load_context(db, session_id)
    contextual_question = resolve_context(question, context)
    cached = get_cached_response(db, question, session_id, contextual_question, context)
    if cached:
        return cached

    structured = answer_freeform_question(db, contextual_question, session_id)
    update_context_from_structured(context, structured.result)

    enterprise = find_enterprise_name(db, contextual_question) or context.last_enterprise_name
    rag_query = build_rag_query(contextual_question, structured.answer, enterprise)
    citations = retrieve_relevant_chunks(
        db,
        question=rag_query,
        limit=limit,
        document_type=None,
        source_category=None,
        content_scope=None,
        research_type=None,
        evidence_level=None,
        medical_device_field="吻合器",
        company_name=None,
    )
    context.last_citations = [citation.model_dump() for citation in citations]

    answer = compose_hybrid_answer(contextual_question, structured.answer, structured.result, citations)
    confidence = "high" if structured.result.rows and citations else "medium" if structured.result.rows or citations else "low"
    response = HybridQuestionResponse(
        question=question,
        session_id=session_id,
        answer=answer,
        query_plan=structured.query_plan,
        result=structured.result,
        citations=citations,
        assumptions=[
            *structured.assumptions,
            "hybrid: 先查询集采结构化数据，再召回RAG资料并综合回答",
            "市场份额没有真实采购量/销量字段时，只能做方向性判断",
        ],
        sources=["device_price_catalogs", "document_chunks", "parsed_documents"],
        confidence=confidence,
        context=context_to_dict(context),
    )
    save_context(db, session_id, context)
    cache_response(db, contextual_question, context, response)
    return response


def load_context(db: Session, session_id: str) -> HybridContext:
    stored = db.get(HybridSessionContext, session_id)
    if not stored:
        return HybridContext()
    return HybridContext(
        last_enterprise_name=stored.last_enterprise_name,
        last_project_name=stored.last_project_name,
        last_procurement_unit=stored.last_procurement_unit,
        last_structured_rows=stored.last_structured_rows or [],
        last_citations=stored.last_citations or [],
    )


def save_context(db: Session, session_id: str, context: HybridContext) -> None:
    stored = db.get(HybridSessionContext, session_id)
    if not stored:
        stored = HybridSessionContext(session_id=session_id)
        db.add(stored)
    stored.last_enterprise_name = context.last_enterprise_name
    stored.last_project_name = context.last_project_name
    stored.last_procurement_unit = context.last_procurement_unit
    stored.last_structured_rows = context.last_structured_rows
    stored.last_citations = context.last_citations
    db.commit()


def get_cached_response(
    db: Session,
    original_question: str,
    session_id: str,
    contextual_question: str,
    context: HybridContext,
) -> HybridQuestionResponse | None:
    now = datetime.now(timezone.utc)
    cached = db.get(HybridQACache, cache_key(contextual_question, context))
    if not cached or cached.expires_at <= now:
        return None
    payload = dict(cached.payload)
    payload["question"] = original_question
    payload["session_id"] = session_id
    payload["context"] = context_to_dict(context)
    return HybridQuestionResponse.model_validate(payload)


def cache_response(db: Session, contextual_question: str, context: HybridContext, response: HybridQuestionResponse) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    db.execute(delete(HybridQACache).where(HybridQACache.expires_at <= now))
    payload = response.model_dump(mode="json")
    payload["question"] = contextual_question
    cached = HybridQACache(
        cache_key=cache_key(contextual_question, context),
        question=contextual_question,
        payload=payload,
        expires_at=now + timedelta(seconds=settings.hybrid_cache_ttl_seconds),
    )
    db.merge(cached)
    db.commit()


def cache_key(question: str, context: HybridContext) -> str:
    return hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()


def resolve_context(question: str, context: HybridContext) -> str:
    result = question
    if context.last_enterprise_name and any(token in result for token in ["它", "其", "该企业", "这家", "这家公司", "这个品牌"]):
        result = result.replace("它", context.last_enterprise_name).replace("其", context.last_enterprise_name)
    if context.last_project_name and any(token in result for token in ["该项目", "这个项目", "刚才项目"]):
        result = result.replace("该项目", context.last_project_name).replace("这个项目", context.last_project_name).replace("刚才项目", context.last_project_name)
    return result


def build_rag_query(question: str, structured_answer: str, enterprise: str | None) -> str:
    parts = [question, structured_answer]
    if enterprise:
        parts.append(enterprise)
    return "\n".join(parts)


def compose_hybrid_answer(
    question: str,
    structured_answer: str,
    result: QueryExecutionResult,
    citations: list[RAGCitation],
) -> str:
    llm_answer = compose_with_llm(question, structured_answer, result, citations)
    if llm_answer:
        return llm_answer

    lines = ["基于集采数据库和RAG资料综合看：", structured_answer]
    if citations:
        titles = "、".join(citation.title or citation.source_name or f"资料{citation.document_id}" for citation in citations[:3])
        lines.append(f"可参考的RAG资料包括：{titles}。")
        lines.append("这些资料可以补充解释价格、产品结构、政策环境和企业策略，但不能替代结构化集采价格本身。")
    else:
        lines.append("当前没有召回到足够相关的RAG资料，因此只能基于集采结构化数据作判断。")
    return "\n".join(lines)


def compose_with_llm(
    question: str,
    structured_answer: str,
    result: QueryExecutionResult,
    citations: list[RAGCitation],
) -> str:
    context = "\n\n".join(
        f"[RAG资料{index}] 标题：{item.title or item.source_name or '未命名'}\n"
        f"来源分类：{item.source_category or ''} / {item.content_scope or ''}\n"
        f"内容：{item.snippet}"
        for index, item in enumerate(citations[:5], start=1)
    )
    prompt = f"""
你是医疗器械集采与市场洞察分析助手。请同时使用“集采结构化查询结果”和“RAG资料”回答用户。

要求：
- 先给结论，再分开说明“集采数据依据”和“RAG资料补充”。
- 如果结构化数据和RAG资料没有直接对应关系，要明确区分，不要强行推导。
- linked_price 是联动价格，不是严格中标价。
- 当前数据库没有真实采购量、销量或市场份额字段；涉及市场份额只能做方向性分析。
- 回答必须体现两类数据如何互相补充。
- 不要输出 Markdown 表格。
- 控制在 4 到 8 句话。

用户问题：
{question}

集采结构化回答：
{structured_answer}

集采查询结果前10行：
{json.dumps(result.rows[:10], ensure_ascii=False)}

RAG资料：
{context or "未召回到相关RAG资料"}
""".strip()
    try:
        return get_llm_provider().generate_text(prompt).strip()
    except Exception:
        return ""


def update_context_from_structured(context: HybridContext, result: QueryExecutionResult) -> None:
    context.last_structured_rows = result.rows[:20]
    for row in result.rows:
        enterprise = row.get("applicant_enterprise") or row.get("manufacturer")
        if isinstance(enterprise, str) and enterprise:
            context.last_enterprise_name = enterprise
            break
    for row in result.rows:
        project = row.get("project_name")
        if isinstance(project, str) and project:
            context.last_project_name = project
            break
    for row in result.rows:
        unit = row.get("procurement_unit")
        if isinstance(unit, str) and unit:
            context.last_procurement_unit = unit
            break


def find_enterprise_name(db: Session, question: str) -> str | None:
    names = db.execute(select(Enterprise.standard_name).distinct()).scalars().all()
    matches = [name for name in names if name and name in question]
    if matches:
        return sorted(matches, key=len, reverse=True)[0]
    aliases = {
        "瑞奇": "天津瑞奇外科器械股份有限公司",
        "健适瑞奇": "天津瑞奇外科器械股份有限公司",
        "强生": "强生（上海）医疗器材有限公司",
        "爱惜康": "强生（上海）医疗器材有限公司",
        "派尔特": "北京派尔特医疗科技股份有限公司",
        "逸思": "逸思（苏州）医疗科技有限公司",
    }
    for alias, canonical in aliases.items():
        if alias in question:
            return canonical
    return None


def context_to_dict(context: HybridContext) -> dict:
    return {
        "last_enterprise_name": context.last_enterprise_name,
        "last_project_name": context.last_project_name,
        "last_procurement_unit": context.last_procurement_unit,
        "last_structured_rows": context.last_structured_rows,
        "last_citation_count": len(context.last_citations),
    }
