from typing import Any
from pydantic import BaseModel


class RowError(BaseModel):
    row: int
    column: str
    value: Any
    reason: str


class IngestionResult(BaseModel):
    filename: str
    total_rows: int
    success_rows: int
    failed_rows: int
    errors: list[RowError]


class JobStatus(BaseModel):
    job_id: str
    file_type: str
    filename: str
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    errors: list[RowError] | None = None
    started_at: str | None = None
    completed_at: str | None = None
