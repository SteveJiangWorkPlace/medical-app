import json

from sqlalchemy.orm import Session

from app.llm.factory import get_llm_provider
from app.query_planning.executor import execute_query_plan
from app.query_planning.planner import plan_query
from app.query_planning.validator import QueryPlanValidationError, validate_query_plan
from app.schemas import FreeformQuestionResponse, QueryPlan


def answer_freeform_question(db: Session, question: str, session_id: str) -> FreeformQuestionResponse:
    llm = get_llm_provider()
    plan, _ = plan_query(question, llm)
    try:
        plan = validate_query_plan(plan)
    except QueryPlanValidationError as exc:
        plan = QueryPlan(
            intent="clarify",
            clarification_question=str(exc),
            assumptions=[*plan.assumptions, "query_plan_validation_failed"],
        )

    result = execute_query_plan(db, plan)
    answer = compose_answer(question, plan, result, llm)
    return FreeformQuestionResponse(
        question=question,
        session_id=session_id,
        answer=answer,
        query_plan=plan,
        result=result,
        assumptions=plan.assumptions,
        sources=["device_price_catalogs"],
        confidence="high" if plan.intent != "clarify" else "low",
    )


def compose_answer(question: str, plan: QueryPlan, result, llm=None) -> str:
    if plan.intent == "clarify":
        return plan.clarification_question or "我需要更多信息才能回答这个问题。"
    if not result.rows:
        return "没有查询到符合条件的数据。"

    if llm is not None:
        generated = compose_answer_with_llm(question, plan, result, llm)
        if generated:
            return generated

    first = result.rows[0]
    if plan.intent == "rank":
        group_parts = [str(first.get(field)) for field in plan.group_by if first.get(field) is not None]
        metric_keys = [key for key in first.keys() if key not in plan.group_by]
        metric_key = metric_keys[-1] if metric_keys else "value"
        metric_name = human_field_name(metric_key)
        return f"从当前数据库看，排名第一的是{' / '.join(group_parts)}，{metric_name}为 {format_value(first.get(metric_key))}。"
    if plan.intent == "aggregate":
        if plan.group_by:
            lines = [f"我按{', '.join(human_field_name(field) for field in plan.group_by)}做了分组统计，共得到 {result.total} 组结果。"]
            for row in result.rows[:5]:
                label = " / ".join(str(row.get(field)) for field in plan.group_by if row.get(field) is not None)
                metric_key = next((key for key in row.keys() if key not in plan.group_by), "")
                lines.append(f"{label}：{human_field_name(metric_key)}为 {format_value(row.get(metric_key))}")
            return "\n".join(lines)
        key = result.columns[-1] if result.columns else "value"
        return f"当前数据库中，{human_field_name(key)}为 {format_value(first.get(key))}。"
    if plan.intent in {"filter", "detail"}:
        lines = [f"我查到了 {result.total} 条相关记录，下面列出前 {len(result.rows)} 条："]
        for index, row in enumerate(result.rows[:20], start=1):
            model = row.get("model") or "型号未标注"
            price = row.get("linked_price")
            enterprise = row.get("applicant_enterprise")
            unit = row.get("procurement_unit")
            parts = [f"{index}. {model}"]
            if price is not None:
                parts.append(f"联动价 {format_value(price)} 元")
            if enterprise:
                parts.append(f"申报企业：{enterprise}")
            if unit:
                parts.append(f"采购单元：{unit}")
            lines.append("，".join(parts))
        return "\n".join(lines)
    return "已完成查询。"


def compose_answer_with_llm(question: str, plan: QueryPlan, result, llm) -> str:
    rows = result.rows[:12]
    prompt = f"""
你是医疗科技市场数据分析助手。请基于给定数据库查询结果，用中文自然语言回答用户问题。

要求：
- 不要编造数据库中没有的信息。
- 如果字段是 linked_price，要说明这是“联动价格”，不是严格中标价。
- 如果 metric 是 catalog_count，要说明数量口径是“目录条目数”，不是采购量。
- 回答要像 AI 对话，先给结论，再给必要补充。
- 如果用户要求“列出”“有哪些”“所有”，必须把查询结果中的关键条目直接写进回答正文。
- 不要输出 Markdown 表格。
- 控制在 2 到 8 句话；如果是列表型问题，可以逐行列出前 10 条。

用户问题：
{question}

查询计划：
{json.dumps(plan.model_dump(), ensure_ascii=False)}

查询结果：
{json.dumps(rows, ensure_ascii=False)}
""".strip()
    try:
        text = llm.generate_text(prompt).strip()
    except Exception:
        return ""
    return text


def human_field_name(field: str) -> str:
    names = {
        "catalog_count": "目录条目数",
        "linked_price": "联动价格",
        "avg_linked_price": "平均联动价格",
        "max_linked_price": "最高联动价格",
        "min_linked_price": "最低联动价格",
        "sum_linked_price": "联动价格合计",
        "medical_device_field": "医疗器械领域",
        "procurement_unit": "采购单元",
        "applicant_enterprise": "申报企业",
        "manufacturer": "生产企业",
    }
    return names.get(field, field)


def format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)
