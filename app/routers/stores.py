from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import IngestionResult, JobStatus
from app.services.store_ingestion import ingest_stores
from app.services.job_runner import run_ingestion_job
from app.repositories.job import JobRepository
from app.core.config import settings

router = APIRouter(prefix="/api/v1/stores", tags=["Stores"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post(
    "/upload",
    response_model=IngestionResult,
    summary="Upload and ingest store master CSV (synchronous)",
    description=(
        "Use this endpoint for files up to ~50K rows. "
        "Returns a full ingestion result synchronously. "
        "For the 500K-row performance file use /upload-async."
    ),
)
async def upload_stores(
    file: UploadFile = File(..., description="stores_master.csv"),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    result = await ingest_stores(content, file.filename, db)
    return result


@router.post(
    "/upload-async",
    response_model=dict,
    summary="Upload and ingest store master CSV (async background job)",
    description=(
        "Returns immediately with a job_id. "
        "Poll GET /api/v1/jobs/{job_id} to track progress. "
        "Use this for large files (e.g. stores_master_500k.csv)."
    ),
)
async def upload_stores_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    job_repo = JobRepository(db)
    job = await job_repo.create_job("stores", file.filename)
    await db.commit()

    background_tasks.add_task(
        run_ingestion_job,
        job.id, "stores", file.filename, content,
    )
    return {"job_id": job.id, "status": "pending", "message": "Job queued. Poll /api/v1/jobs/{job_id} for status."}
