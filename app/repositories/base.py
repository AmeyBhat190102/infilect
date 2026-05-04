from typing import Any, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import Base


class BaseRepository:
    """
    Generic repository with bulk-insert helpers.
    Subclasses inject model at construction time.
    """

    def __init__(self, model: Type[Base], session: AsyncSession):
        self.model = model
        self.session = session

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> int:
        """
        Insert many rows efficiently using PostgreSQL INSERT ... ON CONFLICT DO NOTHING.
        Returns the number of rows inserted.
        """
        if not rows:
            return 0

        stmt = (
            pg_insert(self.model)
            .values(rows)
            .on_conflict_do_nothing()
        )
        result = await self.session.execute(stmt)
        return result.rowcount or len(rows)

    async def get_by_field(self, field: str, value: Any):
        stmt = select(self.model).where(
            getattr(self.model, field) == value
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_field(self, field: str, value: Any) -> bool:
        return await self.get_by_field(field, value) is not None
