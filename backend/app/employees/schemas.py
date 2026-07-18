from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EmploymentStatus


class EmployeeCreate(BaseModel):
    user_id: UUID | None = None
    department_id: UUID | None = None
    employee_code: str = Field(min_length=1, max_length=100)
    job_title: str | None = Field(default=None, max_length=160)
    manager_employee_id: UUID | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    custom_data: dict[str, Any] = Field(default_factory=dict)


class EmployeeUpdate(BaseModel):
    user_id: UUID | None = None
    department_id: UUID | None = None
    employee_code: str | None = Field(default=None, min_length=1, max_length=100)
    job_title: str | None = Field(default=None, max_length=160)
    manager_employee_id: UUID | None = None
    employment_status: EmploymentStatus | None = None
    custom_data: dict[str, Any] | None = None


class EmployeeInternalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID | None
    department_id: UUID | None
    employee_code: str
    job_title: str | None
    manager_employee_id: UUID | None
    employment_status: EmploymentStatus
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    department_id: UUID | None
    employee_code: str
    job_title: str | None
    manager_employee_id: UUID | None
    employment_status: EmploymentStatus
    created_at: datetime
    updated_at: datetime
