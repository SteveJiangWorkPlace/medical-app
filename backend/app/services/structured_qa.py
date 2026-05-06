import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import DevicePriceCatalog, Enterprise
from app.schemas import StructuredQuestionResponse
from app.services.price_catalogs import get_price_catalog_summary


ApplicantEnterprise = aliased(Enterprise)
ManufacturerEnterprise = aliased(Enterprise)


def answer_structured_question(db: Session, question: str) -> StructuredQuestionResponse:
    normalized = question.strip()

    medical_code = extract_medical_code(normalized)
    if medical_code:
        return answer_by_medical_code(db, question, medical_code)

    enterprise_name = find_enterprise_name(db, normalized)
    if enterprise_name:
        return answer_by_enterprise(db, question, enterprise_name)

    procurement_unit = find_procurement_unit(db, normalized)
    if procurement_unit:
        return answer_by_procurement_unit(db, question, procurement_unit)

    if any(token in normalized for token in ["多少条", "总数", "一共", "多少个", "数量"]):
        return answer_summary_count(db, question)

    if any(token in normalized for token in ["最高", "最低", "价格范围", "均价", "平均"]):
        return answer_price_summary(db, question)

    return fallback_keyword_search(db, question, normalized)


def answer_summary_count(db: Session, question: str) -> StructuredQuestionResponse:
    summary = get_price_catalog_summary(db)
    answer = (
        f"当前价格目录共 {summary.total} 条记录，覆盖 {summary.procurement_unit_count} 个采购单元、"
        f"{summary.applicant_enterprise_count} 家申报企业、{summary.medical_insurance_code_count} 个医保编码。"
    )
    return response(question, "price_catalog_summary", answer, summary.model_dump())


def answer_price_summary(db: Session, question: str) -> StructuredQuestionResponse:
    summary = get_price_catalog_summary(db)
    answer = (
        f"当前价格目录最低联动价格为 {summary.min_price} 元，最高联动价格为 {summary.max_price} 元，"
        f"平均联动价格约为 {summary.avg_price:.2f} 元。"
        if summary.avg_price is not None
        else "当前没有可统计的联动价格。"
    )
    return response(question, "price_catalog_price_summary", answer, summary.model_dump())


def answer_by_procurement_unit(db: Session, question: str, procurement_unit: str) -> StructuredQuestionResponse:
    row = db.execute(
        select(
            func.count(DevicePriceCatalog.id),
            func.min(DevicePriceCatalog.linked_price),
            func.max(DevicePriceCatalog.linked_price),
            func.avg(DevicePriceCatalog.linked_price),
            func.count(func.distinct(DevicePriceCatalog.applicant_enterprise_id)),
        ).where(DevicePriceCatalog.procurement_unit == procurement_unit)
    ).one()
    data = {
        "procurement_unit": procurement_unit,
        "total": row[0],
        "min_price": float(row[1]) if row[1] is not None else None,
        "max_price": float(row[2]) if row[2] is not None else None,
        "avg_price": float(row[3]) if row[3] is not None else None,
        "applicant_enterprise_count": row[4],
    }
    answer = (
        f"{procurement_unit} 共 {data['total']} 条价格记录，涉及 {data['applicant_enterprise_count']} 家申报企业；"
        f"联动价格范围为 {data['min_price']} 至 {data['max_price']} 元，平均约 {data['avg_price']:.2f} 元。"
    )
    return response(question, "price_catalog_procurement_unit", answer, data)


