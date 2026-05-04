from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import JobStatus, RowError
from app.repositories.job import JobRepository

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    response_model=JobStatus,
    summary="Poll job status",
)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = JobRepository(db)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")

    errors = None
    if job.errors:
        errors = [
            RowError(**e) if isinstance(e, dict) and "row" in e
            else RowError(row=0, column="system", value=None, reason=str(e))
            for e in job.errors
        ]

    return JobStatus(
        job_id=job.id,
        file_type=job.file_type,
        filename=job.filename,
        status=job.status,
        total_rows=job.total_rows,
        success_rows=job.success_rows,
        failed_rows=job.failed_rows,
        errors=errors,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
