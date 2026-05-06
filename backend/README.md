# Medical RAG API

Local development backend for the medical device procurement RAG application.

## Database

The local database runs in Docker with PostgreSQL 17 and pgvector:

```powershell
docker run --name medical-pgvector -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=medical_rag -p 5433:5432 -d pgvector/pgvector:pg17
```

Connection string:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/medical_rag
```

## Embeddings

Local plumbing tests use deterministic placeholder embeddings:

```env
EMBEDDING_PROVIDER=local-dev
```

For real semantic retrieval, use OpenAI embeddings from the backend only:

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

Do not put `OPENAI_API_KEY` in frontend code or commit it to git.

Gemini embeddings can also be used from the backend:

```env
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=1536
```

Do not put `GEMINI_API_KEY` in frontend code or commit it to git.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Apply the initial schema:

```powershell
& "D:\PostgreSQL\bin\psql.exe" "postgresql://postgres:postgres@localhost:5433/medical_rag" -f sql/001_init.sql
```

If local `psql` is not available, use Docker:

```powershell
docker cp sql/001_init.sql medical-pgvector:/tmp/001_init.sql
docker exec -it medical-pgvector psql -U postgres -d medical_rag -f /tmp/001_init.sql
```

Run the API:

```powershell
uvicorn app.main:app --reload
```

Health checks:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/db/health`
