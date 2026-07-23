from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.departments.it.enums import (
    AccessType, AssetStatus, HardwareAssignmentStatus, ImpactLevel, IncidentSource,
    IncidentStatus, ITRequestCategory, PolicyDecision, ProvisioningStatus,
)


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("company_id", "asset_code", name="uq_assets_company_code"),
        UniqueConstraint("company_id", "serial_number", name="uq_assets_company_serial"),
        Index("ix_assets_company_status_type", "company_id", "status", "asset_type"),
        Index("ix_assets_company_employee", "company_id", "assigned_employee_id"),
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    asset_code: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[AssetStatus] = mapped_column(SAEnum(AssetStatus, name="asset_status", values_callable=enum_values), nullable=False, default=AssetStatus.AVAILABLE, server_default=AssetStatus.AVAILABLE.value)
    assigned_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    location: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


class SoftwareCatalog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "software_catalog"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_software_catalog_company_name"), Index("ix_software_catalog_company_active", "company_id", "is_active"))
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_manager_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    requires_it_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    license_limited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    available_license_count: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


class AccessRequest(TimestampMixin, Base):
    __tablename__ = "access_requests"
    __table_args__ = (Index("ix_access_requests_company_employee", "company_id", "employee_id"), Index("ix_access_requests_company_status", "company_id", "provisioning_status"))
    request_id: Mapped[UUID] = mapped_column(ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    access_type: Mapped[AccessType] = mapped_column(SAEnum(AccessType, name="it_access_type", values_callable=enum_values), nullable=False)
    target_system: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_role: Mapped[str | None] = mapped_column(String(255))
    business_reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_decision: Mapped[PolicyDecision] = mapped_column(SAEnum(PolicyDecision, name="it_policy_decision", values_callable=enum_values), nullable=False, default=PolicyDecision.PENDING, server_default=PolicyDecision.PENDING.value)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    provisioning_status: Mapped[ProvisioningStatus] = mapped_column(SAEnum(ProvisioningStatus, name="it_provisioning_status", values_callable=enum_values), nullable=False, default=ProvisioningStatus.PENDING, server_default=ProvisioningStatus.PENDING.value)
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HardwareRequest(TimestampMixin, Base):
    __tablename__ = "hardware_requests"
    __table_args__ = (Index("ix_hardware_requests_company_employee", "company_id", "employee_id"), Index("ix_hardware_requests_company_status", "company_id", "assignment_status"))
    request_id: Mapped[UUID] = mapped_column(ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_specification: Mapped[str | None] = mapped_column(Text)
    business_reason: Mapped[str] = mapped_column(Text, nullable=False)
    inventory_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    available_asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    budget_validation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    procurement_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    assignment_status: Mapped[HardwareAssignmentStatus] = mapped_column(SAEnum(HardwareAssignmentStatus, name="hardware_assignment_status", values_callable=enum_values), nullable=False, default=HardwareAssignmentStatus.PENDING, server_default=HardwareAssignmentStatus.PENDING.value)
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ITIncident(TimestampMixin, Base):
    __tablename__ = "it_incidents"
    __table_args__ = (Index("ix_it_incidents_company_status", "company_id", "incident_status"), Index("ix_it_incidents_company_reporter", "company_id", "reported_by_user_id"))
    request_id: Mapped[UUID] = mapped_column(ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    affected_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    source: Mapped[IncidentSource] = mapped_column(SAEnum(IncidentSource, name="it_incident_source", values_callable=enum_values), nullable=False)
    category: Mapped[ITRequestCategory] = mapped_column(SAEnum(ITRequestCategory, name="it_request_category", values_callable=enum_values), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    error_messages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    impact: Mapped[ImpactLevel] = mapped_column(SAEnum(ImpactLevel, name="it_impact_level", values_callable=enum_values), nullable=False, default=ImpactLevel.MEDIUM, server_default=ImpactLevel.MEDIUM.value)
    urgency: Mapped[ImpactLevel] = mapped_column(SAEnum(ImpactLevel, name="it_urgency_level", values_callable=enum_values), nullable=False, default=ImpactLevel.MEDIUM, server_default=ImpactLevel.MEDIUM.value)
    diagnostic_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    incident_status: Mapped[IncidentStatus] = mapped_column(SAEnum(IncidentStatus, name="it_incident_status", values_callable=enum_values), nullable=False, default=IncidentStatus.NEW, server_default=IncidentStatus.NEW.value)
    requires_human_technician: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
