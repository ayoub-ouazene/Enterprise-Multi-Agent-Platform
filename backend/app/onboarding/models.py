from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.onboarding.enums import ImportJobStatus, ImportType


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        Index("ix_import_jobs_company_status", "company_id", "status"),
        Index("ix_import_jobs_company_type", "company_id", "import_type"),
        Index("ix_import_jobs_checksum", "company_id", "import_type", "checksum"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    import_type: Mapped[ImportType] = mapped_column(
        SAEnum(
            ImportType,
            name="import_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        SAEnum(
            ImportJobStatus,
            name="import_job_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=ImportJobStatus.PENDING,
        server_default=ImportJobStatus.PENDING.value,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    total_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    valid_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    invalid_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    processed_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_report: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
