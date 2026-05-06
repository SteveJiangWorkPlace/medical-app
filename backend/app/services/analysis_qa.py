from dataclasses import dataclass, field

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import DevicePriceCatalog, Enterprise
from app.schemas import AnalysisQuestionResponse


ApplicantEnterprise = aliased(Enterprise)
ManufacturerEnterprise = aliased(Enterprise)


@dataclass
class ConversationContext:
    last_enterprise_name: str | None = None
    last_procurement_unit: str | None = None
    last_medical_insurance_code: str | None = None
    last_intent: str | None = None
    extras: dict = field(default_factory=dict)


SESSION_CONTEXTS: dict[str, ConversationContext] = {}


def answer_analysis_question(db: Session, question: str, session_id: str) -> AnalysisQuestionResponse:
    context = SESSION_CONTEXTS.setdefault(session_id, ConversationContext())
    text = question.strip()

    if refers_to_last_entity(text) and context.last_enterprise_name:
        return answer_enterprise_followup(db, question, session_id, context.last_enterprise_name, context)

    enterprise = find_enterprise_name(db, text)
    if enterprise:
        context.last_enterprise_name = enterprise
        if contains_count_intent(text):
            return answer_enterprise_count(db, question, session_id, enterprise, context)
        return answer_enterprise_price_range(db, question, session_id, enterprise, context)

    if contains_enterprise_intent(text) and contains_count_intent(text):
        return answer_top_enterprise_by_count(db, question, session_id, context)

    if contains_enterprise_intent(text) and contains_lowest_intent(text):
        return answer_top_enterprise_by_price(db, question, session_id, context, lowest=True)

    if contains_enterprise_intent(text) and contains_highest_intent(text):
        return answer_top_enterprise_by_price(db, question, session_id, context, lowest=False)

    if "采购单元" in text and ("平均" in text or "均价" in text) and contains_highest_intent(text):
        return answer_top_procurement_unit_by_avg_price(db, question, session_id, context)

    if contains_highest_intent(text):
        return answer_top_item_by_price(db, question, session_id, context, lowest=False)

    if contains_lowest_intent(text):
        return answer_top_item_by_price(db, question, session_id, context, lowest=True)

    return response(
        question=question,
        session_id=session_id,
        intent="analysis_fallback",
        answer="我目前能回答价格最高/最低、企业条目数最多、采购单元均价最高，以及基于上一轮企业的追问。",
        data={},
        entities={},
        context=context_to_dict(context),
        confidence="low",
        note=current_data_note(),
    )


