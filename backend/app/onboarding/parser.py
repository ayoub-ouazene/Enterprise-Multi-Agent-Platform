import csv
import hashlib
import io
import tempfile
from collections.abc import Sequence
from typing import Any

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import BusinessValidationError


MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".csv", ".xlsx"})
ALLOWED_MIME_TYPES = frozenset({
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
})


def _extension(filename: str) -> str:
    if "." in filename:
        return filename[filename.rfind(".") :].lower()
    return ""


def _validate_file_meta(
    upload: UploadFile,
    settings: Settings,
) -> None:
    filename = upload.filename or ""
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessValidationError(
            f"Unsupported file extension: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    mime = (upload.content_type or "").lower()
    if mime and mime not in ALLOWED_MIME_TYPES:
        raise BusinessValidationError(
            f"Unsupported MIME type: {mime}"
        )


async def _read_upload_bytes(upload: UploadFile) -> bytes:
    content = await upload.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise BusinessValidationError(
            f"File exceeds maximum size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
        )
    if not content:
        raise BusinessValidationError("Uploaded file is empty")
    return content


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_").replace("-", "_")


def _detect_duplicate_columns(headers: list[str]) -> list[str]:
    normalized = [_normalize_header(h) for h in headers]
    seen: set[str] = set()
    duplicates: list[str] = []
    for h in normalized:
        if h in seen:
            duplicates.append(h)
        seen.add(h)
    return duplicates


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------


def _parse_csv_bytes(data: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise BusinessValidationError("CSV file has no headers")
    headers = list(reader.fieldnames)
    duplicates = _detect_duplicate_columns(headers)
    if duplicates:
        raise BusinessValidationError(
            f"Duplicate columns detected: {', '.join(duplicates)}"
        )
    rows: list[dict[str, Any]] = []
    for line in reader:
        row: dict[str, Any] = {}
        for key, value in line.items():
            if key is not None:
                row[_normalize_header(key)] = value.strip() if value is not None else ""
        rows.append(row)
    return headers, rows


# ---------------------------------------------------------------------------
# XLSX parsing
# ---------------------------------------------------------------------------


def _parse_xlsx_bytes(data: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise BusinessValidationError(
            "XLSX processing is not available"
        ) from exc

    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active
    if ws is None:
        raise BusinessValidationError("XLSX file has no active worksheet")

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise BusinessValidationError("XLSX file has no data")

    headers = [str(h) if h is not None else "" for h in header_row]
    duplicates = _detect_duplicate_columns(headers)
    if duplicates:
        raise BusinessValidationError(
            f"Duplicate columns detected: {', '.join(duplicates)}"
        )

    normalized_headers = [_normalize_header(h) for h in headers]
    rows: list[dict[str, Any]] = []
    for raw in rows_iter:
        row: dict[str, Any] = {}
        for idx, key in enumerate(normalized_headers):
            cell = raw[idx] if idx < len(raw) else None
            if cell is None:
                row[key] = ""
            else:
                row[key] = str(cell).strip()
        rows.append(row)

    return headers, rows


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


class ParsedUpload:
    def __init__(
        self,
        headers: list[str],
        rows: list[dict[str, Any]],
        checksum: str,
        original_filename: str,
    ) -> None:
        self.headers = headers
        self.rows = rows
        self.checksum = checksum
        self.original_filename = original_filename


async def parse_upload(
    upload: UploadFile,
    settings: Settings,
) -> ParsedUpload:
    _validate_file_meta(upload, settings)
    data = await _read_upload_bytes(upload)
    filename = upload.filename or "unknown"
    ext = _extension(filename)
    checksum = compute_checksum(data)

    if ext == ".csv":
        headers, rows = _parse_csv_bytes(data)
    elif ext == ".xlsx":
        headers, rows = _parse_xlsx_bytes(data)
    else:
        raise BusinessValidationError(f"Unsupported file type: {ext}")

    if not rows:
        raise BusinessValidationError("File contains no data rows")

    return ParsedUpload(
        headers=headers,
        rows=rows,
        checksum=checksum,
        original_filename=filename,
    )


REQUIRED_EMPLOYEE_COLUMNS: set[str] = {
    "email",
    "first_name",
    "last_name",
    "temporary_password",
    "employee_code",
    "department",
    "job_title",
    "employment_status",
}

OPTIONAL_EMPLOYEE_COLUMNS: set[str] = {
    "manager_email",
    "custom_data",
}

REQUIRED_DEPARTMENT_COLUMNS: set[str] = {
    "department_type",
    "name",
}

OPTIONAL_DEPARTMENT_COLUMNS: set[str] = {
    "is_active",
    "custom_data",
}

REQUIRED_MANAGER_COLUMNS: set[str] = {
    "employee_email",
    "manager_email",
}


def _check_columns(
    present: set[str],
    required: set[str],
    optional: set[str],
) -> list[str]:
    errors: list[str] = []
    missing = required - present
    if missing:
        errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
    unknown = present - required - optional
    if unknown:
        errors.append(f"Unknown columns: {', '.join(sorted(unknown))}")
    return errors


def validate_import_columns(
    import_type: str,
    headers: list[str],
) -> list[str]:
    present = set(headers)
    if import_type == "employees":
        return _check_columns(
            present, REQUIRED_EMPLOYEE_COLUMNS, OPTIONAL_EMPLOYEE_COLUMNS
        )
    if import_type == "departments":
        return _check_columns(
            present, REQUIRED_DEPARTMENT_COLUMNS, OPTIONAL_DEPARTMENT_COLUMNS
        )
    if import_type == "manager_assignments":
        return _check_columns(
            present, REQUIRED_MANAGER_COLUMNS, set()
        )
    return []


def get_template_columns(import_type: str) -> list[dict[str, Any]]:
    """Return column metadata for downloadable templates."""
    if import_type == "employees":
        return [
            {"name": "email", "required": True},
            {"name": "first_name", "required": True},
            {"name": "last_name", "required": True},
            {"name": "temporary_password", "required": True},
            {"name": "employee_code", "required": True},
            {"name": "department", "required": True},
            {"name": "job_title", "required": True},
            {"name": "employment_status", "required": True},
            {"name": "manager_email", "required": False},
            {"name": "custom_data", "required": False},
        ]
    if import_type == "departments":
        return [
            {"name": "department_type", "required": True},
            {"name": "name", "required": True},
            {"name": "is_active", "required": False},
            {"name": "custom_data", "required": False},
        ]
    if import_type == "manager_assignments":
        return [
            {"name": "employee_email", "required": True},
            {"name": "manager_email", "required": True},
        ]
    return []
