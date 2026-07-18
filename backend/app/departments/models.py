from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DepartmentType, enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.employees.models import Employee


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "department_type",
            name="uq_departments_company_type",
        ),
        Index("ix_departments_company_id", "company_id"),
        Index("ix_departments_company_active", "company_id", "is_active"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    department_type: Mapped[DepartmentType] = mapped_column(
        SAEnum(
            DepartmentType,
            name="department_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    company: Mapped["Company"] = relationship(
        back_populates="departments",
        lazy="raise",
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="department",
        lazy="raise",
    )
