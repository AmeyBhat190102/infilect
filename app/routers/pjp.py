from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import IngestionResult
from app.services.pjp_ingestion import ingest_pjp
from app.services.job_runner import run_ingestion_job
from app.repositories.job import JobRepository
from app.core.config import settings

router = APIRouter(prefix="/api/v1/pjp", tags=["PJP (Store-User Mapping)"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post(
    "/upload",
    response_model=IngestionResult,
    summary="Upload and ingest store-user mapping CSV (synchronous)",
    description=(
        "Upload AFTER stores and users have been ingested. "
        "Rows referencing unknown stores or users will be reported as errors."
    ),
)
async def upload_pjp(
    file: UploadFile = File(..., description="store_user_mapping.csv"),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    result = await ingest_pjp(content, file.filename, db)
    return result


@router.post(
    "/upload-async",
    response_model=dict,
    summary="Upload and ingest store-user mapping CSV (async background job)",
)
async def upload_pjp_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    job_repo = JobRepository(db)
    job = await job_repo.create_job("pjp", file.filename)
    await db.commit()

    background_tasks.add_task(
        run_ingestion_job,
        job.id, "pjp", file.filename, content,
    )
    return {"job_id": job.id, "status": "pending", "message": "Job queued. Poll /api/v1/jobs/{job_id} for status."}
