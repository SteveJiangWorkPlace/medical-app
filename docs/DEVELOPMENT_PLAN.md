# Medical Device Procurement RAG Development Plan

## 1. Project Goal

Build a small-team RAG application for medical device volume-based procurement data. The system will ingest source materials, standardize structured procurement facts, index policy text, and answer questions through a hybrid flow:

- SQL for exact price, volume, time, region, product, and enterprise queries
- Vector retrieval for policy interpretation and evidence lookup
- Hybrid answer generation when both structured facts and policy evidence are needed

## 2. Deployment Direction

Local development:

- Frontend runs locally during development
- Backend runs locally with FastAPI
- Database runs in Docker with `pgvector/pgvector:pg17`
- Local database port is `5433`

Production target:

- Frontend: Netlify
- Backend: Render
- Database: PostgreSQL with pgvector support
- File storage: local during MVP, object storage later if uploads need persistence in production

## 3. Architecture Layers

### Source Layer

Supported input types:

- Web URL
- PDF
- Excel / CSV
- Image or screenshot
- Manual text

### Ingestion Layer

Responsibilities:

- Store source metadata in `source_records`
- Fetch webpages
- Read uploaded files
- Track parse status
- Keep original source traceability

### Parsing Layer

Responsibilities:

- Extract webpage title and body text
- Extract PDF text
- Read Excel / CSV rows
- Prepare OCR support for scanned materials later
- Store parsed text in `parsed_documents`

### Standardization Layer

Responsibilities:

- Normalize dates
- Normalize regions
- Normalize product and enterprise names
- Normalize price and volume units
- Map extracted facts into structured tables

### Storage Layer

Main tables:

- `source_records`
- `parsed_documents`
- `document_chunks`
- `procurement_projects`
- `products`
- `enterprises`
- `bid_results`
- `device_price_catalogs`
- `qa_logs`

Vector storage:

- `document_chunks.embedding`
- pgvector extension enabled in PostgreSQL

### Retrieval Layer

Responsibilities:

- Route questions to SQL, vector, hybrid, or clarification
- Query structured procurement facts
- Search policy text chunks
- Return evidence with source traceability

Current structured database question path:

- User question is sent to Gemini as a query planner request
- Gemini returns a strict `QueryPlan` JSON object, not raw SQL
- Backend validates the plan against a whitelist of datasets, fields, metrics, operators, and limits
- Backend executes the validated plan with SQLAlchemy
- The answer returns natural-language summary, query plan, assumptions, sources, and table rows

This avoids letting the LLM directly execute arbitrary SQL while still supporting broad natural-language questions.

### Answer Layer

Responsibilities:

- Merge SQL results and retrieved text evidence
- Distinguish facts, evidence, and model inference
- Save question and answer records in `qa_logs`

### Application Layer

Initial app pages:

- Source import page
- Document list and detail page
- Question answering page
- Basic data review page

## 4. Development Phases

### Phase 0: Local Foundation

Status: completed

Deliverables:

- Docker PostgreSQL + pgvector
- FastAPI backend skeleton
- Database health check
- SQLAlchemy models
- Alembic baseline migration

Completion standard:

- `/health` returns `ok`
- `/db/health` returns `vector_enabled=true`
- Alembic current revision is at head

### Phase 1: Source Record APIs

Status: completed

Deliverables:

- Pydantic schemas for source inputs
- CRUD service for `source_records`
- REST APIs for creating URL, manual text, and file source records
- List and detail APIs

Completion standard:

- A URL source can be inserted and fetched
- A manual text source can be inserted and fetched
- API responses include source id, type, status, and timestamps

### Phase 2: Webpage And Document Parsing

Status: partially completed

Deliverables:

- Webpage fetcher: completed
- HTML text extraction: completed
- PDF text extraction: completed for text-based PDFs
- Excel / CSV parser: completed as preview text extraction
- Parsed document creation flow: completed for URL sources

Completion standard:

- A webpage URL can create a parsed document
- A PDF can create a parsed document: ready for text PDFs, needs real samples
- An Excel / CSV can create source data candidates: ready for preview extraction, needs real column mapping

### Phase 3: Chunking And Embeddings

Status: partially completed

Deliverables:

- Text chunking service: completed
- Embedding provider interface: completed
- Initial embedding provider implementation: completed with `local-dev` placeholder
- Insert chunks with embeddings into `document_chunks`: completed
- Vector search API: completed

