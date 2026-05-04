"""
Unit tests for row-level validators.
These run without a DB — pure Python logic.
"""

import pytest
from app.services.validators import validate_store_row, validate_user_row, validate_pjp_row


# ─── Store tests ──────────────────────────────────────────────────────────────

def test_valid_store_row():
    raw = {
        "store_id": "STR001", "name": "Test Store", "title": "Test Title",
        "store_brand": "Nike", "store_type": "Flagship",
        "city": "Mumbai", "state": "Maharashtra", "country": "India", "region": "West",
        "latitude": "19.076", "longitude": "72.877", "is_active": "True",
    }
    parsed, errors = validate_store_row(raw, 2)
    assert parsed is not None
    assert errors == []
    assert parsed.latitude == 19.076


def test_store_missing_store_id():
    raw = {"store_id": "", "name": "Test", "title": "Test"}
    _, errors = validate_store_row(raw, 2)
    assert any(e.column == "store_id" for e in errors)


def test_store_latitude_out_of_range():
    raw = {"store_id": "STR001", "name": "Test", "title": "T", "latitude": "999"}
    _, errors = validate_store_row(raw, 3)
    assert any(e.column == "latitude" for e in errors)


def test_store_longitude_not_number():
    raw = {"store_id": "STR001", "name": "Test", "title": "T", "longitude": "abc"}
    _, errors = validate_store_row(raw, 4)
    assert any(e.column == "longitude" for e in errors)


def test_store_id_too_long():
    raw = {"store_id": "X" * 300, "name": "Test", "title": "T"}
    _, errors = validate_store_row(raw, 5)
    assert any(e.column == "store_id" for e in errors)


# ─── User tests ───────────────────────────────────────────────────────────────

def test_valid_user_row():
    raw = {
        "username": "john_doe", "first_name": "John", "last_name": "Doe",
        "email": "john@example.com", "user_type": "1",
        "phone_number": "+91-98765-43210", "is_active": "True",
    }
    parsed, errors = validate_user_row(raw, 2)
    assert parsed is not None
    assert errors == []


def test_user_bad_email():
    raw = {"username": "jdoe", "email": "not-an-email", "user_type": "1"}
    _, errors = validate_user_row(raw, 3)
    assert any(e.column == "email" for e in errors)


def test_user_invalid_user_type():
    raw = {"username": "jdoe", "email": "j@x.com", "user_type": "5"}
    _, errors = validate_user_row(raw, 4)
    assert any(e.column == "user_type" for e in errors)


def test_user_missing_username():
    raw = {"username": "", "email": "j@x.com"}
    _, errors = validate_user_row(raw, 5)
    assert any(e.column == "username" for e in errors)


def test_user_invalid_phone():
    raw = {"username": "jdoe", "email": "j@x.com", "phone_number": "ABCDEF"}
    _, errors = validate_user_row(raw, 6)
    assert any(e.column == "phone_number" for e in errors)


# ─── PJP tests ────────────────────────────────────────────────────────────────

def test_valid_pjp_row():
    raw = {"username": "user001", "store_id": "STR0001", "date": "2024-03-15", "is_active": "True"}
    parsed, errors = validate_pjp_row(raw, 2)
    assert parsed is not None
    assert errors == []
    assert parsed.visit_date is not None


def test_pjp_bad_date():
    raw = {"username": "user001", "store_id": "STR0001", "date": "not-a-date"}
    _, errors = validate_pjp_row(raw, 3)
    assert any(e.column == "visit_date" for e in errors)


def test_pjp_missing_username():
    raw = {"username": "", "store_id": "STR0001"}
    _, errors = validate_pjp_row(raw, 4)
    assert any(e.column == "username" for e in errors)
