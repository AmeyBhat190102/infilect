import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import create_all_tables
from app.routers import stores, users, pjp, jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Backend service for retail platform data ingestion. "
        "Accepts CSV files for stores, users, and store-user mappings. "
        "Validates, resolves lookup FKs, and bulk-inserts into PostgreSQL."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await create_all_tables()
    logging.getLogger(__name__).info("Database tables ready.")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


# Routers
app.include_router(stores.router)
app.include_router(users.router)
app.include_router(pjp.router)
app.include_router(jobs.router)