Completion standard:

- Parsed document text can be chunked
- Chunks can be embedded and stored
- Vector search returns chunks

Note: `local-dev` embeddings are deterministic placeholders for plumbing tests. They are not suitable for production semantic retrieval.

### Phase 4: Structured Procurement Data Import

Status: partially completed

Deliverables:

- Excel / CSV import mapping: completed for default MVP columns
- Product, enterprise, project upsert logic: completed
- Bid result insertion: completed
- Basic validation rules: completed for required columns

Completion standard:

- A structured table can populate `bid_results`: completed with sample CSV
- Price and volume fields are numeric
- Source traceability is preserved

### Phase 4.5: Price Catalog Query APIs

Status: completed for the first imported Excel dataset

Deliverables:

- Price catalog summary API
- Price catalog facet API
- Price catalog list and detail APIs
- Filters for project, procurement unit, enterprise, registration number, medical insurance code, procurement level, province, and keyword

Completion standard:

- The imported 690-row Excel dataset can be summarized
- Catalog rows can be filtered by procurement unit and enterprise
- A single row can be retrieved by id or medical insurance code

### Phase 5: Hybrid RAG QA

Status: structured freeform database QA completed for the first dataset; RAG retrieval path pending

Deliverables:

- Query router: pending
- SQL query path: completed for whitelisted price catalog queries
- LLM query planner: completed with Gemini strict JSON output
- QueryPlan validator: completed
- Safe SQLAlchemy executor: completed
- Freeform database QA endpoint: completed
- Contextual structured analysis: completed for the first price catalog dataset
- Vector retrieval path: completed as search API, not yet connected to final QA route
- Hybrid retrieval path: pending
- Answer generation service: basic deterministic summary completed, richer LLM wording pending
- QA logging: completed

Completion standard:

- SQL-only questions return structured facts: completed for the first price catalog dataset
- Freeform questions such as highest average price, products above a price threshold, grouped average price, and catalog-count ranking are converted to a safe query plan and executed
- Policy questions return source-backed text evidence
- Hybrid questions return data plus policy evidence

### Phase 6: Frontend And Deployment

Deliverables:

- Local frontend app
- Import UI
- QA UI
- Document browsing UI
- Netlify configuration
- Render configuration
- Production environment variable plan

Completion standard:

- Frontend can call local backend
- Backend can deploy to Render
- Frontend can deploy to Netlify

## 5. Current Technical Baseline

Backend:

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- psycopg
- pgvector Python package
- OpenAI SDK for optional production embeddings
- Google Gen AI SDK for Gemini embeddings and query planning

Database:

- PostgreSQL 17
- pgvector extension
- Docker container name: `medical-pgvector`
- Local port: `5433`

Local connection string:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/medical_rag
```

## 6. Current QA Interfaces

Backend:

- `POST /api/qa/structured`: deterministic structured QA for known question patterns
- `POST /api/qa/analysis`: earlier contextual rule-based analysis route
- `POST /api/qa/query-plan`: debug route that shows Gemini's generated `QueryPlan`
- `POST /api/qa/freeform`: current primary route for broad structured database questions

Frontend:

- Local URL: `http://127.0.0.1:5173`
- Vite proxy forwards `/api` to `http://127.0.0.1:8000`
- Current page calls `/api/qa/freeform`
- The page displays answer, assumptions, returned rows, and the generated query plan

## 7. Immediate Next Steps

1. Improve freeform answer wording for grouped and detail results
2. Add follow-up context to `/api/qa/freeform`, for questions like “它有多少个产品”
3. Add total matched row count separate from returned row count
4. Add document metadata for policy, news, report, interview, and manufacturer update sources
5. Connect vector retrieval to a RAG QA endpoint for non-structured text
6. Build hybrid SQL + RAG answering when a question needs both database facts and text evidence

## 8. Data Preparation Needed From The User

For useful MVP testing, prepare:

- 5 real webpage links
- 5 PDF documents
- 3 Excel / CSV procurement result samples
- 10 to 20 representative user questions
- Definitions for price, volume, publish date, and execution date fields

For the current structured database assistant, the most useful next input is 10 to 20 real questions you expect to ask, especially ambiguous ones involving price, enterprise, product, region, time, and quantity.
