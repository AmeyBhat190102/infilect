from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.lookup import LOOKUP_MODEL_MAP


def normalize(value: str) -> str:
    """
    Canonical form for all lookup values:
      - strip whitespace
      - title-case  (so "mumbai", "MUMBAI", "Mumbai " → "Mumbai")

    This prevents duplicate entries for the same logical value written
    differently across CSV rows.
    """
    return value.strip().title()


class LookupService:
    """
    Manages all six lookup tables with a per-request in-memory cache.

    Cache key: (table_name, normalized_name)
    Cache value: row id (int)

    This means each lookup table is only hit once per unique normalized value
    per upload request — critical for the 500K-row case.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[tuple[str, str], int] = {}

    async def preload(self, field: str) -> None:
        """Load an entire lookup table into the cache upfront."""
        model = LOOKUP_MODEL_MAP[field]
        result = await self.session.execute(select(model))
        for row in result.scalars().all():
            self._cache[(field, row.name)] = row.id

    async def get_or_create(self, field: str, raw_value: Optional[str]) -> Optional[int]:
        """
        Given a field name (e.g. "city") and a raw CSV value, return the PK
        of the corresponding lookup row — creating it if it doesn't exist.

        Returns None if raw_value is blank/None.
        """
        if not raw_value or str(raw_value).strip() == "":
            return None

        canonical = normalize(raw_value)
        cache_key = (field, canonical)

        if cache_key in self._cache:
            return self._cache[cache_key]

        model = LOOKUP_MODEL_MAP[field]

        # Try DB lookup first (another worker may have created it)
        result = await self.session.execute(
            select(model).where(model.name == canonical)
        )
        existing = result.scalar_one_or_none()

        if existing:
            self._cache[cache_key] = existing.id
            return existing.id

        # Insert, ignore conflict (race-safe)
        stmt = (
            pg_insert(model)
            .values(name=canonical)
            .on_conflict_do_nothing()
            .returning(model.id)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if row:
            new_id = row[0]
        else:
            # Was created by concurrent request between our SELECT and INSERT
            result = await self.session.execute(
                select(model).where(model.name == canonical)
            )
            new_id = result.scalar_one().id

        await self.session.flush()  # make ID visible within transaction
        self._cache[cache_key] = new_id
        return new_id
