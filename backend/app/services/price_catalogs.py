from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import DevicePriceCatalog, Enterprise
from app.schemas import PriceCatalogFacets, PriceCatalogRead, PriceCatalogSummary


ApplicantEnterprise = aliased(Enterprise)
ManufacturerEnterprise = aliased(Enterprise)


def build_price_catalog_filters(
    statement: Select,
    project_name: str | None = None,
    procurement_unit: str | None = None,
    enterprise_name: str | None = None,
    registration_no: str | None = None,
    medical_insurance_code: str | None = None,
    procurement_level: str | None = None,
    medical_device_field: str | None = None,
    province: str | None = None,
    keyword: str | None = None,
) -> Select:
    if project_name:
        statement = statement.where(DevicePriceCatalog.project_name == project_name)
    if procurement_unit:
        statement = statement.where(DevicePriceCatalog.procurement_unit == procurement_unit)
    if registration_no:
        statement = statement.where(DevicePriceCatalog.registration_no == registration_no)
    if medical_insurance_code:
        statement = statement.where(DevicePriceCatalog.medical_insurance_code == medical_insurance_code)
    if procurement_level:
        statement = statement.where(DevicePriceCatalog.procurement_level == procurement_level)
    if medical_device_field:
        statement = statement.where(DevicePriceCatalog.medical_device_field == medical_device_field)
    if province:
        statement = statement.where(DevicePriceCatalog.province == province)
    if enterprise_name:
        statement = statement.where(
            or_(
                ApplicantEnterprise.standard_name == enterprise_name,
                ManufacturerEnterprise.standard_name == enterprise_name,
            )
        )
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                DevicePriceCatalog.component_name.ilike(pattern),
                DevicePriceCatalog.specification.ilike(pattern),
                DevicePriceCatalog.model.ilike(pattern),
                DevicePriceCatalog.medical_insurance_code.ilike(pattern),
                DevicePriceCatalog.registration_no.ilike(pattern),
                ApplicantEnterprise.standard_name.ilike(pattern),
                ManufacturerEnterprise.standard_name.ilike(pattern),
            )
        )
    return statement


def list_price_catalogs(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    project_name: str | None = None,
    procurement_unit: str | None = None,
    enterprise_name: str | None = None,
    registration_no: str | None = None,
    medical_insurance_code: str | None = None,
    procurement_level: str | None = None,
    medical_device_field: str | None = None,
    province: str | None = None,
    keyword: str | None = None,
) -> tuple[list[PriceCatalogRead], int]:
    base = (
        select(DevicePriceCatalog, ApplicantEnterprise.standard_name, ManufacturerEnterprise.standard_name)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
    )
    base = build_price_catalog_filters(
        base,
        project_name=project_name,
        procurement_unit=procurement_unit,
        enterprise_name=enterprise_name,
        registration_no=registration_no,
        medical_insurance_code=medical_insurance_code,
        procurement_level=procurement_level,
        medical_device_field=medical_device_field,
        province=province,
        keyword=keyword,
    )

    count_statement = select(func.count()).select_from(base.subquery())
    total = db.execute(count_statement).scalar_one()
    rows = db.execute(
        base.order_by(DevicePriceCatalog.id.asc()).limit(limit).offset(offset)
    ).all()
    return [to_price_catalog_read(catalog, applicant, manufacturer) for catalog, applicant, manufacturer in rows], total


def get_price_catalog(db: Session, catalog_id: int) -> PriceCatalogRead | None:
    row = db.execute(
        select(DevicePriceCatalog, ApplicantEnterprise.standard_name, ManufacturerEnterprise.standard_name)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
        .where(DevicePriceCatalog.id == catalog_id)
    ).one_or_none()
    if row is None:
        return None
    catalog, applicant, manufacturer = row
    return to_price_catalog_read(catalog, applicant, manufacturer)


def get_price_catalog_summary(db: Session) -> PriceCatalogSummary:
    row = db.execute(
        select(
            func.count(DevicePriceCatalog.id),
            func.count(func.distinct(DevicePriceCatalog.project_name)),
            func.count(func.distinct(DevicePriceCatalog.procurement_unit)),
            func.count(func.distinct(DevicePriceCatalog.applicant_enterprise_id)),
            func.count(func.distinct(DevicePriceCatalog.manufacturer_id)),
            func.count(func.distinct(DevicePriceCatalog.medical_insurance_code)),
            func.min(DevicePriceCatalog.linked_price),
            func.max(DevicePriceCatalog.linked_price),
            func.avg(DevicePriceCatalog.linked_price),
        )
    ).one()
    return PriceCatalogSummary(
        total=row[0],
        project_count=row[1],
        procurement_unit_count=row[2],
        applicant_enterprise_count=row[3],
        manufacturer_count=row[4],
        medical_insurance_code_count=row[5],
        min_price=float(row[6]) if row[6] is not None else None,
        max_price=float(row[7]) if row[7] is not None else None,
        avg_price=float(row[8]) if row[8] is not None else None,
    )


def get_price_catalog_facets(db: Session) -> PriceCatalogFacets:
    return PriceCatalogFacets(
        project_names=distinct_values(db, DevicePriceCatalog.project_name),
        procurement_levels=distinct_values(db, DevicePriceCatalog.procurement_level),
        procurement_scopes=distinct_values(db, DevicePriceCatalog.procurement_scope),
        procurement_types=distinct_values(db, DevicePriceCatalog.procurement_type),
        alliance_names=distinct_values(db, DevicePriceCatalog.alliance_name),
        medical_device_fields=distinct_values(db, DevicePriceCatalog.medical_device_field),
        provinces=distinct_values(db, DevicePriceCatalog.province),
        procurement_units=distinct_values(db, DevicePriceCatalog.procurement_unit),
        applicant_enterprises=distinct_enterprises(db, DevicePriceCatalog.applicant_enterprise_id),
        manufacturers=distinct_enterprises(db, DevicePriceCatalog.manufacturer_id),
    )


def distinct_values(db: Session, column) -> list[str]:
    return [
        value
        for value in db.execute(select(column).where(column.is_not(None)).distinct().order_by(column.asc())).scalars()
        if value
    ]


def distinct_enterprises(db: Session, enterprise_id_column) -> list[str]:
    return [
        value
        for value in db.execute(
            select(Enterprise.standard_name)
            .join(DevicePriceCatalog, enterprise_id_column == Enterprise.id)
            .where(Enterprise.standard_name.is_not(None))
            .distinct()
            .order_by(Enterprise.standard_name.asc())
        ).scalars()
        if value
    ]


def to_price_catalog_read(
    catalog: DevicePriceCatalog,
    applicant_name: str | None,
    manufacturer_name: str | None,
) -> PriceCatalogRead:
    data = PriceCatalogRead.model_validate(catalog)
    data.applicant_enterprise_name = applicant_name
    data.manufacturer_name = manufacturer_name
    return data
