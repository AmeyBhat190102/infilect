from datetime import datetime, date
from sqlalchemy import Integer, Boolean, ForeignKey, TIMESTAMP, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PermanentJourneyPlan(Base):
    __tablename__ = "permanent_journey_plans"

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "date", name="uq_pjp_user_store_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_on: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow
    )
    modified_on: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow
    )
