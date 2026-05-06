from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import PriceCatalogFacets, PriceCatalogList, PriceCatalogRead, PriceCatalogSummary
from app.services.price_catalogs import (
    get_price_catalog,
    get_price_catalog_facets,
    get_price_catalog_summary,
    list_price_catalogs,
)


router = APIRouter(prefix="/price-catalogs", tags=["price catalogs"])


@router.get("/summary", response_model=PriceCatalogSummary)
def price_catalog_summary_endpoint(db: Session = Depends(get_db)) -> PriceCatalogSummary:
    return get_price_catalog_summary(db)


@router.get("/facets", response_model=PriceCatalogFacets)
def price_catalog_facets_endpoint(db: Session = Depends(get_db)) -> PriceCatalogFacets:
    return get_price_catalog_facets(db)


@router.get("", response_model=PriceCatalogList)
def list_price_catalogs_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    project_name: str | None = None,
    procurement_unit: str | None = None,
    enterprise_name: str | None = None,
    registration_no: str | None = None,
    medical_insurance_code: str | None = None,
    procurement_level: str | None = None,
    medical_device_field: str | None = None,
    is_continuation_procurement: bool | None = None,
    province: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
) -> PriceCatalogList:
    items, total = list_price_catalogs(
        db,
        limit=limit,
        offset=offset,
        project_name=project_name,
        procurement_unit=procurement_unit,
        enterprise_name=enterprise_name,
        registration_no=registration_no,
        medical_insurance_code=medical_insurance_code,
        procurement_level=procurement_level,
        medical_device_field=medical_device_field,
        is_continuation_procurement=is_continuation_procurement,
        province=province,
        keyword=keyword,
    )
    return PriceCatalogList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{catalog_id}", response_model=PriceCatalogRead)
def get_price_catalog_endpoint(catalog_id: int, db: Session = Depends(get_db)) -> PriceCatalogRead:
    catalog = get_price_catalog(db, catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price catalog not found")
    return catalog
