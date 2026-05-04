"""
Background job runner.

For large file uploads (e.g. 500K rows), the router enqueues a job and
returns immediately with a job_id.  This module runs the actual ingestion
in a FastAPI BackgroundTask.

To scale further: replace the BackgroundTask call with a Celery task
by swapping `run_ingestion_job` invocation — the interface is identical.
"""

import logging
from datetime import datetime

from app.database import AsyncSessionLocal
from app.repositories.job import JobRepository
from app.services.store_ingestion import ingest_stores
from app.services.user_ingestion import ingest_users
from app.services.pjp_ingestion import ingest_pjp

logger = logging.getLogger(__name__)

INGESTION_FN_MAP = {
    "stores": ingest_stores,
    "users": ingest_users,
    "pjp": ingest_pjp,
}


async def run_ingestion_job(job_id: str, file_type: str, filename: str, content: bytes):
    """
    Executes an ingestion job asynchronously.
    Opens its own DB session (separate from the request session).
    Updates the IngestionJob row with progress.
    """
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.get_job(job_id)

        if not job:
            logger.error("Job %s not found", job_id)
            return

        await job_repo.update_job(job, status="running", started_at=datetime.utcnow())
        await session.commit()

        try:
            ingest_fn = INGESTION_FN_MAP[file_type]
            result = await ingest_fn(content, filename, session)
            await session.commit()

            error_dicts = [e.model_dump() for e in result.errors]
            await job_repo.update_job(
                job,
                status="completed",
                total_rows=result.total_rows,
                success_rows=result.success_rows,
                failed_rows=result.failed_rows,
                errors=error_dicts,
                completed_at=datetime.utcnow(),
            )
            await session.commit()
            logger.info("Job %s completed: %d/%d rows ingested", job_id, result.success_rows, result.total_rows)

        except Exception as exc:
            await session.rollback()
            await job_repo.update_job(
                job,
                status="failed",
                errors=[{"reason": str(exc)}],
                completed_at=datetime.utcnow(),
            )
            await session.commit()
            logger.exception("Job %s failed: %s", job_id, exc)
