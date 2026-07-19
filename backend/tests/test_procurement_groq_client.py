import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.departments.procurement.enums import ProcurementModelRole
from app.departments.procurement.schemas import ProcurementExecutionInput
from app.llm.exceptions import ProcurementConfigurationError, ProcurementOutputError
from app.llm.groq import GroqProcurementClient


def settings() -> Settings:
    return Settings(
        _env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        groq_api_key="test-only-placeholder", groq_model_fast="fast-fixed",
        groq_model_reasoning="reasoning-fixed", llm_max_retries=1,
    )


def payload() -> ProcurementExecutionInput:
    return ProcurementExecutionInput(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", owner_department_type="procurement",
        active_department_type="procurement", request_type="supplier_evaluation",
        original_summary="Compare suppliers", current_stage="procurement_analysis",
        requester_is_manager=False,
    )


def test_arbitrary_procurement_model_role_is_rejected() -> None:
    provider = AsyncMock()
    client = GroqProcurementClient(settings(), client=provider)
    with pytest.raises(ProcurementConfigurationError, match="Unsupported"):
        asyncio.run(client.generate(payload(), role="arbitrary-model"))
    provider.chat.completions.create.assert_not_awaited()


def test_malformed_output_has_only_one_bounded_correction() -> None:
    provider = AsyncMock()
    provider.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
    )
    client = GroqProcurementClient(settings(), client=provider)
    with pytest.raises(ProcurementOutputError, match="invalid structured"):
        asyncio.run(client.generate(payload(), role=ProcurementModelRole.FAST))
    assert provider.chat.completions.create.await_count == 2
