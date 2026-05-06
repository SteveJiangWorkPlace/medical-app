import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        enabled = conn.execute(
            text("select exists(select 1 from pg_extension where extname = 'vector')")
        ).scalar_one()
    if not enabled:
        raise RuntimeError("pgvector extension is not enabled")
    print("pgvector extension is enabled")


if __name__ == "__main__":
    main()
