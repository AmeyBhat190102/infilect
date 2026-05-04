from datetime import datetime
from sqlalchemy import Integer, String, JSON, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngestionJob(Base):
    """Tracks long-running ingestion jobs (e.g. 500K row uploads)."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)   # UUID
    file_type: Mapped[str] = mapped_column(String(32))               # stores | users | pjp
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending | running | completed | failed

    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)

    errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

    created_on: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
