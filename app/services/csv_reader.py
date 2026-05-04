"""
Streaming CSV reader using pandas with chunked iteration.

Yields (chunk_index, DataFrame) tuples so the ingestion service
can process one chunk at a time without loading the entire file into memory.

This is what makes the 500K-row file tractable:
  - memory footprint = O(chunk_size) rows, not O(total_rows)
  - each chunk is independently validated + bulk-inserted
"""

import io
from typing import Generator

import pandas as pd


def iter_csv_chunks(
    content: bytes,
    chunk_size: int = 2000,
) -> Generator[tuple[int, pd.DataFrame], None, None]:
    """
    Yield (chunk_index, dataframe) for each chunk of the CSV.

    - Strips leading/trailing whitespace from all string columns.
    - Replaces pandas NaN with None so downstream code can use `is None`.
    - chunk_index is 0-based.
    """
    buf = io.BytesIO(content)
    reader = pd.read_csv(
        buf,
        chunksize=chunk_size,
        dtype=str,          # read everything as string; Pydantic does coercion
        keep_default_na=False,
        na_values=["", "NA", "N/A", "null", "NULL", "None", "none"],
    )

    for chunk_idx, chunk in enumerate(reader):
        # Normalise column names: lowercase + strip
        chunk.columns = [c.strip().lower().replace(" ", "_") for c in chunk.columns]

        # Strip whitespace from every cell
        for col in chunk.columns:
            chunk[col] = chunk[col].apply(
                lambda x: x.strip() if isinstance(x, str) else x
            )

        # Replace pandas NA/NaN with Python None
        chunk = chunk.where(pd.notna(chunk), other=None)

        yield chunk_idx, chunk


def count_csv_rows(content: bytes) -> int:
    """Fast row count without reading the full dataframe into memory."""
    buf = io.BytesIO(content)
    count = sum(1 for _ in buf) - 1  # subtract header
    return max(count, 0)
