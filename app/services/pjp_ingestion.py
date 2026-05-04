"""
PJP (store-user mapping) ingestion pipeline.

Depends on stores and users already being in the DB.
For each chunk:
  1. Validate rows with PJPRow schema
  2. Dedup within chunk by (username, store_id, date)
  3. Batch-fetch user PKs and store PKs (one query each)
  4. Report missing references as errors
  5. Bulk-insert valid rows
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pjp import PermanentJourneyPlan
from app.repositories.base import BaseRepository
from app.repositories.store import StoreRepository
from app.repositories.user import UserRepository
from app.schemas.common import RowError, IngestionResult
from app.services.csv_reader import iter_csv_chunks
from app.services.validators import validate_pjp_row, check_batch_uniqueness_pjp
from app.core.config import settings

logger = logging.getLogger(__name__)


async def ingest_pjp(
    content: bytes,
    filename: str,
    session: AsyncSession,
) -> IngestionResult:
    repo = BaseRepository(PermanentJourneyPlan, session)
    store_repo = StoreRepository(session)
    user_repo = UserRepository(session)

    total_rows = 0
    success_rows = 0
    all_errors: list[RowError] = []

    for chunk_idx, chunk in iter_csv_chunks(content, settings.CSV_CHUNK_SIZE):
        parsed_rows = []

        for local_idx, raw in enumerate(chunk.to_dict(orient="records")):
            global_row = chunk_idx * settings.CSV_CHUNK_SIZE + local_idx + 2
            parsed, errors = validate_pjp_row(raw, global_row)
            if errors:
                all_errors.extend(errors)
                total_rows += 1
            else:
                parsed_rows.append((global_row, parsed))
                total_rows += 1

        parsed_rows, dup_errors = check_batch_uniqueness_pjp(parsed_rows)
        all_errors.extend(dup_errors)

        if not parsed_rows:
            continue

        # Batch-resolve FKs in 2 DB queries
        usernames = list({p.username for _, p in parsed_rows})
        store_ids = list({p.store_id for _, p in parsed_rows})

        username_map = await user_repo.build_username_map(usernames)
        store_id_map = await store_repo.build_store_id_map(store_ids)

        rows_to_insert: list[dict[str, Any]] = []

        for row_num, parsed in parsed_rows:
            user_pk = username_map.get(parsed.username)
            store_pk = store_id_map.get(parsed.store_id)

            if user_pk is None:
                all_errors.append(RowError(
                    row=row_num,
                    column="username",
                    value=parsed.username,
                    reason=f"User '{parsed.username}' does not exist in the database",
                ))
                continue

            if store_pk is None:
                all_errors.append(RowError(
                    row=row_num,
                    column="store_id",
                    value=parsed.store_id,
                    reason=f"Store '{parsed.store_id}' does not exist in the database",
                ))
                continue

            rows_to_insert.append({
                "user_id": user_pk,
                "store_id": store_pk,
                "date": parsed.visit_date,
                "is_active": parsed.is_active,
                "created_on": datetime.utcnow(),
                "modified_on": datetime.utcnow(),
            })

        inserted = await repo.bulk_insert(rows_to_insert)
        success_rows += inserted

        logger.info(
            "PJP chunk %d: %d inserted, %d errors so far",
            chunk_idx, inserted, len(all_errors),
        )

    return IngestionResult(
        filename=filename,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=total_rows - success_rows,
        errors=all_errors,
    )
