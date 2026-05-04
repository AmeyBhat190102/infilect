"""
Store ingestion pipeline.

Flow per chunk:
  1. Validate each row with Pydantic (StoreRow)
  2. Deduplicate within chunk by store_id
  3. Resolve lookup FKs via LookupService (get-or-create, cached)
  4. Bulk-insert valid rows via BaseRepository.bulk_insert
  5. Collect errors for the response

Policy: SKIP bad rows, ingest the rest.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.repositories.base import BaseRepository
from app.repositories.lookup import LookupService
from app.schemas.common import RowError, IngestionResult
from app.services.csv_reader import iter_csv_chunks, count_csv_rows
from app.services.validators import (
    validate_store_row,
    check_batch_uniqueness_stores,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

LOOKUP_FIELDS = ["store_brand", "store_type", "city", "state", "country", "region"]


async def ingest_stores(
    content: bytes,
    filename: str,
    session: AsyncSession,
) -> IngestionResult:
    """
    Main entry point for store CSV ingestion.
    Streams file in chunks, validates, resolves lookups, bulk-inserts.
    """
    repo = BaseRepository(Store, session)
    lookup_svc = LookupService(session)

    # Preload all existing lookup values into cache once
    for field in LOOKUP_FIELDS:
        await lookup_svc.preload(field)

    total_rows = 0
    success_rows = 0
    all_errors: list[RowError] = []

    for chunk_idx, chunk in iter_csv_chunks(content, settings.CSV_CHUNK_SIZE):
        rows_to_insert: list[dict[str, Any]] = []
        parsed_rows = []

        for local_idx, raw in enumerate(chunk.to_dict(orient="records")):
            # Global 1-based row number (account for header row)
            global_row = chunk_idx * settings.CSV_CHUNK_SIZE + local_idx + 2

            parsed, errors = validate_store_row(raw, global_row)
            if errors:
                all_errors.extend(errors)
                total_rows += 1
            else:
                parsed_rows.append((global_row, parsed))
                total_rows += 1

        # Dedup within chunk
        parsed_rows, dup_errors = check_batch_uniqueness_stores(parsed_rows)
        all_errors.extend(dup_errors)

        # Resolve lookup FKs and build insert dicts
        for row_num, parsed in parsed_rows:
            try:
                lookup_ids = {}
                for field in LOOKUP_FIELDS:
                    val = getattr(parsed, field, None)
                    lookup_ids[f"{field}_id"] = await lookup_svc.get_or_create(field, val)

                rows_to_insert.append({
                    "store_id": parsed.store_id,
                    "store_external_id": parsed.store_external_id or "",
                    "name": parsed.name,
                    "title": parsed.title,
                    "latitude": parsed.latitude,
                    "longitude": parsed.longitude,
                    "is_active": parsed.is_active,
                    "created_on": datetime.utcnow(),
                    "modified_on": datetime.utcnow(),
                    **lookup_ids,
                })
            except Exception as e:
                all_errors.append(RowError(
                    row=row_num,
                    column="lookup",
                    value=None,
                    reason=f"Lookup resolution failed: {e}",
                ))

        inserted = await repo.bulk_insert(rows_to_insert)
        success_rows += inserted

        logger.info(
            "Stores chunk %d: %d inserted, %d errors so far",
            chunk_idx, inserted, len(all_errors),
        )

    return IngestionResult(
        filename=filename,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=total_rows - success_rows,
        errors=all_errors,
    )
