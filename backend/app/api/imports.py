from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import require_admin_api_key
from app.schemas import (
    BidResultImportRequest,
    BidResultImportResponse,
    PriceCatalogImportRequest,
    PriceCatalogImportResponse,
)
from app.services.bid_import import import_bid_results_from_document, import_price_catalog_from_document
from app.services.parsed_documents import get_parsed_document


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bid-results/from-document", response_model=BidResultImportResponse)
def import_bid_results_from_document_endpoint(
    payload: BidResultImportRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> BidResultImportResponse:
    document = get_parsed_document(db, payload.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")

    try:
        return import_bid_results_from_document(db, document=document, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/price-catalogs/from-document", response_model=PriceCatalogImportResponse)
def import_price_catalog_from_document_endpoint(
    payload: PriceCatalogImportRequest,
    _: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
) -> PriceCatalogImportResponse:
    document = get_parsed_document(db, payload.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsed document not found")

    try:
        return import_price_catalog_from_document(db, document=document, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
