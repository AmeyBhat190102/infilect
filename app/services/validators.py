"""
Row-level validation helpers.

Each validate_* function receives a raw dict (one CSV row) and returns
(parsed_model | None, list[RowError]).

Design: we use Pydantic schemas for coercion + format rules,
then add business-rule checks (uniqueness within batch) here.
"""

from typing import Any
from pydantic import ValidationError

from app.schemas.store import StoreRow
from app.schemas.user import UserRow
from app.schemas.pjp import PJPRow
from app.schemas.common import RowError


def _pydantic_errors(exc: ValidationError, row_num: int) -> list[RowError]:
    errors = []
    for e in exc.errors():
        field = ".".join(str(loc) for loc in e["loc"]) if e["loc"] else "unknown"
        errors.append(RowError(
            row=row_num,
            column=field,
            value=e.get("input"),
            reason=e["msg"],
        ))
    return errors


def validate_store_row(raw: dict[str, Any], row_num: int) -> tuple[StoreRow | None, list[RowError]]:
    try:
        parsed = StoreRow(**raw)
        return parsed, []
    except ValidationError as exc:
        return None, _pydantic_errors(exc, row_num)


def validate_user_row(raw: dict[str, Any], row_num: int) -> tuple[UserRow | None, list[RowError]]:
    try:
        parsed = UserRow(**raw)
        return parsed, []
    except ValidationError as exc:
        return None, _pydantic_errors(exc, row_num)


def validate_pjp_row(raw: dict[str, Any], row_num: int) -> tuple[PJPRow | None, list[RowError]]:
    try:
        parsed = PJPRow.from_csv_row(raw)
        return parsed, []
    except ValidationError as exc:
        return None, _pydantic_errors(exc, row_num)


def check_batch_uniqueness_stores(
    rows: list[tuple[int, StoreRow]]
) -> tuple[list[tuple[int, StoreRow]], list[RowError]]:
    """
    Within a single chunk, detect duplicate store_ids.
    Returns (deduplicated_rows, duplicate_errors).
    """
    seen: dict[str, int] = {}
    valid, errors = [], []
    for row_num, row in rows:
        key = row.store_id.lower()
        if key in seen:
            errors.append(RowError(
                row=row_num,
                column="store_id",
                value=row.store_id,
                reason=f"Duplicate store_id in this file (first seen at row {seen[key]})",
            ))
        else:
            seen[key] = row_num
            valid.append((row_num, row))
    return valid, errors


def check_batch_uniqueness_users(
    rows: list[tuple[int, UserRow]]
) -> tuple[list[tuple[int, UserRow]], list[RowError]]:
    """Within a single chunk, detect duplicate usernames."""
    seen: dict[str, int] = {}
    valid, errors = [], []
    for row_num, row in rows:
        key = row.username.lower()
        if key in seen:
            errors.append(RowError(
                row=row_num,
                column="username",
                value=row.username,
                reason=f"Duplicate username in this file (first seen at row {seen[key]})",
            ))
        else:
            seen[key] = row_num
            valid.append((row_num, row))
    return valid, errors


def check_batch_uniqueness_pjp(
    rows: list[tuple[int, PJPRow]]
) -> tuple[list[tuple[int, PJPRow]], list[RowError]]:
    """Within a single chunk, detect duplicate (username, store_id, visit_date) combos."""
    seen: dict[tuple, int] = {}
    valid, errors = [], []
    for row_num, row in rows:
        key = (row.username.lower(), row.store_id.lower(), row.visit_date)
        if key in seen:
            errors.append(RowError(
                row=row_num,
                column="username/store_id/date",
                value=f"{row.username}/{row.store_id}/{row.visit_date}",
                reason=f"Duplicate mapping in this file (first seen at row {seen[key]})",
            ))
        else:
            seen[key] = row_num
            valid.append((row_num, row))
    return valid, errors
