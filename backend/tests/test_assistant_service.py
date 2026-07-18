import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.assistant.schemas import AssistantMessageRequest
from app.assistant.service import AssistantService
from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.requests.enums import RequestStatus
from app.workflow.router_output import RouterOutput
from app.workflow.schemas import WorkflowControlResponse


def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
        groq_api_key="test-only-groq-key",
    )


def user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="employee@example.com",
        actor_type=ActorType.EMPLOYEE,
        employee_id=uuid4(),
    )


def router_output(category="business_request", department=DepartmentType.IT):
    if category == "platform_question":
        return RouterOutput(
            message_category=category,
            owner_department=None,
            confidence="high",
            needs_clarification=False,
            clarification_question=None,
            platform_answer="Open Requests to submit or track work.",
            request_type=None,
            short_summary=None,
            routing_reason="This is a platform-use question.",
            unsupported_reason=None,
            is_capability_gap=False,
        )
    if category == "unclear":
        return RouterOutput(
            message_category=category,
            owner_department=None,
            confidence="low",
            needs_clarification=True,
            clarification_question="Is this an employee or customer account?",
            platform_answer=None,
            request_type=None,
            short_summary=None,
            routing_reason="Account context is ambiguous.",
            unsupported_reason=None,
            is_capability_gap=False,
        )
    return RouterOutput(
        message_category=category,
        owner_department=department,
        confidence="high",
        needs_clarification=False,
        clarification_question=None,
        platform_answer=None,
        request_type="hardware_request",
        short_summary="Employee requests a laptop.",
        routing_reason="Hardware belongs to IT.",
        unsupported_reason=None,
        is_capability_gap=False,
    )


def control(request_id, *, clarification=False) -> WorkflowControlResponse:
    return WorkflowControlResponse(
        request_id=request_id,
        status=RequestStatus.ROUTING if clarification else RequestStatus.COMPLETED,
        current_stage=(
            "awaiting_router_clarification" if clarification else "completed"
        ),
        owner_department_id=None if clarification else uuid4(),
        active_department_id=None if clarification else uuid4(),
        state_version=1,
        message_category="unclear" if clarification else "business_request",
        owner_department=None if clarification else "it",
        needs_clarification=clarification,
        clarification_question=(
            "Is this an employee or customer account?" if clarification else None
        ),
        response=(
            "Is this an employee or customer account?"
            if clarification
            else "The placeholder department completed the request."
        ),
    )


def service_for(output: RouterOutput):
    router_client = Mock()
    router_client.classify = AsyncMock(return_value=output)
    request_service = Mock()
    created = SimpleNamespace(id=uuid4())
    request_service.create = AsyncMock(return_value=created)
    workflow_service = Mock()
    workflow_service.start_for_submission = AsyncMock(
        return_value=control(created.id, clarification=output.needs_clarification)
    )
    workflow_service.resume_for_requester = AsyncMock(return_value=control(created.id))
    service = AssistantService(
        AsyncMock(),
        user(),
        settings(),
        router_client=router_client,
        request_service=request_service,
        workflow_service=workflow_service,
    )
    return service, router_client, request_service, workflow_service, created


def test_platform_question_is_direct_and_creates_no_request() -> None:
    service, _, requests, workflows, _ = service_for(
        router_output("platform_question", None)
    )

    result = asyncio.run(
        service.handle(AssistantMessageRequest(message="How do I track a request?"))
    )

    assert result.response == "Open Requests to submit or track work."
    assert result.request_id is None
    assert result.owner_department is None
    requests.create.assert_not_awaited()
    workflows.start_for_submission.assert_not_awaited()


@pytest.mark.parametrize("category", ["department_question", "business_request"])
def test_department_and_business_messages_create_workflow_request(category) -> None:
    service, _, requests, workflows, created = service_for(router_output(category))

    result = asyncio.run(service.handle(AssistantMessageRequest(message="I need help")))

    assert result.request_id == created.id
    requests.create.assert_awaited_once()
    workflows.start_for_submission.assert_awaited_once_with(
        created.id,
        preclassified_output=router_output(category),
    )


def test_clarification_creates_paused_request() -> None:
    service, _, requests, workflows, created = service_for(router_output("unclear", None))

    result = asyncio.run(service.handle(AssistantMessageRequest(message="Account help")))

    assert result.request_id == created.id
    assert result.needs_clarification is True
    requests.create.assert_awaited_once()
    workflows.start_for_submission.assert_awaited_once()


def test_clarification_answer_resumes_same_request_without_reclassification() -> None:
    service, router_client, requests, workflows, created = service_for(
        router_output("unclear", None)
    )

    result = asyncio.run(
        service.handle(
            AssistantMessageRequest(
                message="It is my employee account.",
                request_id=created.id,
            )
        )
    )

    assert result.request_id == created.id
    workflows.resume_for_requester.assert_awaited_once_with(
        created.id,
        clarification_answer="It is my employee account.",
    )
    router_client.classify.assert_not_awaited()
    requests.create.assert_not_awaited()
