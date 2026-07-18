import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from groq import APITimeoutError

from app.core.config import Settings
from app.llm.exceptions import (
    RouterConfigurationError,
    RouterOutputError,
    RouterProviderError,
)
from app.llm.groq import GroqRouterClient


def settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "app_env": "test",
        "debug": False,
        "database_url": "postgresql+asyncpg://test:test@localhost/test",
        "alembic_database_url": "postgresql+asyncpg://test:test@localhost/test",
        "jwt_secret_key": "test-only-secret-key-that-is-at-least-32-bytes",
        "groq_api_key": "test-groq-secret-value",
        "groq_model_router": "router-test-model",
        "llm_max_retries": 2,
        "llm_request_timeout_seconds": 7,
    }
    values.update(overrides)
    return Settings(**values)


def response(payload) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def platform_payload() -> dict:
    return {
        "message_category": "platform_question",
        "owner_department": None,
        "confidence": "high",
        "needs_clarification": False,
        "clarification_question": None,
        "platform_answer": "Use the request page to submit work.",
        "request_type": None,
        "short_summary": None,
        "routing_reason": "This is a platform-use question.",
        "unsupported_reason": None,
        "is_capability_gap": False,
    }


def fake_sdk(*side_effects):
    create = AsyncMock(side_effect=list(side_effects))
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )


def test_client_uses_router_model_and_json_mode() -> None:
    sdk = fake_sdk(response(platform_payload()))
    client = GroqRouterClient(settings(), client=sdk)

    result = asyncio.run(client.classify("How do I submit a request?"))

    assert result.platform_answer is not None
    assert sdk.chat.completions.create.await_args.kwargs["model"] == "router-test-model"
    assert sdk.chat.completions.create.await_args.kwargs["response_format"] == {
        "type": "json_object"
    }


def test_api_key_is_secret_and_missing_key_fails_lazily() -> None:
    configured = settings()
    assert "test-groq-secret-value" not in repr(configured)

    with pytest.raises(RouterConfigurationError):
        GroqRouterClient(settings(groq_api_key=""), client=fake_sdk())


def test_official_sdk_receives_configured_key_without_logging_it(monkeypatch) -> None:
    sdk_factory = Mock(return_value=fake_sdk())
    monkeypatch.setattr("app.llm.groq.AsyncGroq", sdk_factory)
    configured = settings()

    GroqRouterClient(configured)

    assert sdk_factory.call_count == 1
    assert sdk_factory.call_args.kwargs["api_key"] == (
        configured.groq_api_key.get_secret_value()
    )


def test_malformed_output_receives_one_corrective_retry() -> None:
    sdk = fake_sdk(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
        ),
        response(platform_payload()),
    )
    client = GroqRouterClient(settings(), client=sdk)

    result = asyncio.run(client.classify("How do I use this?"))

    assert result.platform_answer is not None
    assert sdk.chat.completions.create.await_count == 2


def test_repeated_malformed_output_is_sanitized() -> None:
    invalid = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="secret raw output"))]
    )
    sdk = fake_sdk(invalid, invalid)
    client = GroqRouterClient(settings(), client=sdk)

    with pytest.raises(RouterOutputError, match="invalid structured response") as exc:
        asyncio.run(client.classify("sensitive user content"))

    assert "secret raw output" not in str(exc.value)


def test_timeout_retries_only_to_configured_limit() -> None:
    timeout = APITimeoutError(httpx.Request("POST", "https://provider.invalid"))
    sdk = fake_sdk(timeout, timeout, timeout)
    client = GroqRouterClient(settings(llm_max_retries=2), client=sdk, sleep=AsyncMock())

    with pytest.raises(RouterProviderError, match="temporarily unavailable"):
        asyncio.run(client.classify("message"))

    assert sdk.chat.completions.create.await_count == 3


def test_logs_exclude_api_key_prompt_and_raw_output(caplog) -> None:
    sdk = fake_sdk(response(platform_payload()))
    client = GroqRouterClient(settings(), client=sdk)
    caplog.set_level(logging.INFO)

    asyncio.run(client.classify("private employee message"))

    logged = caplog.text
    assert "test-groq-secret-value" not in logged
    assert "private employee message" not in logged
    assert "Use the request page" not in logged
