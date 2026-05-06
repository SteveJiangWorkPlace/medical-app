ALLOWED_DATASETS = {"device_price_catalogs"}

ALLOWED_DIMENSIONS = {
    "project_name",
    "procurement_level",
    "procurement_scope",
    "procurement_type",
    "alliance_name",
    "medical_device_field",
    "province",
    "city",
    "procurement_unit",
    "applicant_enterprise",
    "manufacturer",
    "registration_no",
    "component_name",
    "specification",
    "model",
    "medical_insurance_code",
}

ALLOWED_METRICS = {
    "linked_price",
    "catalog_count",
    "procurement_volume",
    "planned_volume",
    "actual_volume",
    "agreed_volume",
    "reported_volume",
}

ALLOWED_AGGREGATIONS = {"count", "min", "max", "avg", "sum"}
ALLOWED_ORDERS = {"asc", "desc"}
ALLOWED_INTENTS = {"aggregate", "rank", "filter", "compare", "detail", "clarify"}
