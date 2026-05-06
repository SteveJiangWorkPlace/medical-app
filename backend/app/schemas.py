from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


SourceType = Literal["file", "url", "manual"]
SourceCategory = Literal[
    "industry_report",
    "company_report",
    "industry_news",
    "company_website",
    "expert_interview",
    "policy_document",
    "procurement_notice",
    "academic_literature",
    "financial_report",
    "other",
]
SourceChannel = Literal[
    "broker_research",
    "consulting_report",
    "news_media",
    "company_official",
    "government_platform",
    "academic_database",
    "conference",
    "internal_note",
    "manual_upload",
    "other",
]
PublisherType = Literal["brand", "industry_org", "media", "government", "broker", "consulting", "academic", "internal", "other"]
ContentScope = Literal["industry", "brand", "product", "policy", "market_access", "pricing", "technology", "channel", "other"]
ResearchType = Literal["primary", "secondary", "mixed", "official_disclosure", "news", "opinion", "other"]
EvidenceLevel = Literal["official", "high", "medium", "low", "unknown"]


class SourceRecordBase(BaseModel):
    source_type: SourceType
    file_name: str | None = None
    file_type: str | None = None
    source_url: HttpUrl | None = None
    storage_path: str | None = None
    raw_html: str | None = None
    raw_text: str | None = None
    parse_status: str = "pending"


class SourceRecordCreate(SourceRecordBase):
    @model_validator(mode="after")
    def validate_source_payload(self) -> "SourceRecordCreate":
        if self.source_type == "url" and self.source_url is None:
            raise ValueError("source_url is required when source_type is 'url'")
        if self.source_type == "manual" and not self.raw_text:
            raise ValueError("raw_text is required when source_type is 'manual'")
        if self.source_type == "file" and not self.file_name:
            raise ValueError("file_name is required when source_type is 'file'")
        return self


class SourceRecordUpdate(BaseModel):
    file_name: str | None = None
    file_type: str | None = None
    source_url: HttpUrl | None = None
    storage_path: str | None = None
    raw_html: str | None = None
    raw_text: str | None = None
    parse_status: str | None = Field(default=None, max_length=64)


class SourceRecordRead(BaseModel):
    id: int
    source_type: SourceType
    file_name: str | None
    file_type: str | None
    source_url: str | None
    storage_path: str | None
    raw_html: str | None
    raw_text: str | None
    parse_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceRecordList(BaseModel):
    items: list[SourceRecordRead]
    total: int


class ParsedDocumentCreate(BaseModel):
    source_record_id: int | None = None
    title: str
    document_type: str | None = None
    source_name: str | None = None
    source_category: SourceCategory | None = None
    source_channel: SourceChannel | None = None
    publisher: str | None = None
    publisher_type: PublisherType | None = None
    author: str | None = None
    source_url: str | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    evidence_level: EvidenceLevel | None = None
    geographic_scope: str | None = None
    medical_device_field: str | None = None
    company_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidentiality: str | None = None
    province: str | None = None
    city: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None
    clean_text: str | None = None
    parse_confidence: float | None = None


class ParsedDocumentRead(BaseModel):
    id: int
    source_record_id: int | None
    title: str
    document_type: str | None
    source_name: str | None
    source_category: SourceCategory | None
    source_channel: SourceChannel | None
    publisher: str | None
    publisher_type: PublisherType | None
    author: str | None
    source_url: str | None
    content_scope: ContentScope | None
    research_type: ResearchType | None
    evidence_level: EvidenceLevel | None
    geographic_scope: str | None
    medical_device_field: str | None
    company_name: str | None
    tags: list[str] | None
    confidentiality: str | None
    province: str | None
    city: str | None
    publish_date: date | None
    effective_date: date | None
    clean_text: str | None
    parse_confidence: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ParsedDocumentList(BaseModel):
    items: list[ParsedDocumentRead]
    total: int


class ParseSourceRequest(BaseModel):
    document_type: str | None = None
    source_name: str | None = None
    source_category: SourceCategory | None = None
    source_channel: SourceChannel | None = None
    publisher: str | None = None
    publisher_type: PublisherType | None = None
    author: str | None = None
    source_url: str | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    evidence_level: EvidenceLevel | None = None
    geographic_scope: str | None = None
    medical_device_field: str | None = None
    company_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidentiality: str | None = None
    province: str | None = None
    city: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_text: str
    section_title: str | None
    chunk_index: int
    province: str | None
    publish_date: date | None
    effective_date: date | None
    policy_type: str | None
    source_name: str | None
    source_category: SourceCategory | None
    source_channel: SourceChannel | None
    publisher: str | None
    publisher_type: PublisherType | None
    author: str | None
    source_url: str | None
    content_scope: ContentScope | None
    research_type: ResearchType | None
    evidence_level: EvidenceLevel | None
    geographic_scope: str | None
    medical_device_field: str | None
    company_name: str | None
    tags: list[str] | None
    confidentiality: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkList(BaseModel):
    items: list[DocumentChunkRead]
    total: int


