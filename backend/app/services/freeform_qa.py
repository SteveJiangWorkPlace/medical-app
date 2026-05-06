import json
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased

from app.llm.factory import get_llm_provider
from app.query_planning.executor import execute_query_plan
from app.query_planning.planner import plan_query
from app.query_planning.validator import QueryPlanValidationError, validate_query_plan
from app.models import DevicePriceCatalog, Enterprise
from app.schemas import FreeformQuestionResponse, QueryExecutionResult, QueryPlan, QueryFilter


ApplicantEnterprise = aliased(Enterprise)
ManufacturerEnterprise = aliased(Enterprise)


@dataclass
class FreeformContext:
    last_enterprise_name: str | None = None
    last_project_name: str | None = None
    extras: dict = field(default_factory=dict)


SESSION_CONTEXTS: dict[str, FreeformContext] = {}


def answer_freeform_question(db: Session, question: str, session_id: str) -> FreeformQuestionResponse:
    context = SESSION_CONTEXTS.setdefault(session_id, FreeformContext())
    contextual_question = resolve_contextual_question(db, question, context)
    special = answer_relative_enterprise_price(db, contextual_question, session_id, context)
    if special:
        return special

    llm = get_llm_provider()
    plan, _ = plan_query(contextual_question, llm)
    try:
        plan = validate_query_plan(plan)
    except QueryPlanValidationError as exc:
        plan = QueryPlan(
            intent="clarify",
            clarification_question=str(exc),
            assumptions=[*plan.assumptions, "query_plan_validation_failed"],
        )

    result = execute_query_plan(db, plan)
    update_context_from_result(context, result)
    answer = compose_answer(contextual_question, plan, result, llm)
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


def resolve_contextual_question(db: Session, question: str, context: FreeformContext) -> str:
    enterprise = find_enterprise_name(db, question)
    if enterprise:
        context.last_enterprise_name = enterprise
        return question
    if context.last_enterprise_name and any(token in question for token in ["它", "其", "该企业", "这家", "这家公司", "这个品牌"]):
        return question.replace("它", context.last_enterprise_name).replace("其", context.last_enterprise_name)
    return question


