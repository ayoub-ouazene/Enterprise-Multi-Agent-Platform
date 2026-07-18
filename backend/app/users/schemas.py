from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.enums import ActorType


class UserCreate(BaseModel):
    email: EmailStr
    actor_type: ActorType
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    actor_type: ActorType | None = None
    is_active: bool | None = None


class UserInternalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: EmailStr
    actor_type: ActorType
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    actor_type: ActorType
    is_active: bool
    created_at: datetime
    updated_at: datetime
