from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pydantic import BaseModel, ConfigDict, ValidationError

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType


class TokenValidationError(ValueError):
    """Raised when a token is invalid, expired, or has the wrong purpose."""


class AccessTokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: UUID
    company_id: UUID
    actor_type: ActorType
    token_type: str
    jti: str
    iat: datetime
    exp: datetime
    employee_id: UUID | None = None
    department_id: UUID | None = None
    is_manager: bool = False


class RefreshTokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: UUID
    company_id: UUID
    token_type: str
    jti: str
    iat: datetime
    exp: datetime


@dataclass(frozen=True, slots=True)
class EncodedToken:
    value: str
    jti: str
    expires_at: datetime


def _secret(settings: Settings) -> str:
    if settings.jwt_secret_key is None:
        raise RuntimeError("Authentication configuration has not been validated")
    return settings.jwt_secret_key.get_secret_value()


def _encode(payload: dict[str, object], settings: Settings) -> str:
    return jwt.encode(payload, _secret(settings), algorithm=settings.jwt_algorithm)


def create_access_token(
    context: AuthenticatedUser,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> EncodedToken:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    jti = uuid4().hex
    payload: dict[str, object] = {
        "sub": str(context.user_id),
        "company_id": str(context.company_id),
        "actor_type": context.actor_type.value,
        "token_type": "access",
        "jti": jti,
        "iat": issued_at,
        "exp": expires_at,
    }
    if context.employee_id is not None:
        payload["employee_id"] = str(context.employee_id)
    if context.department_id is not None:
        payload["department_id"] = str(context.department_id)
    if context.is_manager:
        payload["is_manager"] = True
    return EncodedToken(_encode(payload, settings), jti, expires_at)


def create_refresh_token(
    context: AuthenticatedUser,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> EncodedToken:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(days=settings.refresh_token_expire_days)
    jti = uuid4().hex
    payload: dict[str, object] = {
        "sub": str(context.user_id),
        "company_id": str(context.company_id),
        "token_type": "refresh",
        "jti": jti,
        "iat": issued_at,
        "exp": expires_at,
    }
    return EncodedToken(_encode(payload, settings), jti, expires_at)


def _decode(token: str, settings: Settings) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            _secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={
                "require": [
                    "sub",
                    "company_id",
                    "token_type",
                    "jti",
                    "iat",
                    "exp",
                ]
            },
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError("Token is invalid or expired") from exc


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    payload = _decode(token, settings)
    if payload.get("token_type") != "access":
        raise TokenValidationError("Expected an access token")
    try:
        claims = AccessTokenClaims.model_validate(payload)
    except ValidationError as exc:
        raise TokenValidationError("Access token claims are invalid") from exc
    return claims


def decode_refresh_token(token: str, settings: Settings) -> RefreshTokenClaims:
    payload = _decode(token, settings)
    if payload.get("token_type") != "refresh":
        raise TokenValidationError("Expected a refresh token")
    try:
        claims = RefreshTokenClaims.model_validate(payload)
    except ValidationError as exc:
        raise TokenValidationError("Refresh token claims are invalid") from exc
    return claims
