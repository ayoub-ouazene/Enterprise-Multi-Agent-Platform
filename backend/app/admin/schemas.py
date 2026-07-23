"""Admin schemas for company data management (11 areas)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DepartmentType, EmploymentStatus
from app.departments.finance.enums import BudgetStatus, BudgetType
from app.departments.hr.enums import LeaveType
from app.departments.it.enums import AssetStatus


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class AdminPagination(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# =============================================================================
# 1. Employee Directory
# =============================================================================

class AdminEmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=320)
    job_title: str | None = Field(default=None, max_length=160)
    department_id: UUID | None = None
    hire_date: date | None = None
    manager_employee_id: UUID | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminEmployeeUpdate(BaseModel):
    employee_code: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=320)
    job_title: str | None = Field(default=None, max_length=160)
    department_id: UUID | None = None
    hire_date: date | None = None
    manager_employee_id: UUID | None = None
    employment_status: EmploymentStatus | None = None
    custom_data: dict[str, Any] | None = None


class AdminEmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    employee_code: str
    job_title: str | None
    department_id: UUID | None
    hire_date: date | None
    manager_employee_id: UUID | None
    employment_status: str
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 2. Department Configuration
# =============================================================================

class AdminDepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None


class AdminDepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    department_type: str
    is_active: bool
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 3. Asset Inventory
# =============================================================================

class AdminAssetCreate(BaseModel):
    asset_code: str = Field(min_length=1, max_length=100)
    asset_type: str = Field(min_length=1, max_length=100)
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    serial_number: str | None = Field(default=None, max_length=255)
    status: AssetStatus = AssetStatus.AVAILABLE
    location: str | None = Field(default=None, max_length=255)
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminAssetUpdate(BaseModel):
    asset_code: str | None = Field(default=None, min_length=1, max_length=100)
    asset_type: str | None = Field(default=None, min_length=1, max_length=100)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    serial_number: str | None = Field(default=None, max_length=255)
    status: AssetStatus | None = None
    location: str | None = Field(default=None, max_length=255)
    custom_data: dict[str, Any] | None = None
    version: int = Field(ge=1)


class AdminAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_code: str
    asset_type: str
    brand: str
    model: str
    serial_number: str | None
    status: str
    location: str | None
    custom_data: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 4. Software Catalog
# =============================================================================

class AdminSoftwareCatalogCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    access_type: str = Field(min_length=1, max_length=100)
    requires_manager_approval: bool = False
    requires_it_approval: bool = True
    license_limited: bool = False
    available_license_count: int | None = Field(default=None, ge=0)
    is_active: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminSoftwareCatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    access_type: str | None = Field(default=None, min_length=1, max_length=100)
    requires_manager_approval: bool | None = None
    requires_it_approval: bool | None = None
    license_limited: bool | None = None
    available_license_count: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None
    version: int = Field(ge=1)


class AdminSoftwareCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    access_type: str
    requires_manager_approval: bool
    requires_it_approval: bool
    license_limited: bool
    available_license_count: int | None
    is_active: bool
    custom_data: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 5. Budget Management
# =============================================================================

class AdminBudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    budget_type: BudgetType
    currency: str = Field(min_length=3, max_length=3)
    period_start: date
    period_end: date
    allocated_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    approval_threshold: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    department_id: UUID | None = None
    status: BudgetStatus = BudgetStatus.DRAFT
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        v = value.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a three-letter code")
        return v

    @field_validator("period_end")
    @classmethod
    def period_end_after_start(cls, value: date, info) -> date:
        start = info.data.get("period_start")
        if start is not None and value < start:
            raise ValueError("period_end must be >= period_start")
        return value


class AdminBudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    budget_type: BudgetType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    period_start: date | None = None
    period_end: date | None = None
    allocated_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    approval_threshold: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    status: BudgetStatus | None = None
    custom_data: dict[str, Any] | None = None
    version: int = Field(ge=1)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        v = value.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a three-letter code")
        return v


class AdminBudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID | None
    name: str
    budget_type: str
    currency: str
    period_start: date
    period_end: date
    allocated_amount: Decimal
    reserved_amount: Decimal
    committed_amount: Decimal
    spent_amount: Decimal
    available_amount: Decimal
    status: str
    approval_threshold: Decimal | None
    custom_data: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 6. Leave Balances
# =============================================================================

class AdminLeaveBalanceCreate(BaseModel):
    employee_id: UUID
    leave_type: LeaveType
    year: int = Field(ge=2000, le=2100)
    allocated_days: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminLeaveBalanceUpdate(BaseModel):
    allocated_days: Decimal | None = Field(default=None, gt=0, max_digits=7, decimal_places=2)
    custom_data: dict[str, Any] | None = None


class AdminLeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    leave_type: str
    year: int
    allocated_days: Decimal
    used_days: Decimal
    reserved_days: Decimal
    remaining_days: Decimal
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 7. Company Holidays
# =============================================================================

class AdminHolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=255)
    is_paid: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminHolidayUpdate(BaseModel):
    holiday_date: date | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_paid: bool | None = None
    custom_data: dict[str, Any] | None = None


class AdminHolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    holiday_date: date
    name: str
    is_paid: bool
    custom_data: dict[str, Any]


# =============================================================================
# 8. Staffing Rules
# =============================================================================

class AdminStaffingRuleCreate(BaseModel):
    department_id: UUID
    minimum_active_employees: int = Field(ge=0)
    effective_from: date
    effective_to: date | None = None
    is_active: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("effective_to")
    @classmethod
    def effective_to_after_from(cls, value: date | None, info) -> date | None:
        start = info.data.get("effective_from")
        if start is not None and value is not None and value < start:
            raise ValueError("effective_to must be >= effective_from")
        return value


class AdminStaffingRuleUpdate(BaseModel):
    minimum_active_employees: int | None = Field(default=None, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None


class AdminStaffingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID
    minimum_active_employees: int
    effective_from: date
    effective_to: date | None
    is_active: bool
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 9. Supplier Directory
# =============================================================================

class AdminSupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)


class AdminSupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None


class AdminSupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_person: str | None
    email: str | None
    phone: str | None
    address: str | None
    website: str | None
    is_active: bool
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 10. Policy Readiness
# =============================================================================

class AdminPolicyReadinessResponse(BaseModel):
    total_documents: int
    ingested_active_policies: int
    department_coverage: dict[str, bool]
    ready: bool


# =============================================================================
# 11. Onboarding Status
# =============================================================================

class AdminOnboardingStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    is_active: bool
    onboarding_complete: bool
    last_import_job: UUID | None = None
    last_import_at: datetime | None = None