def answer_top_enterprise_by_price(
    db: Session,
    question: str,
    session_id: str,
    context: ConversationContext,
    lowest: bool,
) -> AnalysisQuestionResponse:
    aggregate_price = func.min(DevicePriceCatalog.linked_price) if lowest else func.max(DevicePriceCatalog.linked_price)
    order_by = aggregate_price.asc() if lowest else aggregate_price.desc()
    row = db.execute(
        select(ApplicantEnterprise.standard_name, aggregate_price.label("price"), func.count(DevicePriceCatalog.id))
        .join(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .group_by(ApplicantEnterprise.standard_name)
        .order_by(order_by)
        .limit(1)
    ).one()
    enterprise, price, count = row
    context.last_enterprise_name = enterprise
    context.last_intent = "top_enterprise_by_min_price" if lowest else "top_enterprise_by_max_price"
    data = {"enterprise_name": enterprise, "price": float(price), "catalog_count": count}
    direction = "最低" if lowest else "最高"
    return response(
        question,
        session_id,
        context.last_intent,
        f"按当前联动价格目录统计，{direction}价格企业是 {enterprise}，{direction}联动价格为 {float(price)} 元；该企业共有 {count} 条目录记录。",
        data,
        {"enterprise_name": enterprise},
        context,
        note=current_data_note(),
    )


def answer_top_enterprise_by_count(
    db: Session,
    question: str,
    session_id: str,
    context: ConversationContext,
) -> AnalysisQuestionResponse:
    row = db.execute(
        select(ApplicantEnterprise.standard_name, func.count(DevicePriceCatalog.id).label("catalog_count"))
        .join(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .group_by(ApplicantEnterprise.standard_name)
        .order_by(desc("catalog_count"))
        .limit(1)
    ).one()
    enterprise, count = row
    context.last_enterprise_name = enterprise
    context.last_intent = "top_enterprise_by_catalog_count"
    data = {"enterprise_name": enterprise, "catalog_count": count}
    return response(
        question,
        session_id,
        context.last_intent,
        f"按当前目录条目数统计，数量最多的是 {enterprise}，共有 {count} 条价格目录记录。",
        data,
        {"enterprise_name": enterprise},
        context,
        note="当前文件没有采购量字段，这里的“数量最多”按价格目录条目数统计，不代表实际中标数量或采购量。",
    )


def answer_top_procurement_unit_by_avg_price(
    db: Session,
    question: str,
    session_id: str,
    context: ConversationContext,
) -> AnalysisQuestionResponse:
    row = db.execute(
        select(
            DevicePriceCatalog.procurement_unit,
            func.avg(DevicePriceCatalog.linked_price).label("avg_price"),
            func.count(DevicePriceCatalog.id),
        )
        .group_by(DevicePriceCatalog.procurement_unit)
        .order_by(desc("avg_price"))
        .limit(1)
    ).one()
    unit, avg_price, count = row
    context.last_procurement_unit = unit
    context.last_intent = "top_procurement_unit_by_avg_price"
    data = {"procurement_unit": unit, "avg_price": float(avg_price), "catalog_count": count}
    return response(
        question,
        session_id,
        context.last_intent,
        f"平均联动价格最高的采购单元是 {unit}，平均价格约 {float(avg_price):.2f} 元，共 {count} 条记录。",
        data,
        {"procurement_unit": unit},
        context,
        note=current_data_note(),
    )


def answer_top_item_by_price(
    db: Session,
    question: str,
    session_id: str,
    context: ConversationContext,
    lowest: bool,
) -> AnalysisQuestionResponse:
    order = DevicePriceCatalog.linked_price.asc() if lowest else DevicePriceCatalog.linked_price.desc()
    row = db.execute(
        select(DevicePriceCatalog, ApplicantEnterprise.standard_name)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .order_by(order)
        .limit(1)
    ).one()
    catalog, enterprise = row
    context.last_enterprise_name = enterprise
    context.last_medical_insurance_code = catalog.medical_insurance_code
    context.last_intent = "top_item_by_min_price" if lowest else "top_item_by_max_price"
    data = catalog_data(catalog, enterprise)
    direction = "最低" if lowest else "最高"
    return response(
        question,
        session_id,
        context.last_intent,
        f"当前目录中{direction}联动价格为 {data['linked_price']} 元，对应企业 {enterprise}，产品为 {catalog.component_name}，型号 {catalog.model}。",
        data,
        {"enterprise_name": enterprise, "medical_insurance_code": catalog.medical_insurance_code},
        context,
        note=current_data_note(),
    )


def answer_enterprise_followup(
    db: Session,
    question: str,
    session_id: str,
    enterprise: str,
    context: ConversationContext,
) -> AnalysisQuestionResponse:
    if contains_count_intent(question):
        return answer_enterprise_count(db, question, session_id, enterprise, context)
    return answer_enterprise_price_range(db, question, session_id, enterprise, context)


def answer_enterprise_count(
    db: Session,
    question: str,
    session_id: str,
    enterprise: str,
    context: ConversationContext,
) -> AnalysisQuestionResponse:
    total = count_enterprise_catalogs(db, enterprise)
    context.last_enterprise_name = enterprise
    context.last_intent = "enterprise_catalog_count"
    data = {"enterprise_name": enterprise, "catalog_count": total}
    return response(
        question,
        session_id,
        context.last_intent,
        f"{enterprise} 在当前目录中共有 {total} 条价格目录记录。",
        data,
        {"enterprise_name": enterprise},
        context,
        note="当前文件没有采购量字段，这里的数量是目录条目数。",
    )


def answer_enterprise_price_range(
    db: Session,
    question: str,
    session_id: str,
    enterprise: str,
    context: ConversationContext,
) -> AnalysisQuestionResponse:
    row = db.execute(
        enterprise_base_query()
        .with_only_columns(
            func.count(DevicePriceCatalog.id),
            func.min(DevicePriceCatalog.linked_price),
            func.max(DevicePriceCatalog.linked_price),
            func.avg(DevicePriceCatalog.linked_price),
        )
        .where(enterprise_filter(enterprise))
    ).one()
    total, min_price, max_price, avg_price = row
    context.last_enterprise_name = enterprise
    context.last_intent = "enterprise_price_range"
    data = {
        "enterprise_name": enterprise,
        "catalog_count": total,
        "min_price": float(min_price) if min_price is not None else None,
        "max_price": float(max_price) if max_price is not None else None,
        "avg_price": float(avg_price) if avg_price is not None else None,
    }
    return response(
        question,
        session_id,
        context.last_intent,
        f"{enterprise} 共有 {total} 条目录记录，联动价格范围为 {data['min_price']} 至 {data['max_price']} 元，平均约 {data['avg_price']:.2f} 元。",
        data,
        {"enterprise_name": enterprise},
        context,
        note=current_data_note(),
    )


def count_enterprise_catalogs(db: Session, enterprise: str) -> int:
    return db.execute(
        enterprise_base_query()
        .with_only_columns(func.count(DevicePriceCatalog.id))
        .where(enterprise_filter(enterprise))
    ).scalar_one()


def enterprise_base_query():
    return (
        select(DevicePriceCatalog)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
    )


def enterprise_filter(enterprise: str):
    return or_(ApplicantEnterprise.standard_name == enterprise, ManufacturerEnterprise.standard_name == enterprise)


def find_enterprise_name(db: Session, question: str) -> str | None:
    names = db.execute(select(Enterprise.standard_name).distinct()).scalars().all()
    matches = [name for name in names if name and name in question]
    return sorted(matches, key=len, reverse=True)[0] if matches else None


def contains_enterprise_intent(text: str) -> bool:
    return any(token in text for token in ["哪家", "企业", "公司", "厂家", "申报企业", "生产企业"])


def contains_highest_intent(text: str) -> bool:
    return any(token in text for token in ["最高", "最大", "最贵", "高"])


def contains_lowest_intent(text: str) -> bool:
    return any(token in text for token in ["最低", "最小", "最便宜", "低"])


def contains_count_intent(text: str) -> bool:
    return any(token in text for token in ["数量最多", "最多", "多少个", "多少条", "数量", "几个", "多少款", "多少种"])


def refers_to_last_entity(text: str) -> bool:
    return any(token in text for token in ["它", "这家", "该企业", "这个企业", "这家公司", "其"])


def catalog_data(catalog: DevicePriceCatalog, enterprise: str | None) -> dict:
    return {
        "enterprise_name": enterprise,
        "procurement_unit": catalog.procurement_unit,
        "component_name": catalog.component_name,
        "model": catalog.model,
        "registration_no": catalog.registration_no,
        "medical_insurance_code": catalog.medical_insurance_code,
        "linked_price": float(catalog.linked_price) if catalog.linked_price is not None else None,
        "price_unit": catalog.price_unit,
    }


def context_to_dict(context: ConversationContext) -> dict:
    return {
        "last_enterprise_name": context.last_enterprise_name,
        "last_procurement_unit": context.last_procurement_unit,
        "last_medical_insurance_code": context.last_medical_insurance_code,
        "last_intent": context.last_intent,
    }


def current_data_note() -> str:
    return "当前数据字段为联动价格，不是严格意义的中标价；当前文件也没有采购量字段。"


def response(
    question: str,
    session_id: str,
    intent: str,
    answer: str,
    data: dict,
    entities: dict,
    context: ConversationContext,
    confidence: str = "high",
    note: str | None = None,
) -> AnalysisQuestionResponse:
    return AnalysisQuestionResponse(
        question=question,
        session_id=session_id,
        intent=intent,
        answer=answer,
        data=data,
        entities=entities,
        context=context_to_dict(context),
        sources=["device_price_catalogs"],
        confidence=confidence,
        note=note,
    )
