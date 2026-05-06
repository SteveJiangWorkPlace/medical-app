# Medical Device Procurement RAG Task List

## Completed

- [x] Confirm local PostgreSQL Docker strategy with pgvector
- [x] Start `pgvector/pgvector:pg17` container on local port `5433`
- [x] Enable and verify the `vector` extension
- [x] Create backend FastAPI project skeleton
- [x] Create local `.env` database configuration
- [x] Create initial MVP database schema
- [x] Apply schema to the local Docker database
- [x] Install backend Python dependencies in `backend/.venv`
- [x] Add `/health` API endpoint
- [x] Add `/db/health` API endpoint
- [x] Verify backend can connect to PostgreSQL + pgvector
- [x] Add SQLAlchemy models for the MVP tables
- [x] Add Alembic migrations so schema changes are versioned
- [x] Stamp current database schema as Alembic baseline
- [x] Add Pydantic request/response schemas for source records
- [x] Add source record APIs for URL, file, and manual text inputs
- [x] Add webpage fetch and text extraction module
- [x] Add parsed document APIs and service layer
- [x] Add URL source parsing flow into parsed documents
- [x] Add basic document chunking module and APIs
- [x] Add local file upload source API
- [x] Add PDF text extraction module
- [x] Add Excel/CSV ingestion preview module
- [x] Add file source parsing flow into parsed documents
- [x] Add embedding provider interface
- [x] Add local development embedding provider
- [x] Add OpenAI embedding provider
- [x] Add Gemini embedding provider
- [x] Add embedding generation and vector insert flow
- [x] Add vector search API
- [x] Add structured bid result import API
- [x] Validate sample CSV import into `bid_results`
- [x] Add procurement metadata fields for project name, province, publish date, execution date, volume, and procurement level
- [x] Add `device_price_catalogs` table for price linkage/catalog data
- [x] Import sample Excel into `device_price_catalogs`
- [x] Add price catalog summary API
- [x] Add price catalog facets API
- [x] Add price catalog list/detail API with filters
- [x] Add basic structured QA API for price catalog data
- [x] Validate structured QA for total count, procurement unit, enterprise, and medical insurance code questions
- [x] Add initial frontend structured QA test page
- [x] Validate frontend build and local dev server
- [x] Add contextual analysis QA API with in-memory session context
- [x] Support analysis questions for highest price, most catalog rows, top procurement unit average, and follow-up pronouns
- [x] Update frontend QA page to call contextual analysis API
- [x] Add LLM provider for query planning
- [x] Add QueryPlan schema and whitelist
- [x] Add Gemini query planner that returns strict JSON
- [x] Add QueryPlan validator
- [x] Add safe QueryPlan executor with SQLAlchemy
- [x] Add `/api/qa/query-plan` debug endpoint
- [x] Add `/api/qa/freeform` endpoint
- [x] Update frontend to call freeform QA and show query plan
- [x] Validate freeform QA for ranking, filtering, grouped averages, and catalog count questions
- [x] Validate frontend build and local Vite proxy to backend
- [x] Add Render backend deployment scripts and pgvector bootstrap
- [x] Add Netlify frontend deployment configuration
- [x] Add deployment guide for Render, Netlify, environment variables, and data migration

## Next

- [ ] Improve freeform answer wording for grouped tables and detailed row lists
- [ ] Add conversational follow-up support to the LLM freeform route
- [ ] Add explicit total-count query for filtered results beyond returned page size
- [ ] Add RAG document type fields for policy, news, report, interview, and manufacturer updates
- [ ] Add RAG retrieval route for non-structured documents
- [ ] Add hybrid SQL + RAG answer generation path
- [ ] Map real Excel/CSV columns into `bid_results`
- [ ] Add simple query router
- [ ] Add answer generation service
- [ ] Push repository to GitHub
- [ ] Create Render PostgreSQL and backend Web Service
- [ ] Create Netlify frontend site
- [ ] Migrate or re-import local data into production database
- [ ] Decide production database provider and pgvector support

## Needs User Input Soon

- [x] Choose embedding route: Gemini API selected for now
- [x] Add Gemini API key to backend `.env`
- [ ] Provide 3 to 5 real webpage links for procurement policy pages
- [ ] Provide 2 to 3 PDF samples, including at least one text PDF and one scanned PDF if OCR is needed
- [ ] Provide 2 to 3 Excel/CSV samples for procurement result data
- [ ] Confirm the standard meaning of price, volume, publish date, and execution date
- [ ] Provide 10 to 20 real analysis questions you want the freeform database assistant to handle

## Current Local Commands

Backend server:

```powershell
cd "D:\IT Projects\医疗应用\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/db/health
```

Freeform QA check:

```powershell
$body = @{ session_id='local-test'; question='哪家企业数量最多？' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/qa/freeform -ContentType 'application/json' -Body $body
```

Frontend:

```powershell
cd "D:\IT Projects\医疗应用\frontend"
npm run dev -- --port 5173
```

Database connection:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/medical_rag
```
