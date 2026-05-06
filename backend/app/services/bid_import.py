from io import StringIO
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidResult, DevicePriceCatalog, Enterprise, ParsedDocument, ProcurementProject, Product
from app.schemas import (
    BidResultImportRequest,
    BidResultImportResponse,
    PriceCatalogImportRequest,
    PriceCatalogImportResponse,
)


def import_bid_results_from_document(
    db: Session,
    document: ParsedDocument,
    payload: BidResultImportRequest,
) -> BidResultImportResponse:
    frame = read_document_table(document.clean_text or "")
    warnings: list[str] = []
    required_columns = [
        payload.project_name_column,
        payload.province_column,
        payload.product_name_column,
        payload.enterprise_name_column,
        payload.winning_price_column,
    ]
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    imported_rows = 0
    skipped_rows = 0
    project_ids: set[int] = set()
    product_ids: set[int] = set()
    enterprise_ids: set[int] = set()

    for row_index, row in frame.iterrows():
        project_name = clean_string(row.get(payload.project_name_column))
        product_name = clean_string(row.get(payload.product_name_column))
        enterprise_name = clean_string(row.get(payload.enterprise_name_column))
        province = clean_string(row.get(payload.province_column))

        if not project_name or not product_name or not enterprise_name:
            skipped_rows += 1
            warnings.append(f"Row {row_index + 1} skipped: missing project, product, or enterprise")
            continue

        project = get_or_create_project(
            db,
            project_name=payload.project_name or project_name,
            province=payload.province or province,
            city=payload.city,
            alliance_name=payload.alliance_name,
            medical_device_field=payload.medical_device_field,
            procurement_level=payload.procurement_level,
            procurement_scope=payload.procurement_scope,
            procurement_type=payload.procurement_type,
            publish_date=payload.publish_date,
            effective_date=payload.execution_start_date,
        )
        product = get_or_create_product(db, product_name=product_name)
        enterprise = get_or_create_enterprise(db, enterprise_name=enterprise_name)

        result = BidResult(
            project_id=project.id,
            product_id=product.id,
            enterprise_id=enterprise.id,
            source_record_id=document.source_record_id,
            procurement_unit=None,
            project_name=payload.project_name or project_name,
            procurement_level=payload.procurement_level,
            procurement_scope=payload.procurement_scope,
            procurement_type=payload.procurement_type,
            alliance_name=payload.alliance_name,
            medical_device_field=payload.medical_device_field,
            province=payload.province or province,
            city=payload.city,
            winning_price=parse_number(row.get(payload.winning_price_column)),
            procurement_volume=payload.procurement_volume,
            planned_volume=payload.planned_volume or parse_number(row.get(payload.planned_volume_column)),
            actual_volume=payload.actual_volume
            or (parse_number(row.get(payload.actual_volume_column)) if payload.actual_volume_column else None),
            agreed_volume=payload.agreed_volume,
            reported_volume=payload.reported_volume,
            price_unit=clean_string(row.get(payload.price_unit_column)),
            volume_unit=payload.volume_unit or clean_string(row.get(payload.volume_unit_column)),
            publish_date=payload.publish_date
            or (parse_date(row.get(payload.publish_date_column)) if payload.publish_date_column else None),
            execution_start_date=payload.execution_start_date
            or (parse_date(row.get(payload.execution_start_date_column))
            if payload.execution_start_date_column
            else None),
            execution_end_date=payload.execution_end_date
            or (parse_date(row.get(payload.execution_end_date_column))
            if payload.execution_end_date_column
            else None),
        )
        db.add(result)
        db.flush()

        imported_rows += 1
        project_ids.add(project.id)
        product_ids.add(product.id)
        enterprise_ids.add(enterprise.id)

    db.commit()

    return BidResultImportResponse(
        document_id=document.id,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
        project_count=len(project_ids),
        product_count=len(product_ids),
        enterprise_count=len(enterprise_ids),
        bid_result_count=imported_rows,
        warnings=warnings,
    )


