import asyncio
from unittest.mock import AsyncMock
import pytest
from types import SimpleNamespace
from app.core.config import Settings
from app.departments.it.enums import ITModelRole
from app.departments.it.schemas import ITExecutionInput
from uuid import uuid4
from app.llm.exceptions import ITConfigurationError, ITOutputError
from app.llm.groq import GroqITClient


def settings():
    return Settings(_env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        groq_api_key="test-only", groq_model_fast="fast-fixed", groq_model_reasoning="reasoning-fixed")


def test_arbitrary_it_model_role_is_rejected_before_provider_call() -> None:
    provider = AsyncMock()
    client = GroqITClient(settings(), client=provider)
    with pytest.raises(ITConfigurationError):
        asyncio.run(client.generate(object(), role="arbitrary-model"))
    provider.chat.completions.create.assert_not_awaited()


def test_malformed_it_output_is_rejected_after_bounded_correction() -> None:
    provider = AsyncMock()
    provider.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content="not-json"))])
    configured = settings().model_copy(update={"llm_max_retries": 1})
    client = GroqITClient(configured, client=provider)
    with pytest.raises(ITOutputError, match="invalid structured"):
        payload = ITExecutionInput(request_id=uuid4(), company_id=uuid4(),
            requester_user_id=uuid4(), requester_actor_type="employee", request_type="incident",
            original_summary="Network issue", current_stage="it_analysis")
        asyncio.run(client.generate(payload, role=ITModelRole.FAST))
    assert provider.chat.completions.create.await_count == 2
