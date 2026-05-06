from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from requests import RequestException
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import get_settings
from app.ingestion.files import save_upload_file
from app.security import require_admin_api_key
from app.schemas import (
    ParsedDocumentRead,
    ParseSourceRequest,
    SourceRecordCreate,
    SourceRecordList,
    SourceRecordRead,
    SourceRecordUpdate,
)
from app.services.source_records import (
    create_source_record,
    get_source_record,
    list_source_records,
    parse_file_source_record,
    parse_url_source_record,
    update_source_record,
)


router = APIRouter(prefix="/source-records", tags=["source records"])


@router.post("", response_model=SourceRecordRead, status_code=status.HTTP_201_CREATED)
def create_source_record_endpoint(
    payload: SourceRecordCreate,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> SourceRecordRead:
    return create_source_record(db, payload)


@router.post("/upload", response_model=SourceRecordRead, status_code=status.HTTP_201_CREATED)
def upload_source_file_endpoint(
    file: UploadFile = File(...),
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> SourceRecordRead:
    settings = get_settings()
    original_name, storage_path = save_upload_file(settings.upload_dir, file)
    payload = SourceRecordCreate(
        source_type="file",
        file_name=original_name,
        file_type=file.content_type,
        storage_path=storage_path,
        parse_status="pending",
    )
    return create_source_record(db, payload)


@router.get("", response_model=SourceRecordList)
def list_source_records_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> SourceRecordList:
    records, total = list_source_records(db, limit=limit, offset=offset)
    return SourceRecordList(items=records, total=total)


@router.get("/{record_id}", response_model=SourceRecordRead)
def get_source_record_endpoint(
    record_id: int,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> SourceRecordRead:
    record = get_source_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source record not found")
    return record


@router.patch("/{record_id}", response_model=SourceRecordRead)
def update_source_record_endpoint(
    record_id: int,
    payload: SourceRecordUpdate,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> SourceRecordRead:
    record = update_source_record(db, record_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source record not found")
    return record


@router.post("/{record_id}/parse-url", response_model=ParsedDocumentRead, status_code=status.HTTP_201_CREATED)
def parse_url_source_record_endpoint(
    record_id: int,
    payload: ParseSourceRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> ParsedDocumentRead:
    try:
        document = parse_url_source_record(db, record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch URL: {exc}") from exc

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source record not found")
    return document


@router.post("/{record_id}/parse-file", response_model=ParsedDocumentRead, status_code=status.HTTP_201_CREATED)
def parse_file_source_record_endpoint(
    record_id: int,
    payload: ParseSourceRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> ParsedDocumentRead:
    try:
        document = parse_file_source_record(db, record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source record not found")
    return document