class ChunkDocumentRequest(BaseModel):
    max_chars: int = Field(default=800, ge=200, le=3000)
    overlap_chars: int = Field(default=80, ge=0, le=500)
    replace_existing: bool = True


class EmbedDocumentRequest(BaseModel):
    replace_existing: bool = True


class EmbedDocumentResponse(BaseModel):
    document_id: int
    embedded_chunks: int
    provider: str
    dimensions: int


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    province: str | None = None
    policy_type: str | None = None
    source_category: SourceCategory | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    medical_device_field: str | None = None
    company_name: str | None = None


class VectorSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    chunk_text: str
    distance: float
    province: str | None
    policy_type: str | None
    source_name: str | None
    source_category: SourceCategory | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    evidence_level: EvidenceLevel | None = None
    medical_device_field: str | None
    company_name: str | None
    publish_date: date | None


class VectorSearchResponse(BaseModel):
    items: list[VectorSearchResult]
    total: int


class RAGQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str = "local-test"
    limit: int = Field(default=5, ge=1, le=12)
    document_type: str | None = None
    source_category: SourceCategory | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    evidence_level: EvidenceLevel | None = None
    medical_device_field: str | None = None
    company_name: str | None = None


class RAGCitation(BaseModel):
    document_id: int
    chunk_id: int
    title: str | None = None
    document_type: str | None = None
    source_name: str | None = None
    source_category: SourceCategory | None = None
    source_channel: SourceChannel | None = None
    publisher: str | None = None
    publisher_type: PublisherType | None = None
    content_scope: ContentScope | None = None
    research_type: ResearchType | None = None
    evidence_level: EvidenceLevel | None = None
    medical_device_field: str | None = None
    company_name: str | None = None
    snippet: str
    score: float | None = None


class RAGQuestionResponse(BaseModel):
    question: str
    session_id: str
    answer: str
    citations: list[RAGCitation]
    confidence: str


class BidResultImportRequest(BaseModel):
    document_id: int
    project_name: str | None = None
    procurement_level: str | None = None
    procurement_scope: str | None = None
    procurement_type: str | None = None
    is_continuation_procurement: bool = False
    alliance_name: str | None = None
    medical_device_field: str | None = None
    province: str | None = None
    city: str | None = None
    publish_date: date | None = None
    execution_start_date: date | None = None
    execution_end_date: date | None = None
    procurement_volume: float | None = None
    planned_volume: float | None = None
    actual_volume: float | None = None
    agreed_volume: float | None = None
    reported_volume: float | None = None
    volume_unit: str | None = None
    project_name_column: str = "project_name"
    province_column: str = "province"
    product_name_column: str = "product_name"
    enterprise_name_column: str = "enterprise_name"
    winning_price_column: str = "winning_price"
    planned_volume_column: str = "planned_volume"
    actual_volume_column: str | None = None
    price_unit_column: str = "price_unit"
    volume_unit_column: str = "volume_unit"
    publish_date_column: str | None = "publish_date"
    execution_start_date_column: str | None = "execution_start_date"
    execution_end_date_column: str | None = "execution_end_date"


class BidResultImportResponse(BaseModel):
    document_id: int
    imported_rows: int
    skipped_rows: int
    project_count: int
    product_count: int
    enterprise_count: int
    bid_result_count: int
    warnings: list[str]


class PriceCatalogImportRequest(BaseModel):
    document_id: int
    project_name: str | None = None
    procurement_level: str | None = None
    procurement_scope: str | None = None
    procurement_type: str | None = None
    is_continuation_procurement: bool = False
    alliance_name: str | None = None
    medical_device_field: str | None = None
    province: str | None = None
    city: str | None = None
    publish_date: date | None = None
    execution_start_date: date | None = None
    execution_end_date: date | None = None
    procurement_volume: float | None = None
    planned_volume: float | None = None
    actual_volume: float | None = None
    agreed_volume: float | None = None
    reported_volume: float | None = None
    volume_unit: str | None = None
    procurement_unit_column: str = "采购单元"
    applicant_enterprise_column: str = "申报企业"
    manufacturer_column: str = "生产企业"
    registration_no_column: str = "注册证号"
    component_name_column: str = "部件名称"
    specification_column: str = "规格"
    model_column: str = "型号"
    medical_insurance_code_column: str = "国家医保编码（27位）"
    linked_price_column: str = "联动价格（元）"
    price_unit: str = "元"