def answer_relative_enterprise_price(
    db: Session,
    question: str,
    session_id: str,
    context: FreeformContext,
) -> FreeformQuestionResponse | None:
    if not asks_relative_price(question):
        return None
    enterprise = find_enterprise_name(db, question) or context.last_enterprise_name
    if not enterprise:
        return None

    project_keyword = extract_project_keyword(question) or extract_project_keyword(context.last_project_name or "")
    rows = enterprise_price_rows(db, enterprise, project_keyword)
    if not rows:
        return None

    unit_rows = []
    for unit in sorted({row["procurement_unit"] for row in rows if row["procurement_unit"]}):
        unit_rows.extend(unit_price_comparison(db, enterprise, unit, project_keyword))

    enterprise_prices = [row["linked_price"] for row in rows if row["linked_price"] is not None]
    avg_price = sum(enterprise_prices) / len(enterprise_prices) if enterprise_prices else None
    rank_rows = enterprise_avg_price_rank(db, project_keyword)
    rank = next((index for index, row in enumerate(rank_rows, start=1) if row["enterprise_name"] == enterprise), None)

    total_enterprises = len(rank_rows)
    price_position = describe_price_position(rank, total_enterprises)
    project_scope = f"{project_keyword}项目" if project_keyword else "当前可比项目"
    answer_lines = [
        f"{enterprise} 在{project_scope}中不是“低价前10未出现=没有记录”，而是需要单独看它自己的价格和全体分布。",
        f"当前查到该企业 {len(rows)} 条目录记录，联动价格范围为 {format_value(min(enterprise_prices))} 至 {format_value(max(enterprise_prices))} 元，平均约 {format_value(avg_price)} 元。",
    ]
    if rank:
        answer_lines.append(f"按企业平均联动价格从低到高排序，它位于第 {rank}/{total_enterprises}，整体属于{price_position}。")
    if unit_rows:
        samples = "; ".join(
            f"{item['procurement_unit']}：本企业均价 {format_value(item['enterprise_avg_price'])} 元，同单元全体均价 {format_value(item['market_avg_price'])} 元"
            for item in unit_rows[:3]
        )
        answer_lines.append(f"同采购单元对比看，{samples}。")
    answer_lines.append(
        "对市场份额的影响需要谨慎：数据库没有真实采购量或销量字段，只能用目录条目数近似观察覆盖面。价格偏高通常会降低纯价格竞争优势，但如果对应电动枪身/钉仓等更高端产品，可能反映产品结构和技术溢价，不能直接等同于份额下降。"
    )

    result_rows = [
        {
            "applicant_enterprise": enterprise,
            "project_name": row["project_name"],
            "procurement_unit": row["procurement_unit"],
            "model": row["model"],
            "linked_price": row["linked_price"],
        }
        for row in rows[:20]
    ]
    plan = QueryPlan(
        intent="compare",
        metric="linked_price",
        aggregation="avg",
        group_by=["applicant_enterprise"],
        filters=[QueryFilter(field="applicant_enterprise", operator="contains", value=enterprise)],
        order_by="linked_price",
        order="asc",
        limit=20,
        assumptions=[
            "价格按联动价格 linked_price 统计",
            "相对价格先计算目标企业自身价格，再与同项目/同采购单元分布比较",
            "市场份额不能由当前价格目录直接推导，目录条目数只能作为覆盖面 proxy",
        ],
    )
    result = QueryExecutionResult(
        columns=["applicant_enterprise", "project_name", "procurement_unit", "model", "linked_price"],
        rows=result_rows,
        total=len(rows),
    )
    context.last_enterprise_name = enterprise
    if rows[0].get("project_name"):
        context.last_project_name = rows[0]["project_name"]
    return FreeformQuestionResponse(
        question=question,
        session_id=session_id,
        answer="\n".join(answer_lines),
        query_plan=plan,
        result=result,
        assumptions=plan.assumptions,
        sources=["device_price_catalogs"],
        confidence="high",
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


def asks_relative_price(question: str) -> bool:
    has_price = any(token in question for token in ["价格", "联动价", "报价", "贵", "便宜"])
    has_compare = any(token in question for token in ["相对", "其他品牌", "其他企业", "对比", "比较", "排名", "咋样", "如何"])
    has_share = any(token in question for token in ["市场份额", "份额", "影响"])
    return (has_price and has_compare) or has_share


def find_enterprise_name(db: Session, question: str) -> str | None:
    names = db.execute(select(Enterprise.standard_name).distinct()).scalars().all()
    direct_matches = [name for name in names if name and name in question]
    if direct_matches:
        return sorted(direct_matches, key=len, reverse=True)[0]

    aliases = {
        "瑞奇": "天津瑞奇外科器械股份有限公司",
        "健适瑞奇": "天津瑞奇外科器械股份有限公司",
        "强生": "强生（上海）医疗器材有限公司",
        "爱惜康": "强生（上海）医疗器材有限公司",
        "派尔特": "北京派尔特医疗科技股份有限公司",
    }
    for alias, canonical in aliases.items():
        if alias in question:
            match = db.execute(
                select(Enterprise.standard_name)
                .where(Enterprise.standard_name.ilike(f"%{alias}%"))
                .order_by(Enterprise.standard_name.asc())
                .limit(1)
            ).scalar_one_or_none()
            return match or canonical
    return None


def extract_project_keyword(text: str) -> str | None:
    if not text:
        return None
    for keyword in ["京津冀", "重庆", "湖南", "福建"]:
        if keyword in text:
            return keyword
    return None


def enterprise_price_rows(db: Session, enterprise: str, project_keyword: str | None) -> list[dict]:
    statement = (
        select(
            DevicePriceCatalog.project_name,
            DevicePriceCatalog.procurement_unit,
            DevicePriceCatalog.model,
            DevicePriceCatalog.linked_price,
        )
        .select_from(DevicePriceCatalog)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(or_(ApplicantEnterprise.standard_name == enterprise, ManufacturerEnterprise.standard_name == enterprise))
        .where(DevicePriceCatalog.linked_price.is_not(None))
    )
    if project_keyword:
        statement = statement.where(DevicePriceCatalog.project_name.ilike(f"%{project_keyword}%"))
    rows = db.execute(statement.order_by(DevicePriceCatalog.linked_price.asc())).all()
    return [
        {
            "project_name": project_name,
            "procurement_unit": procurement_unit,
            "model": model,
            "linked_price": float(linked_price),
        }
        for project_name, procurement_unit, model, linked_price in rows
    ]


def unit_price_comparison(db: Session, enterprise: str, procurement_unit: str, project_keyword: str | None) -> list[dict]:
    statement = (
        select(
            func.avg(DevicePriceCatalog.linked_price).filter(
                or_(ApplicantEnterprise.standard_name == enterprise, ManufacturerEnterprise.standard_name == enterprise)
            ),
            func.avg(DevicePriceCatalog.linked_price),
            func.min(DevicePriceCatalog.linked_price),
            func.max(DevicePriceCatalog.linked_price),
            func.count(DevicePriceCatalog.id),
        )
        .select_from(DevicePriceCatalog)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(DevicePriceCatalog.procurement_unit == procurement_unit)
        .where(DevicePriceCatalog.linked_price.is_not(None))
    )
    if project_keyword:
        statement = statement.where(DevicePriceCatalog.project_name.ilike(f"%{project_keyword}%"))
    row = db.execute(statement).one()
    enterprise_avg, market_avg, market_min, market_max, count = row
    if enterprise_avg is None:
        return []
    return [
        {
            "procurement_unit": procurement_unit,
            "enterprise_avg_price": float(enterprise_avg),
            "market_avg_price": float(market_avg) if market_avg is not None else None,
            "market_min_price": float(market_min) if market_min is not None else None,
            "market_max_price": float(market_max) if market_max is not None else None,
            "catalog_count": count,
        }
    ]


def enterprise_avg_price_rank(db: Session, project_keyword: str | None) -> list[dict]:
    statement = (
        select(
            ApplicantEnterprise.standard_name,
            func.avg(DevicePriceCatalog.linked_price).label("avg_price"),
            func.count(DevicePriceCatalog.id),
        )
        .select_from(DevicePriceCatalog)
        .join(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .where(DevicePriceCatalog.linked_price.is_not(None))
        .group_by(ApplicantEnterprise.standard_name)
    )
    if project_keyword:
        statement = statement.where(DevicePriceCatalog.project_name.ilike(f"%{project_keyword}%"))
    rows = db.execute(statement.order_by("avg_price")).all()
    return [
        {"enterprise_name": enterprise, "avg_price": float(avg_price), "catalog_count": count}
        for enterprise, avg_price, count in rows
    ]


def describe_price_position(rank: int | None, total: int) -> str:
    if not rank or not total:
        return "无法判断"
    percentile = rank / total
    if percentile <= 0.33:
        return "偏低价格带"
    if percentile <= 0.66:
        return "中间价格带"
    return "偏高价格带"


def update_context_from_result(context: FreeformContext, result: QueryExecutionResult) -> None:
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
