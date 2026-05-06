from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.imports import router as imports_router
from app.api.parsed_documents import router as parsed_documents_router
from app.api.price_catalogs import router as price_catalogs_router
from app.api.qa import router as qa_router
from app.api.rag import router as rag_router
from app.api.search import router as search_router
from app.api.source_records import router as source_records_router
from app.config import get_settings
from app.db import check_database, get_db


settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(source_records_router, prefix="/api")
app.include_router(parsed_documents_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(imports_router, prefix="/api")
app.include_router(price_catalogs_router, prefix="/api")
app.include_router(qa_router, prefix="/api")
app.include_router(rag_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/db/health")
def db_health(_: Session = Depends(get_db)) -> dict[str, str]:
    return check_database()