def import_price_catalog_from_document(
    db: Session,
    document: ParsedDocument,
    payload: PriceCatalogImportRequest,
) -> PriceCatalogImportResponse:
    frame = read_document_table(document.clean_text or "")
    warnings: list[str] = []
    required_columns = [
        payload.procurement_unit_column,
        payload.applicant_enterprise_column,
        payload.manufacturer_column,
        payload.registration_no_column,
        payload.component_name_column,
        payload.specification_column,
        payload.model_column,
        payload.medical_insurance_code_column,
        payload.linked_price_column,
    ]
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    project = None
    project_ids: set[int] = set()
    if payload.project_name:
        project = get_or_create_project(
            db,
            project_name=payload.project_name,
            province=payload.province,
            city=payload.city,
            alliance_name=payload.alliance_name,
            medical_device_field=payload.medical_device_field,
            procurement_level=payload.procurement_level,
            procurement_scope=payload.procurement_scope,
            procurement_type=payload.procurement_type,
            publish_date=payload.publish_date,
            effective_date=payload.execution_start_date,
        )
        project_ids.add(project.id)

    imported_rows = 0
    skipped_rows = 0
    applicant_ids: set[int] = set()
    manufacturer_ids: set[int] = set()

    for row_index, row in frame.iterrows():
        medical_code = clean_string(row.get(payload.medical_insurance_code_column))
        linked_price = parse_number(row.get(payload.linked_price_column))
        if not medical_code or linked_price is None:
            skipped_rows += 1
            warnings.append(f"Row {row_index + 1} skipped: missing medical insurance code or linked price")
            continue

        applicant = get_or_create_enterprise(db, clean_string(row.get(payload.applicant_enterprise_column)) or "")
        manufacturer = get_or_create_enterprise(db, clean_string(row.get(payload.manufacturer_column)) or "")

        catalog = DevicePriceCatalog(
            source_record_id=document.source_record_id,
            project_id=project.id if project else None,
            procurement_level=payload.procurement_level,
            procurement_scope=payload.procurement_scope,
            procurement_type=payload.procurement_type,
            alliance_name=payload.alliance_name,
            medical_device_field=payload.medical_device_field,
            province=payload.province or document.province,
            city=payload.city or document.city,
            project_name=payload.project_name,
            procurement_unit=clean_string(row.get(payload.procurement_unit_column)),
            applicant_enterprise_id=applicant.id,
            manufacturer_id=manufacturer.id,
            registration_no=clean_string(row.get(payload.registration_no_column)),
            component_name=clean_string(row.get(payload.component_name_column)),
            specification=clean_string(row.get(payload.specification_column)),
            model=clean_string(row.get(payload.model_column)),
            medical_insurance_code=medical_code,
            linked_price=linked_price,
            price_unit=payload.price_unit,
            procurement_volume=payload.procurement_volume,
            planned_volume=payload.planned_volume,
            actual_volume=payload.actual_volume,
            agreed_volume=payload.agreed_volume,
            reported_volume=payload.reported_volume,
            volume_unit=payload.volume_unit,
            publish_date=payload.publish_date or document.publish_date,
            execution_start_date=payload.execution_start_date or document.effective_date,
            execution_end_date=payload.execution_end_date,
        )
        db.add(catalog)
        db.flush()

        imported_rows += 1
        applicant_ids.add(applicant.id)
        manufacturer_ids.add(manufacturer.id)

    db.commit()
    return PriceCatalogImportResponse(
        document_id=document.id,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
        project_count=len(project_ids),
        applicant_enterprise_count=len(applicant_ids),
        manufacturer_count=len(manufacturer_ids),
        catalog_count=imported_rows,
        warnings=warnings,
    )


def read_document_table(text: str) -> pd.DataFrame:
    if not text.strip():
        raise ValueError("Document has no text to import")
    lines = text.splitlines()
    if lines and lines[0].startswith("[Sheet:"):
        lines = lines[1:]
    return pd.read_csv(StringIO("\n".join(lines)))


def get_or_create_project(
    db: Session,
    project_name: str,
    province: str | None,
    city: str | None = None,
    alliance_name: str | None = None,
    medical_device_field: str | None = None,
    procurement_level: str | None = None,
    procurement_scope: str | None = None,
    procurement_type: str | None = None,
    publish_date=None,
    effective_date=None,
) -> ProcurementProject:
    project = db.execute(
        select(ProcurementProject).where(
            ProcurementProject.project_name == project_name,
            ProcurementProject.province == province,
        )
    ).scalar_one_or_none()
    if project:
        return project

    project = ProcurementProject(
        project_name=project_name,
        province=province,
        city=city,
        alliance_name=alliance_name,
        medical_device_field=medical_device_field,
        procurement_level=procurement_level,
        procurement_scope=procurement_scope,
        procurement_type=procurement_type,
        publish_date=publish_date,
        effective_date=effective_date,
    )
    db.add(project)
    db.flush()
    return project


def get_or_create_product(db: Session, product_name: str) -> Product:
    product = db.execute(select(Product).where(Product.standard_name == product_name)).scalar_one_or_none()
    if product:
        return product

    product = Product(standard_name=product_name)
    db.add(product)
    db.flush()
    return product


def get_or_create_enterprise(db: Session, enterprise_name: str) -> Enterprise:
    enterprise = db.execute(select(Enterprise).where(Enterprise.standard_name == enterprise_name)).scalar_one_or_none()
    if enterprise:
        return enterprise

    enterprise = Enterprise(standard_name=enterprise_name)
    db.add(enterprise)
    db.flush()
    return enterprise


def clean_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def parse_number(value: Any):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return pd.to_numeric(value, errors="coerce")


def parse_date(value: Any):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()
