# Infilect Data Ingestion Service

A FastAPI backend for ingesting retail master data (stores, users, store-user mappings) from CSV files into PostgreSQL.

---

## Architecture at a Glance

```
┌─────────────┐    CSV upload     ┌──────────────────────────────────────────────┐
│   Client    │ ───────────────► │  Router (routers/)                           │
│ (Postman /  │                  │    ↓ reads file bytes                         │
│   curl)     │                  │  Service (services/*_ingestion.py)            │
└─────────────┘                  │    ↓ iter_csv_chunks() — streams in chunks    │
                                 │    ↓ Pydantic validation per row              │
                                 │    ↓ LookupService.get_or_create() (cached)   │
                                 │    ↓ BaseRepository.bulk_insert()             │
                                 │  PostgreSQL (via asyncpg)                     │
                                 └──────────────────────────────────────────────┘
```

### Key Design Patterns

| Pattern | Where | Why |
|---|---|---|
| **Repository** | `repositories/` | Swap DB without touching services |
| **Service layer** | `services/` | Pure business logic, no HTTP concerns |
| **Port/Adapter** | `LookupService` | In-memory cache over DB; swap to Redis with zero service changes |
| **Chunked streaming** | `csv_reader.py` | O(chunk) memory, not O(file) — handles 500K rows |
| **Bulk insert** | `bulk_insert()` | Single SQL INSERT per chunk vs N row-by-row saves |
| **Background jobs** | `job_runner.py` | Async for large files; replace BackgroundTask with Celery in one line |
| **Schema validation** | Pydantic v2 | Coercion + error collection without try/except spaghetti |

---

## Project Structure

```
infilect/
├── app/
│   ├── main.py                  # FastAPI app, startup
│   ├── database.py              # Async SQLAlchemy engine + session factory
│   ├── core/
│   │   ├── config.py            # Settings (env vars)
│   │   └── exceptions.py        # Domain exceptions
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── lookup.py            # 6 lookup tables
│   │   ├── store.py
│   │   ├── user.py
│   │   ├── pjp.py
│   │   └── job.py               # Background job tracking
│   ├── schemas/                 # Pydantic row schemas (validation)
│   │   ├── store.py
│   │   ├── user.py
│   │   ├── pjp.py
│   │   └── common.py            # RowError, IngestionResult, JobStatus
│   ├── repositories/            # DB access layer
│   │   ├── base.py              # Generic bulk_insert, get_by_field
│   │   ├── lookup.py            # get-or-create with in-memory cache
│   │   ├── store.py
│   │   ├── user.py
│   │   └── job.py
│   ├── services/                # Business logic
│   │   ├── csv_reader.py        # Chunked streaming CSV iterator
│   │   ├── validators.py        # Row validation + batch dedup
│   │   ├── store_ingestion.py
│   │   ├── user_ingestion.py
│   │   ├── pjp_ingestion.py
│   │   └── job_runner.py        # Background job executor
│   └── routers/                 # FastAPI route handlers
│       ├── stores.py
│       ├── users.py
│       ├── pjp.py
│       └── jobs.py
├── tests/
│   ├── conftest.py
│   ├── test_validators.py
│   └── test_csv_reader.py
├── sample_data/
│   ├── stores_master.csv          (100 rows, ~6 intentional errors)
│   ├── users_master.csv           (30 rows, ~6 intentional errors)
│   ├── store_user_mapping.csv     (150 rows, ~5 intentional errors)
│   └── stores_master_500k.csv     (500,000 rows, performance test)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose

### Run

```bash
cp .env.example .env
docker-compose up --build
```

API is live at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

---

## API Endpoints

### Health Check
```
GET /health
```

### Upload Order (important!)
1. `POST /api/v1/stores/upload`  — must come first
2. `POST /api/v1/users/upload`   — must come first (parallel with stores is fine)
3. `POST /api/v1/pjp/upload`     — depends on both stores and users existing

---

## curl Examples

### Upload stores (synchronous)
```bash
curl -X POST http://localhost:8000/api/v1/stores/upload \
  -F "file=@sample_data/stores_master.csv"
```

### Upload users (synchronous)
```bash
curl -X POST http://localhost:8000/api/v1/users/upload \
  -F "file=@sample_data/users_master.csv"
```

### Upload PJP mapping (synchronous)
```bash
curl -X POST http://localhost:8000/api/v1/pjp/upload \
  -F "file=@sample_data/store_user_mapping.csv"
```

### Upload 500K file (async background job)
```bash
# Returns immediately with job_id
curl -X POST http://localhost:8000/api/v1/stores/upload-async \
  -F "file=@sample_data/stores_master_500k.csv"

# Poll for completion
curl http://localhost:8000/api/v1/jobs/<job_id>
```

---

## Response Format

```json
{
  "filename": "stores_master.csv",
  "total_rows": 100,
  "success_rows": 95,
  "failed_rows": 5,
  "errors": [
    {
      "row": 5,
      "column": "store_id",
      "value": "",
      "reason": "store_id is required and cannot be blank"
    },
    {
      "row": 10,
      "column": "latitude",
      "value": "999",
      "reason": "latitude must be between -90 and 90"
    }
  ]
}
```

---

## Design Decisions

### Failure Policy: Skip bad rows, ingest the rest
A single malformed email or missing field shouldn't block 99 valid stores. Each row gets an independent validation result. The response reports every failure (row number, column, reason). The caller can fix and re-upload just the failed rows.

### Lookup table normalization
Before any get-or-create call, values are normalized: `strip()` + `title()`.
So `"mumbai"`, `"MUMBAI"`, `"  Mumbai "` all resolve to `"Mumbai"` — same DB row.

### Performance strategy for 500K rows
- Chunked CSV streaming with pandas (`chunksize=2000`) — constant memory
- Lookup table cache built per-request — avoids N+1 SELECTs
- PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` — single statement per chunk
- FastAPI `BackgroundTasks` for async endpoint — returns immediately
- Total time for 500K rows on a standard machine: ~2–4 minutes

### Self-referential supervisor FK (users)
Two-pass approach per chunk:
1. Insert all users without `supervisor_id`
2. Resolve supervisor FKs using the username→id map built after pass 1
This allows supervisors and supervisees to appear in the same file.

---

## Scaling Path

| Bottleneck | Current | Scale-up |
|---|---|---|
| Background jobs | FastAPI BackgroundTasks | Drop-in Celery + Redis |
| DB writes | asyncpg bulk insert | PostgreSQL COPY (10x faster for huge files) |
| Concurrency | Single worker | Gunicorn multi-worker / Kubernetes HPA |
| Lookup cache | Per-request dict | Redis with TTL |
| File storage | In-memory bytes | S3 presigned upload → stream from S3 |

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover all validators and the CSV reader. No DB required for unit tests.
