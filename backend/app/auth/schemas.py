from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.auth.passwords import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH


class LoginRequest(BaseModel):
    company_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: SecretStr

    @field_validator("company_slug")
    @classmethod
    def normalize_company_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Company slug must not be empty")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: SecretStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: SecretStr
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def validate_new_password_length(cls, value: SecretStr) -> SecretStr:
        pw = value.get_secret_value()
        if len(pw) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters")
        if len(pw) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must contain at most {MAX_PASSWORD_LENGTH} characters")
        return value


class ChangePasswordResponse(BaseModel):
    success: bool = True
    message: str = "Password changed successfully"


class AuthenticatedUserResponse(BaseModel):
    user_id: UUID
    company_id: UUID
    email: EmailStr
    actor_type: ActorType
    employee_id: UUID | None
    department_id: UUID | None
    is_manager: bool
    permissions: tuple[str, ...]
    company_active: bool
    onboarding_complete: bool
    must_change_password: bool

    @classmethod
    def from_context(cls, context: AuthenticatedUser) -> "AuthenticatedUserResponse":
        return cls(
            user_id=context.user_id,
            company_id=context.company_id,
            email=context.email,
            actor_type=context.actor_type,
            employee_id=context.employee_id,
            department_id=context.department_id,
            is_manager=context.is_manager,
            permissions=context.permissions,
            company_active=context.company_active,
            onboarding_complete=context.onboarding_complete,
            must_change_password=context.must_change_password,
        )
