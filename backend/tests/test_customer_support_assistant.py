import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.assistant.schemas import AssistantMessageRequest
from app.assistant.service import AssistantService
from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.workflow.router_output import RouterOutput
from app.core.config import Settings
from tests.test_customer_support_contracts import grounded_result
from app.departments.customer_support.service import CustomerSupportService


def test_grounded_department_question_does_not_create_request() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        debug=False,
    )
    current = AuthenticatedUser(uuid4(), uuid4(), "u@example.com", ActorType.EXTERNAL_USER)
    router = AsyncMock()
    router.classify.return_value = RouterOutput.model_validate({
        "message_category": "department_question", "owner_department": "customer_support",
        "confidence": "high", "needs_clarification": False, "request_type": "support_hours",
        "short_summary": "Support hours", "routing_reason": "Customer Support question.",
        "is_capability_gap": False,
    })
    support = AsyncMock(spec=CustomerSupportService)
    result = grounded_result()
    from app.departments.customer_support.service import CustomerSupportService as Service
    support.execute.return_value = Service._to_department_result(result)
    request_service = AsyncMock()
    workflow = SimpleNamespace(
        department_execution_service=SimpleNamespace(customer_support_service=support)
    )
    service = AssistantService(AsyncMock(), current, settings, router_client=router,
        request_service=request_service, workflow_service=workflow)
    response = asyncio.run(service.handle(AssistantMessageRequest(message="What are support hours?")))
    assert response.request_id is None
    assert "Sources: Support FAQ" in response.response
    request_service.create.assert_not_awaited()
