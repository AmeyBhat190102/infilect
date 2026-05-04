"""
User ingestion pipeline.

Special handling:
  - supervisor_username: self-referential FK.
    We make two passes per chunk:
      Pass 1 — insert users without supervisor_id.
      Pass 2 — update supervisor_id using the username→id map built after pass 1.
    This allows supervisors and supervisees to be in the same file.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.schemas.common import RowError, IngestionResult
from app.services.csv_reader import iter_csv_chunks
from app.services.validators import validate_user_row, check_batch_uniqueness_users
from app.core.config import settings

logger = logging.getLogger(__name__)


async def ingest_users(
    content: bytes,
    filename: str,
    session: AsyncSession,
) -> IngestionResult:
    repo = BaseRepository(User, session)
    user_repo = UserRepository(session)

    total_rows = 0
    success_rows = 0
    all_errors: list[RowError] = []

    for chunk_idx, chunk in iter_csv_chunks(content, settings.CSV_CHUNK_SIZE):
        parsed_rows = []

        for local_idx, raw in enumerate(chunk.to_dict(orient="records")):
            global_row = chunk_idx * settings.CSV_CHUNK_SIZE + local_idx + 2
            parsed, errors = validate_user_row(raw, global_row)
            if errors:
                all_errors.extend(errors)
                total_rows += 1
            else:
                parsed_rows.append((global_row, parsed))
                total_rows += 1

        parsed_rows, dup_errors = check_batch_uniqueness_users(parsed_rows)
        all_errors.extend(dup_errors)

        # ------------------------------------------------------------------ #
        # Pass 1 — insert without supervisor_id
        # ------------------------------------------------------------------ #
        rows_to_insert: list[dict[str, Any]] = []
        supervisor_pending: list[tuple[str, str]] = []  # (username, supervisor_username)

        for _, parsed in parsed_rows:
            rows_to_insert.append({
                "username": parsed.username,
                "first_name": parsed.first_name or "",
                "last_name": parsed.last_name or "",
                "email": parsed.email,
                "user_type": parsed.user_type,
                "phone_number": parsed.phone_number or "",
                "is_active": parsed.is_active,
                "created_on": datetime.utcnow(),
                "modified_on": datetime.utcnow(),
                # supervisor_id intentionally omitted here
            })
            if parsed.supervisor_username:
                supervisor_pending.append(
                    (parsed.username, parsed.supervisor_username)
                )

        inserted = await repo.bulk_insert(rows_to_insert)
        success_rows += inserted

        # ------------------------------------------------------------------ #
        # Pass 2 — resolve supervisor FKs
        # ------------------------------------------------------------------ #
        if supervisor_pending:
            all_usernames = [s for _, s in supervisor_pending] + [u for u, _ in supervisor_pending]
            username_map = await user_repo.build_username_map(list(set(all_usernames)))

            for username, supervisor_username in supervisor_pending:
                user_pk = username_map.get(username)
                supervisor_pk = username_map.get(supervisor_username)

                if user_pk and supervisor_pk:
                    await session.execute(
                        update(User)
                        .where(User.id == user_pk)
                        .values(supervisor_id=supervisor_pk)
                    )
                elif user_pk and not supervisor_pk:
                    # Supervisor not found — log warning but row already inserted
                    logger.warning(
                        "Supervisor '%s' not found for user '%s'",
                        supervisor_username, username,
                    )

        logger.info(
            "Users chunk %d: %d inserted, %d errors so far",
            chunk_idx, inserted, len(all_errors),
        )

    return IngestionResult(
        filename=filename,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=total_rows - success_rows,
        errors=all_errors,
    )
