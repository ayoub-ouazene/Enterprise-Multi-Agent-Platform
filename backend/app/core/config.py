import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIRECTORY / ".env"
ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(RuntimeError):
    """Raised with a sanitized message when application configuration is invalid."""


StringList = Annotated[list[str], NoDecode]
UrlList = Annotated[list[AnyHttpUrl], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Enterprise Multi-Agent Platform"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    frontend_url: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    cors_origins: UrlList = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:5173")]
    )

    # Database
    database_url: SecretStr = Field(repr=False)
    alembic_database_url: SecretStr = Field(repr=False)
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout: int = Field(default=30, gt=0)
    database_echo: bool = False

    # Authentication placeholders
    jwt_secret_key: SecretStr | None = Field(default=None, repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)

    # Groq placeholders
    groq_api_key: SecretStr | None = Field(default=None, repr=False)
    groq_base_url: AnyHttpUrl = AnyHttpUrl("https://api.groq.com/openai/v1")
    groq_model_router: str = "llama-3.1-8b-instant"
    groq_model_fast: str = "openai/gpt-oss-20b"
    groq_model_reasoning: str = "openai/gpt-oss-120b"
    groq_model_reviewer: str = "llama-3.3-70b-versatile"
    llm_temperature: float = Field(default=0.1, ge=0)
    llm_max_retries: int = Field(default=3, ge=0)
    llm_request_timeout_seconds: int = Field(default=60, gt=0)

    # Pinecone placeholders
    pinecone_api_key: SecretStr | None = Field(default=None, repr=False)
    pinecone_index_name: str = "enterprise-knowledge"
    pinecone_index_host: AnyHttpUrl | None = None
    pinecone_embedding_model: str = "multilingual-e5-large"
    pinecone_namespace_prefix: str = "company"
    rag_top_k: int = Field(default=8, gt=0)
    rag_chunk_size: int = Field(default=400, gt=0)
    rag_chunk_overlap: int = Field(default=60, ge=0)

    # File and workflow placeholders
    upload_directory: Path = Path("uploads")
    max_upload_size_mb: int = Field(default=25, gt=0)
    allowed_upload_extensions: StringList = Field(
        default_factory=lambda: ["pdf", "docx", "txt", "csv", "xlsx"]
    )
    router_max_clarification_questions: int = Field(default=3, ge=0, le=3)
    workflow_max_tool_retries: int = Field(default=2, ge=0)
    workflow_review_max_revisions: int = Field(default=1, ge=0, le=1)
    workflow_max_collaboration_depth: int = Field(default=3, ge=1, le=3)
    workflow_max_collaboration_calls: int = Field(default=6, ge=1, le=6)
    workflow_max_collaboration_attempts: int = Field(default=2, ge=1, le=2)
    sse_heartbeat_seconds: int = Field(default=15, gt=0)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Project configuration is intentionally centralized in backend/.env.
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    @field_validator("cors_origins", "allowed_upload_extensions", mode="before")
    @classmethod
    def parse_list_value(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return []

        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "must be a comma-separated list or JSON array"
                ) from exc
            if not isinstance(parsed, list):
                raise ValueError("must be a comma-separated list or JSON array")
            return parsed

        return [item.strip() for item in stripped.split(",") if item.strip()]

    @field_validator("pinecone_index_host", mode="before")
    @classmethod
    def empty_url_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("pinecone_namespace_prefix")
    @classmethod
    def validate_namespace_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        algorithm = value.strip().upper()
        if algorithm not in ALLOWED_JWT_ALGORITHMS:
            allowed = ", ".join(sorted(ALLOWED_JWT_ALGORITHMS))
            raise ValueError(f"must be one of: {allowed}")
        return algorithm

    @field_validator("database_url", "alembic_database_url", mode="before")
    @classmethod
    def validate_asyncpg_url(cls, value: object) -> SecretStr:
        raw_value = (
            value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        )
        if not raw_value.strip():
            raise ValueError("must be configured")

        try:
            url = make_url(raw_value)
        except (ArgumentError, ValueError) as exc:
            raise ValueError("must be a valid PostgreSQL asyncpg URL") from exc

        if url.drivername != "postgresql+asyncpg":
            raise ValueError("must use the postgresql+asyncpg driver")
        if not url.host or not url.database:
            raise ValueError("must include a database host and database name")

        return SecretStr(raw_value)

    @model_validator(mode="after")
    def validate_rag_chunking(self) -> "Settings":
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        return self


def load_settings(env_file: Path | str | None = ENV_FILE) -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        invalid_fields = sorted(
            {
                str(error["loc"][0]).upper()
                for error in exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
                if error["loc"]
            }
        )
        fields = ", ".join(invalid_fields) or "UNKNOWN"
        raise ConfigurationError(
            f"Missing or invalid required configuration: {fields}"
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def validate_auth_configuration(settings: Settings) -> None:
    """Fail safely when authentication cannot sign tokens securely."""
    if settings.jwt_secret_key is None:
        raise ConfigurationError("JWT_SECRET_KEY must be configured")

    secret = settings.jwt_secret_key.get_secret_value()
    if len(secret.encode("utf-8")) < 32:
        raise ConfigurationError("JWT_SECRET_KEY must contain at least 32 bytes")


def validate_router_configuration(settings: Settings) -> None:
    """Validate Groq Router settings only when Router functionality is invoked."""

    if (
        settings.groq_api_key is None
        or not settings.groq_api_key.get_secret_value().strip()
    ):
        raise ConfigurationError("GROQ_API_KEY must be configured for Router functionality")
    if not settings.groq_model_router.strip():
        raise ConfigurationError(
            "GROQ_MODEL_ROUTER must be configured for Router functionality"
        )


def validate_customer_support_configuration(settings: Settings) -> None:
    """Validate Customer Support model roles without exposing configuration values."""
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value().strip():
        raise ConfigurationError("GROQ_API_KEY must be configured for Customer Support")
    if not settings.groq_model_fast.strip() or not settings.groq_model_reasoning.strip():
        raise ConfigurationError("Fast and Reasoning Groq models must be configured for Customer Support")


def validate_it_configuration(settings: Settings) -> None:
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value().strip():
        raise ConfigurationError("GROQ_API_KEY must be configured for IT")
    if not settings.groq_model_fast.strip() or not settings.groq_model_reasoning.strip():
        raise ConfigurationError("Fast and Reasoning Groq models must be configured for IT")


def validate_pinecone_configuration(settings: Settings) -> None:
    """Validate Pinecone only when knowledge functionality is invoked."""
    if (
        settings.pinecone_api_key is None
        or not settings.pinecone_api_key.get_secret_value().strip()
    ):
        raise ConfigurationError(
            "PINECONE_API_KEY must be configured for knowledge functionality"
        )
    if settings.pinecone_index_host is None:
        raise ConfigurationError(
            "PINECONE_INDEX_HOST must be configured for knowledge functionality"
        )
    if not settings.pinecone_index_name.strip():
        raise ConfigurationError(
            "PINECONE_INDEX_NAME must be configured for knowledge functionality"
        )
    if not settings.pinecone_embedding_model.strip():
        raise ConfigurationError(
            "PINECONE_EMBEDDING_MODEL must be configured for knowledge functionality"
        )
