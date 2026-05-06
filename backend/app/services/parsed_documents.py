from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ParsedDocument
from app.schemas import ParsedDocumentCreate


def create_parsed_document(db: Session, payload: ParsedDocumentCreate) -> ParsedDocument:
    document = ParsedDocument(**payload.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_parsed_document(db: Session, document_id: int) -> ParsedDocument | None:
    return db.get(ParsedDocument, document_id)


def list_parsed_documents(db: Session, limit: int = 50, offset: int = 0) -> tuple[list[ParsedDocument], int]:
    total = db.execute(select(func.count()).select_from(ParsedDocument)).scalar_one()
    documents = db.execute(
        select(ParsedDocument).order_by(ParsedDocument.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return documents, total
