import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import IngestionJob
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(IngestionJob, session)

    async def create_job(self, file_type: str, filename: str) -> IngestionJob:
        job = IngestionJob(
            id=str(uuid.uuid4()),
            file_type=file_type,
            filename=filename,
            status="pending",
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: str) -> IngestionJob | None:
        result = await self.session.execute(
            select(IngestionJob).where(IngestionJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_job(self, job: IngestionJob, **kwargs) -> IngestionJob:
        for k, v in kwargs.items():
            setattr(job, k, v)
        self.session.add(job)
        await self.session.flush()
        return job
