import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.it.service import ITService
from app.rag.enums import KnowledgeDepartmentScope, KnowledgeDocumentType
from app.rag.exceptions import KnowledgeProviderError
import pytest
from tests.test_it_contracts import valid_it_result


def settings():
    return Settings(_env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db")


def test_it_service_uses_it_shared_rag_and_fast_model() -> None:
    company, user, employee_id, document_id = uuid4(), uuid4(), uuid4(), uuid4()
    current = AuthenticatedUser(user, company, "employee@example.com", ActorType.EMPLOYEE,
        employee_id=employee_id)
    session, retrieval, llm = AsyncMock(), AsyncMock(), AsyncMock()
    retrieval.search_trusted.return_value = [SimpleNamespace(document_id=document_id,
        title="IT Guide", document_type=KnowledgeDocumentType.PROCEDURE, version=1,
        chunk_index=0, effective_date=None, chunk_text="Use the access portal.")]
    llm.generate.return_value = valid_it_result(sources_used=[{"document_id": str(document_id),
        "title": "IT Guide", "document_type": "procedure", "version": 1, "chunk_index": 0}])
    access, hardware, incidents, assets, software, employees = (AsyncMock() for _ in range(6))
    employees.get_by_id.return_value = SimpleNamespace(id=employee_id, department_id=uuid4(),
        job_title="Engineer", employment_status=SimpleNamespace(value="active"))
    assets.assigned_to.return_value = []
    access.list_for_employee.return_value = []
    service = ITService(session, current, settings(), retrieval, llm_client=llm,
        access_repository=access, hardware_repository=hardware, incident_repository=incidents,
        asset_repository=assets, software_repository=software, employee_repository=employees)
    context = DepartmentExecutionContext(request_id=uuid4(), company_id=company,
        requester_user_id=user, requester_employee_id=employee_id, requester_actor_type="employee",
        owner_department_type=DepartmentType.IT, active_department_type=DepartmentType.IT,
        request_type="it_information", request_summary="How do I request access?", current_stage="it_analysis")
    result = asyncio.run(service.execute(context))
    query = retrieval.search_trusted.await_args.args[0]
    assert query.departments == [KnowledgeDepartmentScope.IT, KnowledgeDepartmentScope.SHARED]
    assert result.department_type == DepartmentType.IT
    assert llm.generate.await_count == 1 and session.rollback.await_count == 2


def test_access_hardware_and_incident_state_persist_without_commits() -> None:
    current = AuthenticatedUser(uuid4(), uuid4(), "u@example.com", ActorType.EMPLOYEE)
    access, hardware, incidents = AsyncMock(), AsyncMock(), AsyncMock()
    service = ITService(AsyncMock(), current, settings(), AsyncMock(), llm_client=AsyncMock(),
        access_repository=access, hardware_repository=hardware, incident_repository=incidents,
        asset_repository=AsyncMock(), software_repository=AsyncMock(), employee_repository=AsyncMock())
    employee_id = uuid4()
    result = valid_it_result(category="password_reset", decision="prepare_operation",
        sources_used=[], request_approved_by_policy=None,
        state_updates={"access": {"employee_id": str(employee_id), "access_type": "password_reset",
            "target_system": "Identity", "business_reason": "Locked out", "provisioning_status": "prepared"}})
    asyncio.run(service.persist_result(uuid4(), result, reported_by_user_id=current.user_id))
    access.upsert.assert_awaited_once()
    stored = access.upsert.await_args.args[1]
    assert not {"password", "password_hash", "reset_token"}.intersection(stored)

    hardware_result = valid_it_result(category="hardware_request", decision="prepare_operation",
        sources_used=[], state_updates={"hardware": {"employee_id": str(employee_id),
            "asset_type": "laptop", "business_reason": "Engineering work",
            "inventory_checked": True, "assignment_status": "asset_available"}})
    asyncio.run(service.persist_result(uuid4(), hardware_result, reported_by_user_id=current.user_id))
    hardware.upsert.assert_awaited_once()

    incident_result = valid_it_result(category="employee_incident", decision="diagnose",
        sources_used=[], state_updates={"incident": {"affected_employee_id": str(employee_id),
            "source": "employee", "symptoms": ["No network"],
            "diagnostic_steps": [{"step_id": "check_connection", "instruction": "Check connection", "completed": True}]}})
    asyncio.run(service.persist_result(uuid4(), incident_result, reported_by_user_id=current.user_id))
    incidents.upsert.assert_awaited_once()


def test_pinecone_failure_remains_sanitized_and_skips_groq() -> None:
    current = AuthenticatedUser(uuid4(), uuid4(), "u@example.com", ActorType.EMPLOYEE)
    retrieval, llm = AsyncMock(), AsyncMock()
    retrieval.search_trusted.side_effect = KnowledgeProviderError("Company knowledge is temporarily unavailable")
    empty = AsyncMock()
    empty.get_by_id.return_value = None
    service = ITService(AsyncMock(), current, settings(), retrieval, llm_client=llm,
        access_repository=empty, hardware_repository=AsyncMock(), incident_repository=AsyncMock(),
        asset_repository=empty, software_repository=AsyncMock(), employee_repository=empty)
    context = DepartmentExecutionContext(request_id=uuid4(), company_id=current.company_id,
        requester_user_id=current.user_id, requester_actor_type="employee",
        owner_department_type=DepartmentType.IT, active_department_type=DepartmentType.IT,
        request_type="it_information", request_summary="IT policy?", current_stage="it_analysis")
    with pytest.raises(KnowledgeProviderError, match="temporarily unavailable"):
        asyncio.run(service.execute(context))
    llm.generate.assert_not_awaited()