class PriceCatalogImportResponse(BaseModel):
    document_id: int
    imported_rows: int
    skipped_rows: int
    project_count: int
    applicant_enterprise_count: int
    manufacturer_count: int
    catalog_count: int
    warnings: list[str]


class PriceCatalogRead(BaseModel):
    id: int
    source_record_id: int | None
    project_id: int | None
    project_name: str | None
    procurement_level: str | None
    procurement_scope: str | None
    procurement_type: str | None
    is_continuation_procurement: bool
    alliance_name: str | None
    medical_device_field: str | None
    province: str | None
    city: str | None
    procurement_unit: str | None
    registration_no: str | None
    component_name: str | None
    specification: str | None
    model: str | None
    medical_insurance_code: str | None
    linked_price: float | None
    price_unit: str | None
    procurement_volume: float | None
    planned_volume: float | None
    actual_volume: float | None
    agreed_volume: float | None
    reported_volume: float | None
    volume_unit: str | None
    publish_date: date | None
    execution_start_date: date | None
    execution_end_date: date | None
    applicant_enterprise_name: str | None = None
    manufacturer_name: str | None = None

    model_config = {"from_attributes": True}


class PriceCatalogList(BaseModel):
    items: list[PriceCatalogRead]
    total: int
    limit: int
    offset: int


class PriceCatalogSummary(BaseModel):
    total: int
    project_count: int
    procurement_unit_count: int
    applicant_enterprise_count: int
    manufacturer_count: int
    medical_insurance_code_count: int
    document_count: int
    industry_report_count: int
    company_report_count: int
    interview_record_count: int
    news_report_count: int
    min_price: float | None
    max_price: float | None
    avg_price: float | None


class PriceCatalogFacets(BaseModel):
    project_names: list[str]
    procurement_levels: list[str]
    procurement_scopes: list[str]
    procurement_types: list[str]
    alliance_names: list[str]
    medical_device_fields: list[str]
    provinces: list[str]
    procurement_units: list[str]
    applicant_enterprises: list[str]
    manufacturers: list[str]


class StructuredQuestionRequest(BaseModel):
    question: str = Field(min_length=1)


class StructuredQuestionResponse(BaseModel):
    question: str
    route_type: str
    answer: str
    data: dict
    sources: list[str]
    confidence: str


class AnalysisQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str = "local-test"


class AnalysisQuestionResponse(BaseModel):
    question: str
    session_id: str
    intent: str
    answer: str
    data: dict
    entities: dict
    context: dict
    sources: list[str]
    confidence: str
    note: str | None = None


class QueryFilter(BaseModel):
    field: str
    operator: Literal["eq", "contains", "gt", "gte", "lt", "lte"]
    value: str | float | int


class QueryPlan(BaseModel):
    intent: Literal["aggregate", "rank", "filter", "compare", "detail", "clarify"]
    dataset: str = "device_price_catalogs"
    metric: str | None = None
    aggregation: Literal["count", "min", "max", "avg", "sum"] | None = None
    group_by: list[str] = Field(default_factory=list)
    filters: list[QueryFilter] = Field(default_factory=list)
    order_by: str | None = None
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=10, ge=1, le=100)
    clarification_question: str | None = None
    assumptions: list[str] = Field(default_factory=list)


class QueryPlanRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str = "local-test"


class QueryPlanResponse(BaseModel):
    question: str
    session_id: str
    query_plan: QueryPlan
    raw_response: str | None = None


class QueryExecutionResult(BaseModel):
    columns: list[str]
    rows: list[dict]
    total: int


class FreeformQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str = "local-test"


class FreeformQuestionResponse(BaseModel):
    question: str
    session_id: str
    answer: str
    query_plan: QueryPlan
    result: QueryExecutionResult
    assumptions: list[str]
    sources: list[str]
    confidence: str


class HybridQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str = "local-test"
    limit: int = Field(default=6, ge=1, le=12)


class HybridQuestionResponse(BaseModel):
    question: str
    session_id: str
    answer: str
    query_plan: QueryPlan
    result: QueryExecutionResult
    citations: list[RAGCitation]
    assumptions: list[str]
    sources: list[str]
    confidence: str
    context: dict
