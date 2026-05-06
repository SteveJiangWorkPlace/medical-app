from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        CheckConstraint("source_type in ('file', 'url', 'manual')", name="source_records_source_type_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    raw_html: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list["ParsedDocument"]] = relationship(back_populates="source_record")


class ParsedDocument(Base):
    __tablename__ = "parsed_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_records.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(Text)
    source_category: Mapped[str | None] = mapped_column(Text)
    source_channel: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    publisher_type: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    content_scope: Mapped[str | None] = mapped_column(Text)
    research_type: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str | None] = mapped_column(Text)
    geographic_scope: Mapped[str | None] = mapped_column(Text)
    medical_device_field: Mapped[str | None] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSONB)
    confidentiality: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    publish_date: Mapped[Date | None] = mapped_column(Date)
    effective_date: Mapped[Date | None] = mapped_column(Date)
    clean_text: Mapped[str | None] = mapped_column(Text)
    parse_confidence: Mapped[Numeric | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source_record: Mapped[SourceRecord | None] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class ProcurementProject(Base):
    __tablename__ = "procurement_projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    alliance_name: Mapped[str | None] = mapped_column(Text)
    medical_device_field: Mapped[str | None] = mapped_column(Text)
    procurement_level: Mapped[str | None] = mapped_column(Text)
    procurement_scope: Mapped[str | None] = mapped_column(Text)
    procurement_type: Mapped[str | None] = mapped_column(Text)
    batch_no: Mapped[str | None] = mapped_column(Text)
    publish_date: Mapped[Date | None] = mapped_column(Date)
    effective_date: Mapped[Date | None] = mapped_column(Date)
    organization: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bid_results: Mapped[list["BidResult"]] = relationship(back_populates="project")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    standard_name: Mapped[str] = mapped_column(Text, nullable=False)
    alias_name: Mapped[str | None] = mapped_column(Text)
    category_level_1: Mapped[str | None] = mapped_column(Text)
    category_level_2: Mapped[str | None] = mapped_column(Text)
    category_level_3: Mapped[str | None] = mapped_column(Text)
    specification: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    registration_no: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bid_results: Mapped[list["BidResult"]] = relationship(back_populates="product")


class Enterprise(Base):
    __tablename__ = "enterprises"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    standard_name: Mapped[str] = mapped_column(Text, nullable=False)
    alias_name: Mapped[str | None] = mapped_column(Text)
    enterprise_type: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bid_results: Mapped[list["BidResult"]] = relationship(back_populates="enterprise")


class BidResult(Base):
    __tablename__ = "bid_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_projects.id", ondelete="SET NULL"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id", ondelete="SET NULL"))
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id", ondelete="SET NULL"))
    procurement_unit: Mapped[str | None] = mapped_column(Text)
    project_name: Mapped[str | None] = mapped_column(Text)
    medical_device_field: Mapped[str | None] = mapped_column(Text)
    procurement_level: Mapped[str | None] = mapped_column(Text)
    procurement_scope: Mapped[str | None] = mapped_column(Text)
    procurement_type: Mapped[str | None] = mapped_column(Text)
    is_continuation_procurement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    alliance_name: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    winning_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    procurement_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    planned_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    actual_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    agreed_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    reported_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    price_unit: Mapped[str | None] = mapped_column(Text)
    volume_unit: Mapped[str | None] = mapped_column(Text)
    publish_date: Mapped[Date | None] = mapped_column(Date)
    execution_start_date: Mapped[Date | None] = mapped_column(Date)
    execution_end_date: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[ProcurementProject | None] = relationship(back_populates="bid_results")
    product: Mapped[Product | None] = relationship(back_populates="bid_results")
    enterprise: Mapped[Enterprise | None] = relationship(back_populates="bid_results")


class DevicePriceCatalog(Base):
    __tablename__ = "device_price_catalogs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_projects.id", ondelete="SET NULL"))
    procurement_level: Mapped[str | None] = mapped_column(Text)
    procurement_scope: Mapped[str | None] = mapped_column(Text)
    procurement_type: Mapped[str | None] = mapped_column(Text)
    is_continuation_procurement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    alliance_name: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    project_name: Mapped[str | None] = mapped_column(Text)
    medical_device_field: Mapped[str | None] = mapped_column(Text)
    procurement_unit: Mapped[str | None] = mapped_column(Text)
    applicant_enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id", ondelete="SET NULL"))
    manufacturer_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id", ondelete="SET NULL"))
    registration_no: Mapped[str | None] = mapped_column(Text)
    component_name: Mapped[str | None] = mapped_column(Text)
    specification: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    medical_insurance_code: Mapped[str | None] = mapped_column(Text)
    linked_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    price_unit: Mapped[str | None] = mapped_column(Text)
    procurement_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    planned_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    actual_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    agreed_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    reported_volume: Mapped[Numeric | None] = mapped_column(Numeric(18, 4))
    volume_unit: Mapped[str | None] = mapped_column(Text)
    publish_date: Mapped[Date | None] = mapped_column(Date)
    execution_start_date: Mapped[Date | None] = mapped_column(Date)
    execution_end_date: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("parsed_documents.id", ondelete="CASCADE"))
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_title: Mapped[str | None] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    province: Mapped[str | None] = mapped_column(Text)
    publish_date: Mapped[Date | None] = mapped_column(Date)
    effective_date: Mapped[Date | None] = mapped_column(Date)
    policy_type: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(Text)
    source_category: Mapped[str | None] = mapped_column(Text)
    source_channel: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    publisher_type: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    content_scope: Mapped[str | None] = mapped_column(Text)
    research_type: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str | None] = mapped_column(Text)
    geographic_scope: Mapped[str | None] = mapped_column(Text)
    medical_device_field: Mapped[str | None] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSONB)
    confidentiality: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[ParsedDocument] = relationship(back_populates="chunks")


class QALog(Base):
    __tablename__ = "qa_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    route_type: Mapped[str | None] = mapped_column(Text)
    sql_query: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
