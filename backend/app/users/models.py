from typing import TYPE_CHECKING
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ActorType, enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.employees.models import Employee


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_users_company_email"),
        Index("ix_users_company_id", "company_id"),
        Index("ix_users_company_actor_type", "company_id", "actor_type"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[ActorType] = mapped_column(
        SAEnum(
            ActorType,
            name="actor_type",
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

    company: Mapped["Company"] = relationship(
        back_populates="users",
        lazy="raise",
    )
    employee: Mapped["Employee | None"] = relationship(
        back_populates="user",
        uselist=False,
        lazy="raise",
    )
