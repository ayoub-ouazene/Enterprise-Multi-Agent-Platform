from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.auth.context import AuthenticatedUser
from app.auth.tokens import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.core.config import ConfigurationError, Settings, validate_auth_configuration
from app.core.enums import ActorType


def build_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "debug": False,
        "database_url": "postgresql+asyncpg://test:test@localhost/test",
        "alembic_database_url": "postgresql+asyncpg://test:test@localhost/test",
        "jwt_secret_key": "test-only-secret-key-that-is-at-least-32-bytes",
        **overrides,
    }
    return Settings(**values)


def build_context() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="manager@example.com",
        actor_type=ActorType.DEPARTMENT_MANAGER,
        employee_id=uuid4(),
        department_id=uuid4(),
        is_manager=True,
    )


def test_access_token_creation_and_verification() -> None:
    context = build_context()
    claims = decode_access_token(
        create_access_token(context, build_settings()).value,
        build_settings(),
    )

    assert claims.sub == context.user_id
    assert claims.company_id == context.company_id
    assert claims.actor_type == ActorType.DEPARTMENT_MANAGER
    assert claims.employee_id == context.employee_id
    assert claims.department_id == context.department_id
    assert claims.is_manager is True


def test_expired_access_token_is_rejected() -> None:
    settings = build_settings()
    expired = create_access_token(
        build_context(),
        settings,
        now=datetime.now(UTC) - timedelta(days=1),
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(expired.value, settings)


def test_tampered_access_token_is_rejected() -> None:
    settings = build_settings()
    token = create_access_token(build_context(), settings).value
    prefix, payload, signature = token.split(".")
    replacement = "A" if payload[-1] != "A" else "B"
    tampered = ".".join((prefix, payload[:-1] + replacement, signature))

    with pytest.raises(TokenValidationError):
        decode_access_token(tampered, settings)


def test_access_token_is_rejected_as_refresh_token() -> None:
    settings = build_settings()
    access = create_access_token(build_context(), settings)

    with pytest.raises(TokenValidationError, match="Expected a refresh token"):
        decode_refresh_token(access.value, settings)


def test_refresh_token_is_distinguishable_and_verifiable() -> None:
    settings = build_settings()
    context = build_context()
    refresh = create_refresh_token(context, settings)

    claims = decode_refresh_token(refresh.value, settings)

    assert claims.token_type == "refresh"
    assert claims.sub == context.user_id
    assert claims.company_id == context.company_id


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_missing_or_weak_jwt_secret_fails_auth_configuration(secret) -> None:
    settings = build_settings(jwt_secret_key=secret)

    with pytest.raises(ConfigurationError):
        validate_auth_configuration(settings)
