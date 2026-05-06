from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> dict[str, str]:
    with engine.connect() as conn:
        version = conn.execute(text("select version()")).scalar_one()
        vector_enabled = conn.execute(
            text("select exists(select 1 from pg_extension where extname = 'vector')")
        ).scalar_one()
    return {"version": version, "vector_enabled": str(vector_enabled).lower()}
