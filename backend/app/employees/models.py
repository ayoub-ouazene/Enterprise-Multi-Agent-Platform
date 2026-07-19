from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Enum as SAEnum,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EmploymentStatus, enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.departments.models import Department
    from app.users.models import User


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "employee_code",
            name="uq_employees_company_code",
        ),
        UniqueConstraint("user_id", name="uq_employees_user_id"),
        Index("ix_employees_company_id", "company_id"),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_manager_id", "manager_employee_id"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_code: Mapped[str] = mapped_column(String(100), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    manager_employee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        SAEnum(
            EmploymentStatus,
            name="employment_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
        server_default=EmploymentStatus.ACTIVE.value,
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    company: Mapped["Company"] = relationship(
        back_populates="employees",
        lazy="raise",
    )
    user: Mapped["User | None"] = relationship(
        back_populates="employee",
        lazy="raise",
    )
    department: Mapped["Department | None"] = relationship(
        back_populates="employees",
        lazy="raise",
    )
    manager: Mapped["Employee | None"] = relationship(
        back_populates="subordinates",
        foreign_keys=[manager_employee_id],
        remote_side="Employee.id",
        lazy="raise",
    )
    subordinates: Mapped[list["Employee"]] = relationship(
        back_populates="manager",
        foreign_keys=[manager_employee_id],
        lazy="raise",
    )
