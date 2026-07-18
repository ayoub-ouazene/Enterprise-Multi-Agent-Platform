from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.departments.models import Department
    from app.employees.models import Employee
    from app.users.models import User


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_companies_slug"),
        Index("ix_companies_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
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

    users: Mapped[list["User"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    departments: Mapped[list["Department"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
