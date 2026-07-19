import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import (
    DepartmentConfidence,
    DepartmentExecutionContext,
    DepartmentNextAction,
)
from app.departments.procurement.enums import ProcurementDecision, ProcurementRequestCategory
from app.departments.procurement.schemas import ProcurementDepartmentResult
from app.departments.procurement.service import ProcurementService
from app.rag.enums import KnowledgeDepartmentScope


def settings() -> Settings:
    return Settings(
        _env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        groq_api_key="test-only-placeholder",
    )


def test_procurement_rag_is_limited_to_procurement_and_shared() -> None:
    company_id = uuid4()
    current = AuthenticatedUser(
        user_id=uuid4(), company_id=company_id, email="company@example.com",
        actor_type=ActorType.COMPANY,
    )
    session = AsyncMock()
    retrieval = AsyncMock()
    retrieval.search_trusted.return_value = []
    llm = AsyncMock()
    llm.generate.return_value = ProcurementDepartmentResult(
        category=ProcurementRequestCategory.PROCUREMENT_INFORMATION,
        decision=ProcurementDecision.ANSWER,
        reason="The available policy was explained safely.",
        user_message="Procurement policy answer.",
        confidence=DepartmentConfidence.HIGH,
        requirements_complete=True,
        candidate_count=0,
        eligible_candidate_count=0,
        next_action=DepartmentNextAction.COMPLETE_REQUEST,
        safe_event_title="Procurement answered",
        safe_event_message="The policy question was answered.",
    )
    requests = AsyncMock()
    requests.get.return_value = None
    candidates = AsyncMock()
    service = ProcurementService(
        session, current, settings(), retrieval, llm_client=llm,
        request_repository=requests, candidate_repository=candidates,
    )
    context = DepartmentExecutionContext(
        request_id=uuid4(), company_id=company_id, requester_user_id=current.user_id,
        requester_actor_type=ActorType.COMPANY,
        owner_department_type=DepartmentType.PROCUREMENT,
        active_department_type=DepartmentType.PROCUREMENT,
        request_type="procurement_information", request_summary="What is our procurement policy?",
        current_stage="processing",
    )
    output = asyncio.run(service.execute(context))
    query = retrieval.search_trusted.await_args.args[0]
    assert query.departments == [
        KnowledgeDepartmentScope.PROCUREMENT,
        KnowledgeDepartmentScope.SHARED,
    ]
    assert output.department_type == DepartmentType.PROCUREMENT
    assert output.next_action == DepartmentNextAction.COMPLETE_REQUEST
    candidates.list_for_request.assert_not_awaited()
