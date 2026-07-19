import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.departments.hr.enums import HRModelRole
from app.departments.hr.schemas import HRExecutionInput
from app.llm.exceptions import HRConfigurationError, HROutputError
from app.llm.groq import GroqHRClient


def settings() -> Settings:
    return Settings(_env_file=None, debug=False,
        database_url="postgresql+asyncpg://test_user@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://test_user@direct.example/db",
        groq_api_key="test-placeholder", groq_model_fast="fast-fixed",
        groq_model_reasoning="reasoning-fixed", llm_max_retries=1)


def payload() -> HRExecutionInput:
    return HRExecutionInput(request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", requester_is_manager=False, owner_department_type="hr",
        active_department_type="hr", request_type="hr_information", original_summary="Policy?", current_stage="hr")


def test_arbitrary_hr_model_is_rejected() -> None:
    provider = AsyncMock()
    client = GroqHRClient(settings(), client=provider)
    with pytest.raises(HRConfigurationError):
        asyncio.run(client.generate(payload(), role="arbitrary"))
    provider.chat.completions.create.assert_not_awaited()


def test_malformed_hr_output_has_bounded_correction() -> None:
    provider = AsyncMock()
    provider.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="bad"))])
    with pytest.raises(HROutputError):
        asyncio.run(GroqHRClient(settings(), client=provider).generate(payload(), role=HRModelRole.FAST))
    assert provider.chat.completions.create.await_count == 2
