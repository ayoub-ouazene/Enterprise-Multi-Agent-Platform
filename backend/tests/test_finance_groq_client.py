import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.departments.finance.enums import FinanceModelRole
from app.departments.finance.schemas import FinanceExecutionInput
from app.llm.exceptions import FinanceConfigurationError, FinanceOutputError
from app.llm.groq import GroqFinanceClient


def settings() -> Settings:
    return Settings(
        _env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        groq_api_key="test-only-placeholder", groq_model_fast="fast-fixed",
        groq_model_reasoning="reasoning-fixed", llm_max_retries=1,
    )


def payload() -> FinanceExecutionInput:
    return FinanceExecutionInput(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", owner_department_type="finance",
        active_department_type="finance", request_type="budget_inquiry",
        original_summary="Budget status?", current_stage="finance_analysis",
    )


def test_arbitrary_finance_model_role_is_rejected_before_provider_call() -> None:
    provider = AsyncMock()
    client = GroqFinanceClient(settings(), client=provider)
    with pytest.raises(FinanceConfigurationError, match="Unsupported"):
        asyncio.run(client.generate(payload(), role="arbitrary-model"))
    provider.chat.completions.create.assert_not_awaited()


def test_malformed_output_is_rejected_after_bounded_correction() -> None:
    provider = AsyncMock()
    provider.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
    )
    client = GroqFinanceClient(settings(), client=provider)
    with pytest.raises(FinanceOutputError, match="invalid structured"):
        asyncio.run(client.generate(payload(), role=FinanceModelRole.FAST))
    assert provider.chat.completions.create.await_count == 2
