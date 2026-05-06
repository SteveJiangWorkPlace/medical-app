from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.docx import extract_docx_text
from app.ingestion.pdf import extract_pdf_text
from app.ingestion.tables import extract_table_preview
from app.ingestion.web import fetch_webpage
from app.models import SourceRecord
from app.schemas import ParsedDocumentCreate, ParseSourceRequest, SourceRecordCreate, SourceRecordUpdate
from app.services.parsed_documents import create_parsed_document


def create_source_record(db: Session, payload: SourceRecordCreate) -> SourceRecord:
    data = payload.model_dump()
    if data.get("source_url") is not None:
        data["source_url"] = str(data["source_url"])
    record = SourceRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_source_record(db: Session, record_id: int) -> SourceRecord | None:
    return db.get(SourceRecord, record_id)


def list_source_records(db: Session, limit: int = 50, offset: int = 0) -> tuple[list[SourceRecord], int]:
    total = db.execute(select(func.count()).select_from(SourceRecord)).scalar_one()
    records = db.execute(
        select(SourceRecord).order_by(SourceRecord.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return records, total


def update_source_record(db: Session, record_id: int, payload: SourceRecordUpdate) -> SourceRecord | None:
    record = get_source_record(db, record_id)
    if record is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    if data.get("source_url") is not None:
        data["source_url"] = str(data["source_url"])
    for key, value in data.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    return record


def parse_url_source_record(db: Session, record_id: int, payload: ParseSourceRequest):
    record = get_source_record(db, record_id)
    if record is None:
        return None
    if record.source_type != "url" or not record.source_url:
        raise ValueError("Only URL source records can be parsed by this endpoint")

    webpage = fetch_webpage(record.source_url)
    record.raw_html = webpage.html
    record.raw_text = webpage.text
    record.parse_status = "parsed"

    document = create_parsed_document(
        db,
        ParsedDocumentCreate(
            source_record_id=record.id,
            title=webpage.title,
            document_type=payload.document_type or "webpage",
            source_name=payload.source_name,
            medical_device_field=payload.medical_device_field,
            company_name=payload.company_name,
            tags=payload.tags,
            confidentiality=payload.confidentiality,
            province=payload.province,
            city=payload.city,
            publish_date=payload.publish_date,
            effective_date=payload.effective_date,
            clean_text=webpage.text,
            parse_confidence=0.8,
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return document


def parse_file_source_record(db: Session, record_id: int, payload: ParseSourceRequest):
    record = get_source_record(db, record_id)
    if record is None:
        return None
    if record.source_type != "file" or not record.storage_path:
        raise ValueError("Only file source records can be parsed by this endpoint")

    file_type = (record.file_type or "").lower()
    file_name = (record.file_name or "").lower()
    if "pdf" in file_type or file_name.endswith(".pdf"):
        text = extract_pdf_text(record.storage_path)
        document_type = payload.document_type or "pdf"
    elif file_name.endswith(".docx"):
        text = extract_docx_text(record.storage_path)
        document_type = payload.document_type or "document"
    elif any(file_name.endswith(suffix) for suffix in [".csv", ".xls", ".xlsx"]):
        text = extract_table_preview(record.storage_path)
        document_type = payload.document_type or "table"
    else:
        raise ValueError("Unsupported file type for parsing")

    record.raw_text = text
    record.parse_status = "parsed"
    title = record.file_name or f"source-record-{record.id}"

    document = create_parsed_document(
        db,
        ParsedDocumentCreate(
            source_record_id=record.id,
            title=title,
            document_type=document_type,
            source_name=payload.source_name,
            medical_device_field=payload.medical_device_field,
            company_name=payload.company_name,
            tags=payload.tags,
            confidentiality=payload.confidentiality,
            province=payload.province,
            city=payload.city,
            publish_date=payload.publish_date,
            effective_date=payload.effective_date,
            clean_text=text,
            parse_confidence=0.7,
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return document
