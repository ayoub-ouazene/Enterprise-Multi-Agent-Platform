from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DepartmentType


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    department_type: DepartmentType
    is_active: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    department_type: DepartmentType | None = None
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None


class DepartmentInternalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    department_type: DepartmentType
    is_active: bool
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    department_type: DepartmentType
    is_active: bool
    created_at: datetime
    updated_at: datetime
