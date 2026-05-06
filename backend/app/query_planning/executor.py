from decimal import Decimal
from typing import Any

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import DevicePriceCatalog, Enterprise
from app.schemas import QueryExecutionResult, QueryPlan, QueryFilter


ApplicantEnterprise = aliased(Enterprise)
ManufacturerEnterprise = aliased(Enterprise)


DIMENSION_COLUMNS = {
    "project_name": DevicePriceCatalog.project_name,
    "procurement_level": DevicePriceCatalog.procurement_level,
    "procurement_scope": DevicePriceCatalog.procurement_scope,
    "procurement_type": DevicePriceCatalog.procurement_type,
    "alliance_name": DevicePriceCatalog.alliance_name,
    "medical_device_field": DevicePriceCatalog.medical_device_field,
    "province": DevicePriceCatalog.province,
    "city": DevicePriceCatalog.city,
    "procurement_unit": DevicePriceCatalog.procurement_unit,
    "applicant_enterprise": ApplicantEnterprise.standard_name,
    "manufacturer": ManufacturerEnterprise.standard_name,
    "registration_no": DevicePriceCatalog.registration_no,
    "component_name": DevicePriceCatalog.component_name,
    "specification": DevicePriceCatalog.specification,
    "model": DevicePriceCatalog.model,
    "medical_insurance_code": DevicePriceCatalog.medical_insurance_code,
}

METRIC_COLUMNS = {
    "linked_price": DevicePriceCatalog.linked_price,
    "procurement_volume": DevicePriceCatalog.procurement_volume,
    "planned_volume": DevicePriceCatalog.planned_volume,
    "actual_volume": DevicePriceCatalog.actual_volume,
    "agreed_volume": DevicePriceCatalog.agreed_volume,
    "reported_volume": DevicePriceCatalog.reported_volume,
}


def execute_query_plan(db: Session, plan: QueryPlan) -> QueryExecutionResult:
    if plan.intent == "clarify":
        return QueryExecutionResult(columns=[], rows=[], total=0)
    if plan.intent in {"aggregate", "rank", "compare"}:
        return execute_aggregate_or_rank(db, plan)
    if plan.intent in {"filter", "detail"}:
        return execute_filter_or_detail(db, plan)
    return QueryExecutionResult(columns=[], rows=[], total=0)


def execute_aggregate_or_rank(db: Session, plan: QueryPlan) -> QueryExecutionResult:
    group_columns = [(field, DIMENSION_COLUMNS[field]) for field in plan.group_by]
    metric_expr = build_metric_expression(plan)
    metric_label = metric_output_name(plan)

    selected = [column.label(field) for field, column in group_columns]
    selected.append(metric_expr.label(metric_label))

    statement = base_statement(select(*selected))
    statement = apply_filters(statement, plan.filters)
    if group_columns:
        statement = statement.group_by(*[column for _, column in group_columns])

    order_column = metric_expr if plan.order_by in {plan.metric, metric_label, "catalog_count", None} else resolve_column(plan.order_by)
    statement = statement.order_by(desc(order_column) if plan.order == "desc" else asc(order_column)).limit(plan.limit)
    rows = [row_to_dict(row._mapping) for row in db.execute(statement).all()]
    return QueryExecutionResult(columns=list(rows[0].keys()) if rows else [*plan.group_by, metric_label], rows=rows, total=len(rows))


def execute_filter_or_detail(db: Session, plan: QueryPlan) -> QueryExecutionResult:
    columns = [
        ("project_name", DevicePriceCatalog.project_name),
        ("medical_device_field", DevicePriceCatalog.medical_device_field),
        ("procurement_unit", DevicePriceCatalog.procurement_unit),
        ("applicant_enterprise", ApplicantEnterprise.standard_name),
        ("manufacturer", ManufacturerEnterprise.standard_name),
        ("component_name", DevicePriceCatalog.component_name),
        ("model", DevicePriceCatalog.model),
        ("medical_insurance_code", DevicePriceCatalog.medical_insurance_code),
        ("linked_price", DevicePriceCatalog.linked_price),
        ("price_unit", DevicePriceCatalog.price_unit),
    ]
    statement = base_statement(select(*[column.label(name) for name, column in columns]))
    statement = apply_filters(statement, plan.filters)
    if plan.order_by:
        order_column = resolve_column(plan.order_by)
        statement = statement.order_by(desc(order_column) if plan.order == "desc" else asc(order_column))
    statement = statement.limit(plan.limit)
    rows = [row_to_dict(row._mapping) for row in db.execute(statement).all()]
    return QueryExecutionResult(columns=[name for name, _ in columns], rows=rows, total=len(rows))


def base_statement(statement: Select) -> Select:
    return (
        statement.select_from(DevicePriceCatalog)
        .outerjoin(ApplicantEnterprise, DevicePriceCatalog.applicant_enterprise_id == ApplicantEnterprise.id)
        .outerjoin(ManufacturerEnterprise, DevicePriceCatalog.manufacturer_id == ManufacturerEnterprise.id)
    )


def build_metric_expression(plan: QueryPlan):
    if plan.metric == "catalog_count" or plan.aggregation == "count":
        return func.count(DevicePriceCatalog.id)
    metric_column = METRIC_COLUMNS.get(plan.metric or "linked_price", DevicePriceCatalog.linked_price)
    if plan.aggregation == "min":
        return func.min(metric_column)
    if plan.aggregation == "max":
        return func.max(metric_column)
    if plan.aggregation == "sum":
        return func.sum(metric_column)
    return func.avg(metric_column)


def metric_output_name(plan: QueryPlan) -> str:
    if plan.metric == "catalog_count" or plan.aggregation == "count":
        return "catalog_count"
    return f"{plan.aggregation or 'avg'}_{plan.metric or 'linked_price'}"


def apply_filters(statement: Select, filters: list[QueryFilter]) -> Select:
    for item in filters:
        column = resolve_column(item.field)
        value = item.value
        if item.operator == "eq":
            statement = statement.where(column == value)
        elif item.operator == "contains":
            statement = statement.where(column.ilike(f"%{value}%"))
        elif item.operator == "gt":
            statement = statement.where(column > value)
        elif item.operator == "gte":
            statement = statement.where(column >= value)
        elif item.operator == "lt":
            statement = statement.where(column < value)
        elif item.operator == "lte":
            statement = statement.where(column <= value)
    return statement


def resolve_column(field: str | None):
    if field in DIMENSION_COLUMNS:
        return DIMENSION_COLUMNS[field]
    if field in METRIC_COLUMNS:
        return METRIC_COLUMNS[field]
    if field == "catalog_count":
        return func.count(DevicePriceCatalog.id)
    return DevicePriceCatalog.id


def row_to_dict(mapping: Any) -> dict:
    result = {}
    for key, value in dict(mapping).items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result
