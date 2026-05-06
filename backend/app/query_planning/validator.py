from app.query_planning.whitelist import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_DATASETS,
    ALLOWED_DIMENSIONS,
    ALLOWED_INTENTS,
    ALLOWED_METRICS,
    ALLOWED_ORDERS,
)
from app.schemas import QueryPlan


class QueryPlanValidationError(ValueError):
    pass


def validate_query_plan(plan: QueryPlan) -> QueryPlan:
    if plan.intent not in ALLOWED_INTENTS:
        raise QueryPlanValidationError(f"Unsupported intent: {plan.intent}")
    if plan.dataset not in ALLOWED_DATASETS:
        raise QueryPlanValidationError(f"Unsupported dataset: {plan.dataset}")
    if plan.metric and plan.metric not in ALLOWED_METRICS:
        raise QueryPlanValidationError(f"Unsupported metric: {plan.metric}")
    if plan.aggregation and plan.aggregation not in ALLOWED_AGGREGATIONS:
        raise QueryPlanValidationError(f"Unsupported aggregation: {plan.aggregation}")
    if plan.order not in ALLOWED_ORDERS:
        raise QueryPlanValidationError(f"Unsupported order: {plan.order}")
    if plan.limit < 1 or plan.limit > 100:
        raise QueryPlanValidationError("Limit must be between 1 and 100")
    for field in plan.group_by:
        if field not in ALLOWED_DIMENSIONS:
            raise QueryPlanValidationError(f"Unsupported group_by field: {field}")
    for item in plan.filters:
        if item.field not in ALLOWED_DIMENSIONS and item.field not in ALLOWED_METRICS:
            raise QueryPlanValidationError(f"Unsupported filter field: {item.field}")
    if plan.order_by and plan.order_by not in ALLOWED_DIMENSIONS and plan.order_by not in ALLOWED_METRICS:
        raise QueryPlanValidationError(f"Unsupported order_by field: {plan.order_by}")
    return plan
