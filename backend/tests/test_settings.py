import pytest

from app.core.config import ConfigurationError, Settings, load_settings


POOLED_URL = "postgresql+asyncpg://user:fake-password@pooled.example/test?ssl=require"
DIRECT_URL = "postgresql+asyncpg://user:fake-password@direct.example/test?ssl=require"


def configure_required_database_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", POOLED_URL)
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", DIRECT_URL)
    monkeypatch.setenv("DEBUG", "false")


def test_settings_parse_typed_environment_values(monkeypatch) -> None:
    configure_required_database_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("BACKEND_PORT", "9000")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,https://example.com")
    monkeypatch.setenv("DATABASE_POOL_SIZE", "7")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "12")
    monkeypatch.setenv("DATABASE_POOL_TIMEOUT", "45")
    monkeypatch.setenv("DATABASE_ECHO", "true")
    monkeypatch.setenv("ALLOWED_UPLOAD_EXTENSIONS", '["pdf", "csv"]')

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.debug is False
    assert settings.backend_port == 9000
    assert [str(origin) for origin in settings.cors_origins] == [
        "http://localhost:5173/",
        "https://example.com/",
    ]
    assert settings.database_pool_size == 7
    assert settings.database_max_overflow == 12
    assert settings.database_pool_timeout == 45
    assert settings.database_echo is True
    assert settings.allowed_upload_extensions == ["pdf", "csv"]


def test_database_urls_are_redacted_from_settings_representation(monkeypatch) -> None:
    configure_required_database_environment(monkeypatch)

    settings = Settings(_env_file=None)
    representation = repr(settings)

    assert "fake-password" not in representation
    assert "database_url" not in representation
    assert "alembic_database_url" not in representation


def test_missing_database_configuration_has_sanitized_error(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=None)

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "ALEMBIC_DATABASE_URL" in message
    assert "password" not in message.lower()


def test_database_urls_require_asyncpg_driver(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:should-not-appear@pooled.example/test",
    )
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", DIRECT_URL)

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=None)

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "should-not-appear" not in message