def answer_by_enterprise(db: Session, question: str, enterprise_name: str) -> StructuredQuestionResponse:
    statement = (
        select(
            func.count(DevicePriceCatalog.id),
            func.min(DevicePriceCatalog.linked_price),
            func.max(DevicePriceCatalog.linked_price),
            func.count(func.distinct(DevicePriceCatalog.medical_insurance_code)),
        )
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(or_(ApplicantEnterprise.standard_name == enterprise_name, ManufacturerEnterprise.standard_name == enterprise_name))
    )
    row = db.execute(statement).one()
    sample_rows = db.execute(
        select(DevicePriceCatalog.component_name, DevicePriceCatalog.model, DevicePriceCatalog.linked_price)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(or_(ApplicantEnterprise.standard_name == enterprise_name, ManufacturerEnterprise.standard_name == enterprise_name))
        .order_by(DevicePriceCatalog.id.asc())
        .limit(5)
    ).all()
    samples = [
        {"component_name": component_name, "model": model, "linked_price": float(price) if price is not None else None}
        for component_name, model, price in sample_rows
    ]
    data = {
        "enterprise_name": enterprise_name,
        "total": row[0],
        "min_price": float(row[1]) if row[1] is not None else None,
        "max_price": float(row[2]) if row[2] is not None else None,
        "medical_insurance_code_count": row[3],
        "samples": samples,
    }
    answer = (
        f"{enterprise_name} 在当前价格目录中共有 {data['total']} 条记录，覆盖 "
        f"{data['medical_insurance_code_count']} 个医保编码；联动价格范围为 {data['min_price']} 至 {data['max_price']} 元。"
    )
    return response(question, "price_catalog_enterprise", answer, data)


def answer_by_medical_code(db: Session, question: str, medical_code: str) -> StructuredQuestionResponse:
    row = db.execute(
        select(DevicePriceCatalog, ApplicantEnterprise.standard_name, ManufacturerEnterprise.standard_name)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(DevicePriceCatalog.medical_insurance_code == medical_code)
    ).one_or_none()
    if row is None:
        return response(
            question,
            "price_catalog_medical_code",
            f"未找到医保编码 {medical_code} 对应的价格目录记录。",
            {"medical_insurance_code": medical_code, "found": False},
            confidence="medium",
        )
    catalog, applicant, manufacturer = row
    data = {
        "medical_insurance_code": medical_code,
        "procurement_unit": catalog.procurement_unit,
        "component_name": catalog.component_name,
        "specification": catalog.specification,
        "model": catalog.model,
        "registration_no": catalog.registration_no,
        "linked_price": float(catalog.linked_price) if catalog.linked_price is not None else None,
        "price_unit": catalog.price_unit,
        "applicant_enterprise_name": applicant,
        "manufacturer_name": manufacturer,
    }
    answer = (
        f"医保编码 {medical_code} 对应 {catalog.component_name}，型号 {catalog.model}，"
        f"联动价格为 {data['linked_price']} {catalog.price_unit or '元'}；申报企业为 {applicant}。"
    )
    return response(question, "price_catalog_medical_code", answer, data)


def fallback_keyword_search(db: Session, question: str, keyword: str) -> StructuredQuestionResponse:
    pattern = f"%{keyword}%"
    total = db.execute(
        select(func.count(DevicePriceCatalog.id))
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(
            or_(
                DevicePriceCatalog.component_name.ilike(pattern),
                DevicePriceCatalog.specification.ilike(pattern),
                DevicePriceCatalog.model.ilike(pattern),
                DevicePriceCatalog.procurement_unit.ilike(pattern),
                ApplicantEnterprise.standard_name.ilike(pattern),
                ManufacturerEnterprise.standard_name.ilike(pattern),
            )
        )
    ).scalar_one()
    answer = f"按关键词“{keyword}”在价格目录中检索到 {total} 条相关记录。"
    return response(question, "price_catalog_keyword", answer, {"keyword": keyword, "total": total}, confidence="medium")


def find_procurement_unit(db: Session, question: str) -> str | None:
    units = db.execute(select(DevicePriceCatalog.procurement_unit).distinct()).scalars().all()
    return find_longest_match(question, [unit for unit in units if unit])


def find_enterprise_name(db: Session, question: str) -> str | None:
    names = db.execute(select(Enterprise.standard_name).distinct()).scalars().all()
    return find_longest_match(question, [name for name in names if name])


def find_longest_match(text: str, candidates: list[str]) -> str | None:
    matches = [candidate for candidate in candidates if candidate in text]
    if not matches:
        return None
    return sorted(matches, key=len, reverse=True)[0]


def extract_medical_code(text: str) -> str | None:
    match = re.search(r"C\d{26}", text)
    return match.group(0) if match else None


def response(
    question: str,
    route_type: str,
    answer: str,
    data: dict,
    confidence: str = "high",
) -> StructuredQuestionResponse:
    return StructuredQuestionResponse(
        question=question,
        route_type=route_type,
        answer=answer,
        data=data,
        sources=["device_price_catalogs"],
        confidence=confidence,
    )
