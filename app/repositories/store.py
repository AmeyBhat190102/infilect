from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.store import Store
from app.repositories.base import BaseRepository


class StoreRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(Store, session)

    async def get_id_by_store_id(self, store_id: str) -> int | None:
        """Return the PK `id` for a given business-key `store_id`."""
        result = await self.session.execute(
            select(Store.id).where(Store.store_id == store_id)
        )
        row = result.scalar_one_or_none()
        return row

    async def build_store_id_map(self, store_ids: list[str]) -> dict[str, int]:
        """
        Fetch PK ids for a batch of store_ids in a single query.
        Returns {store_id: pk_id}.
        """
        result = await self.session.execute(
            select(Store.store_id, Store.id).where(Store.store_id.in_(store_ids))
        )
        return {row[0]: row[1] for row in result.fetchall()}
