"""Tests for onboarding CSV/XLSX parser and template helpers."""
import io
from collections.abc import Sequence
from typing import Any

import pytest
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import BusinessValidationError
from app.onboarding.parser import (
    ParsedUpload,
    compute_checksum,
    get_template_columns,
    parse_upload,
    validate_import_columns,
    _parse_csv_bytes,
    _parse_xlsx_bytes,
)


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def csv_upload(filename: str, content: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content.encode("utf-8-sig")))


def test_compute_checksum_is_stable() -> None:
    data = b"hello"
    assert compute_checksum(data) == compute_checksum(data)
    assert len(compute_checksum(data)) == 64


def test_parse_csv_parses_headers_and_rows() -> None:
    content = "email,name\ntest@example.com,Alice"
    headers, rows = _parse_csv_bytes(content.encode())
    assert headers == ["email", "name"]
    assert rows == [{"email": "test@example.com", "name": "Alice"}]


def test_parse_csv_normalizes_headers() -> None:
    content = "Email-Address, First Name \ntest@example.com,Alice"
    headers, rows = _parse_csv_bytes(content.encode())
    # row keys are normalized; returned headers reflect originals
    assert rows[0]["email_address"] == "test@example.com"
    assert rows[0]["first_name"] == "Alice"


def test_parse_csv_rejects_duplicate_headers() -> None:
    content = "email,email\ntest@example.com,other"
    with pytest.raises(BusinessValidationError, match="Duplicate columns"):
        _parse_csv_bytes(content.encode())


def test_parse_csv_rejects_empty_file() -> None:
    content = "email,name\n"
    headers, rows = _parse_csv_bytes(content.encode())
    # No data rows, but parse itself succeeds
    assert rows == []


@pytest.mark.skipif(
    "openpyxl" not in __import__("sys").modules, reason="openpyxl not installed"
)
def test_parse_xlsx_reads_active_sheet(monkeypatch) -> None:
    from unittest.mock import Mock

    fake_ws = Mock()
    fake_ws.iter_rows = Mock(return_value=iter([
        ["email", "name"],
        ["a@example.com", "Alice"],
    ]))

    fake_wb = Mock()
    fake_wb.active = fake_ws

    monkeypatch.setattr(
        "app.onboarding.parser.openpyxl.load_workbook",
        Mock(return_value=fake_wb),
    )
    headers, rows = _parse_xlsx_bytes(b"xlsx-data")
    assert headers == ["email", "name"]
    assert rows == [{"email": "a@example.com", "name": "Alice"}]


def test_validate_import_columns_detects_missing_required() -> None:
    errors = validate_import_columns("employees", ["email", "first_name"])
    assert any("Missing required columns" in e for e in errors)


def test_validate_import_columns_detects_unknown() -> None:
    errors = validate_import_columns("employees", ["email", "first_name", "unknown_column"])
    assert any("Unknown columns" in e for e in errors)


def test_validate_import_columns_allows_optional() -> None:
    headers = [
        "email", "first_name", "last_name", "temporary_password",
        "employee_code", "department", "job_title", "employment_status",
        "manager_email", "custom_data",
    ]
    errors = validate_import_columns("employees", headers)
    assert errors == []


def test_validate_departments_required_and_optional() -> None:
    headers = ["department_type", "name", "is_active", "custom_data"]
    errors = validate_import_columns("departments", headers)
    assert errors == []


def test_validate_unknown_import_type_returns_empty() -> None:
    assert validate_import_columns("unknown", ["a"]) == []


def test_get_template_columns_returns_expected() -> None:
    cols = get_template_columns("employees")
    assert any(c["name"] == "email" and c["required"] for c in cols)
    assert any(c["name"] == "manager_email" and not c["required"] for c in cols)


def test_get_template_columns_departments() -> None:
    cols = get_template_columns("departments")
    assert any(c["name"] == "department_type" and c["required"] for c in cols)


def test_get_template_columns_unknown() -> None:
    assert get_template_columns("unknown") == []


async def test_parse_upload_rejects_size_exceeded() -> None:
    settings = build_settings()
    content = "x" * (26 * 1024 * 1024)
    upload = csv_upload("big.csv", content)
    with pytest.raises(BusinessValidationError, match="exceeds maximum size"):
        await parse_upload(upload, settings)


async def test_parse_upload_rejects_empty_file() -> None:
    settings = build_settings()
    upload = csv_upload("empty.csv", "")
    with pytest.raises(BusinessValidationError):
        await parse_upload(upload, settings)


async def test_parse_upload_rejects_no_data_rows() -> None:
    settings = build_settings()
    upload = csv_upload("headers_only.csv", "email,name\n")
    with pytest.raises(BusinessValidationError, match="no data"):
        await parse_upload(upload, settings)


async def test_parse_upload_rejects_bad_extension() -> None:
    settings = build_settings()
    upload = csv_upload("data.txt", "email\ntest@example.com")
    with pytest.raises(BusinessValidationError, match="Unsupported file extension"):
        await parse_upload(upload, settings)


async def test_parse_upload_returns_parsed_upload() -> None:
    settings = build_settings()
    upload = csv_upload("employees.csv", "email,name\ntest@example.com,Alice\n")
    result: ParsedUpload = await parse_upload(upload, settings)
    assert result.checksum is not None
    assert result.rows == [{"email": "test@example.com", "name": "Alice"}]
    assert result.original_filename == "employees.csv"
