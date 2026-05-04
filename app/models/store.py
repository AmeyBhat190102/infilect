from datetime import datetime
from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    store_external_id: Mapped[str] = mapped_column(String(255), default="")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    store_brand_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("store_brands.id", ondelete="SET NULL"), nullable=True
    )
    store_type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("store_types.id", ondelete="SET NULL"), nullable=True
    )
    city_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cities.id", ondelete="SET NULL"), nullable=True
    )
    state_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("states.id", ondelete="SET NULL"), nullable=True
    )
    country_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("countries.id", ondelete="SET NULL"), nullable=True
    )
    region_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True
    )

    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_on: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow
    )
    modified_on: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow
    )
