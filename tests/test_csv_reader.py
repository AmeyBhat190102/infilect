import pytest
from app.services.csv_reader import iter_csv_chunks, count_csv_rows


SAMPLE_CSV = b"""store_id,name,title
STR001,Store 1,Title 1
STR002,Store 2,Title 2
STR003,Store 3,Title 3
STR004,Store 4,Title 4
STR005,Store 5,Title 5
"""


def test_iter_chunks_basic():
    chunks = list(iter_csv_chunks(SAMPLE_CSV, chunk_size=2))
    # 5 rows / chunk_size 2 → 3 chunks
    assert len(chunks) == 3


def test_iter_chunks_column_normalisation():
    csv_with_spaces = b"Store ID , Name \nSTR001, My Store\n"
    chunks = list(iter_csv_chunks(csv_with_spaces, chunk_size=100))
    assert "store_id" in chunks[0][1].columns
    assert "name" in chunks[0][1].columns


def test_count_csv_rows():
    count = count_csv_rows(SAMPLE_CSV)
    assert count == 5
