# Deployment Guide

## 1. Before Pushing To GitHub

Do not commit secrets or local raw uploads.

Already ignored:

```text
.env
.venv/
data/raw/
data/processed/
__pycache__/
*.pyc
```

Recommended check:

```powershell
git status
```

Make sure `backend/.env` is not listed.

## 2. Render PostgreSQL

Create a Render PostgreSQL database first.

Use the External Database URL as backend `DATABASE_URL`.

The backend build script runs:

```bash
python scripts/ensure_pgvector.py
alembic upgrade head
```

This will run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 3. Render Backend Web Service

Create a Render Web Service from the GitHub repository.

If using `backend/render.yaml`, set root directory to:

```text
backend
```

Build command:

```bash
bash scripts/render_build.sh
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variables:

```env
APP_ENV=production
DATABASE_URL=<Render External Database URL>
CORS_ORIGINS=https://<your-netlify-domain>
GEMINI_API_KEY=<your Gemini key>
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-2.5-flash
EMBEDDING_PROVIDER=gemini
EMBEDDING_DIMENSIONS=1536
LLM_PROVIDER=gemini
LLM_TEMPERATURE=0
UPLOAD_DIR=data/raw
```

Do not set these on Render unless you explicitly need a proxy:

```env
HTTP_PROXY
HTTPS_PROXY
```

## 4. Netlify Frontend

Connect the same GitHub repository to Netlify.

This repo includes `netlify.toml`:

```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"
```

Required Netlify environment variable:

```env
VITE_API_BASE_URL=https://<your-render-backend-domain>
```

Redeploy frontend after changing this variable.

## 5. Data Migration

The local Docker PostgreSQL data is not automatically uploaded to Render.

Option A: re-import data in production.

Use the existing upload/parse/import APIs to import:

- Procurement Excel
- Expert interview DOCX
- Reports and future text sources

Option B: use PostgreSQL dump/restore.

Local dump example:

```powershell
docker exec medical-pgvector pg_dump -U postgres -d medical_rag --format=custom --file=/tmp/medical_rag.dump
docker cp medical-pgvector:/tmp/medical_rag.dump .\medical_rag.dump
```

Restore to Render from a machine with `pg_restore`:

```bash
pg_restore --clean --if-exists --no-owner --dbname "<Render External Database URL>" medical_rag.dump
```

If restoring into a fresh Render database, make sure pgvector is enabled first.

## 6. Smoke Tests

Backend:

```text
GET https://<render-backend>/health
GET https://<render-backend>/db/health
POST https://<render-backend>/api/qa/freeform
POST https://<render-backend>/api/rag/ask
```

Frontend:

Open:

```text
https://<your-netlify-domain>
```

Test:

```text
哪家企业数量最多？
把所有联动价在3000以上的型号列给我
派尔特2025年Q3的情况怎么样？
```
