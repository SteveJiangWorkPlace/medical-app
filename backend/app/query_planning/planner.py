import json
import re

from pydantic import ValidationError

from app.llm.base import LLMProvider
from app.query_planning.whitelist import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_DATASETS,
    ALLOWED_DIMENSIONS,
    ALLOWED_INTENTS,
    ALLOWED_METRICS,
    ALLOWED_ORDERS,
)
from app.schemas import QueryPlan


def plan_query(question: str, llm: LLMProvider) -> tuple[QueryPlan, str]:
    prompt = build_query_plan_prompt(question)
    try:
        raw = llm.generate_json(prompt)
    except Exception as exc:
        fallback = fallback_query_plan(question, f"planner_provider_error: {exc.__class__.__name__}")
        return fallback, str(exc)
    try:
        data = json.loads(raw)
        return QueryPlan.model_validate(data), raw
    except (json.JSONDecodeError, ValidationError) as exc:
        fallback = QueryPlan(
            intent="clarify",
            clarification_question="我没有可靠理解这个问题，请换一种更明确的问法，例如指定企业、采购单元、价格指标或排名方式。",
            assumptions=[f"planner_parse_error: {exc.__class__.__name__}"],
        )
        return fallback, raw


def fallback_query_plan(question: str, reason: str) -> QueryPlan:
    assumptions = ["LLM查询规划不可用，已使用本地规则降级处理"]
    filters = []

    if "吻合器" in question:
        filters.append({"field": "medical_device_field", "operator": "eq", "value": "吻合器"})

    price_threshold = re.search(
        r"(?:价格|联动价|联动价格)(?:在)?\s*(\d+(?:\.\d+)?)\s*(?:以上|及以上|超过|大于|高于)",
        question,
    ) or re.search(
        r"(?:价格|联动价|联动价格)(?:超过|大于|高于)\s*(\d+(?:\.\d+)?)",
        question,
    )
    if price_threshold:
        return QueryPlan(
            intent="filter",
            metric="linked_price",
            filters=[*filters, {"field": "linked_price", "operator": "gt", "value": float(price_threshold.group(1))}],
            order_by="linked_price",
            order="desc",
            limit=10,
            assumptions=[*assumptions, "价格按联动价格 linked_price 统计"],
        )

    if "多少条" in question or "多少个" in question or "数量" in question and "最多" not in question:
        return QueryPlan(
            intent="aggregate",
            metric="catalog_count",
            aggregation="count",
            filters=filters,
            limit=10,
            assumptions=[*assumptions, "数量按目录条目数统计"],
        )

    if "数量最多" in question:
        return QueryPlan(
            intent="rank",
            metric="catalog_count",
            aggregation="count",
            group_by=["applicant_enterprise"],
            filters=filters,
            order_by="catalog_count",
            order="desc",
            limit=1,
            assumptions=[*assumptions, "当前无采购量字段，数量按目录条目数统计"],
        )

    if "采购单元" in question and "平均价格" in question:
        return QueryPlan(
            intent="aggregate",
            metric="linked_price",
            aggregation="avg",
            group_by=["procurement_unit"],
            filters=filters,
            order_by="linked_price",
            order="desc",
            limit=10,
            assumptions=[*assumptions, "价格按联动价格 linked_price 统计"],
        )

    if "平均价格最高" in question or "价格最高" in question:
        return QueryPlan(
            intent="rank",
            metric="linked_price",
            aggregation="avg" if "平均" in question else "max",
            group_by=["applicant_enterprise"],
            filters=filters,
            order_by="linked_price",
            order="desc",
            limit=1,
            assumptions=[*assumptions, "价格按联动价格 linked_price 统计"],
        )

    return QueryPlan(
        intent="clarify",
        clarification_question="当前查询规划服务不可用，请先尝试更明确的问题，例如“吻合器领域有多少条价格记录？”或“哪家企业数量最多？”。",
        assumptions=assumptions,
    )


def build_query_plan_prompt(question: str) -> str:
    return f"""
你是医疗器械集采数据库查询规划器。你的任务是把用户问题转换成严格 JSON 查询计划。

只能输出 JSON，不能输出 Markdown，不能解释。

当前只有一个数据集：
- device_price_catalogs：京津冀3+N联盟腔镜切割吻/缝合器类价格目录。

重要口径：
- linked_price 表示联动价格，不是严格意义的中标价。
- 当前数据没有真实采购量字段。如果用户问“数量最多”，默认理解为 catalog_count，即目录条目数量。
- applicant_enterprise 表示申报企业。
- manufacturer 表示生产企业。
- medical_device_field 表示医疗器械领域，当前数据所属领域为“吻合器”。

允许 intent：
{sorted(ALLOWED_INTENTS)}

允许 dataset：
{sorted(ALLOWED_DATASETS)}

允许维度 group_by / filter field：
{sorted(ALLOWED_DIMENSIONS)}

允许 metric：
{sorted(ALLOWED_METRICS)}

允许 aggregation：
{sorted(ALLOWED_AGGREGATIONS)}

允许 order：
{sorted(ALLOWED_ORDERS)}

输出 JSON schema：
{{
  "intent": "aggregate|rank|filter|compare|detail|clarify",
  "dataset": "device_price_catalogs",
  "metric": "linked_price|catalog_count|procurement_volume|planned_volume|actual_volume|agreed_volume|reported_volume|null",
  "aggregation": "count|min|max|avg|sum|null",
  "group_by": ["field"],
  "filters": [
    {{"field": "field", "operator": "eq|contains|gt|gte|lt|lte", "value": "value"}}
  ],
  "order_by": "field_or_metric_or_null",
  "order": "asc|desc",
  "limit": 10,
  "clarification_question": null,
  "assumptions": ["..."]
}}

示例：
用户：哪家企业价格最高？
输出：{{"intent":"rank","dataset":"device_price_catalogs","metric":"linked_price","aggregation":"max","group_by":["applicant_enterprise"],"filters":[],"order_by":"linked_price","order":"desc","limit":1,"clarification_question":null,"assumptions":["价格按联动价格 linked_price 统计"]}}

用户：哪家企业数量最多？
输出：{{"intent":"rank","dataset":"device_price_catalogs","metric":"catalog_count","aggregation":"count","group_by":["applicant_enterprise"],"filters":[],"order_by":"catalog_count","order":"desc","limit":1,"clarification_question":null,"assumptions":["当前无采购量字段，数量按目录条目数统计"]}}

用户：电动腔镜吻合器钉仓平均价格是多少？
输出：{{"intent":"aggregate","dataset":"device_price_catalogs","metric":"linked_price","aggregation":"avg","group_by":[],"filters":[{{"field":"procurement_unit","operator":"eq","value":"电动腔镜吻合器钉仓"}}],"order_by":null,"order":"desc","limit":10,"clarification_question":null,"assumptions":["价格按联动价格 linked_price 统计"]}}

用户：价格超过3000的有哪些？
输出：{{"intent":"filter","dataset":"device_price_catalogs","metric":"linked_price","aggregation":null,"group_by":[],"filters":[{{"field":"linked_price","operator":"gt","value":3000}}],"order_by":"linked_price","order":"desc","limit":10,"clarification_question":null,"assumptions":["价格按联动价格 linked_price 统计"]}}

用户问题：
{question}
""".strip()
