import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.customer_support.service import CustomerSupportService
from app.rag.enums import KnowledgeAccessScope, KnowledgeDepartmentScope, KnowledgeDocumentType
from tests.test_customer_support_contracts import grounded_result
from app.core.config import Settings


def test_service_builds_tenant_scoped_query_and_validates_sources() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
        debug=False,
    )
    current = AuthenticatedUser(uuid4(), uuid4(), "u@example.com", ActorType.EXTERNAL_USER)
    session = AsyncMock()
    document_id = uuid4()
    hit = SimpleNamespace(
        document_id=document_id, title="Support FAQ", document_type=KnowledgeDocumentType.FAQ,
        version=1, chunk_index=0, effective_date=None, chunk_text="Hours are 09:00–17:00.",
    )
    retrieval = AsyncMock()
    retrieval.search_trusted.return_value = [hit]
    output = grounded_result(sources=[{"document_id": str(document_id), "title": "Support FAQ",
        "document_type": "faq", "version": 1, "chunk_index": 0}])
    llm = AsyncMock()
    llm.generate.return_value = output
    issues = AsyncMock()
    issues.get.return_value = None
    service = CustomerSupportService(session, current, settings, retrieval,
        llm_client=llm, issue_repository=issues)
    context = DepartmentExecutionContext(
        request_id=uuid4(), company_id=current.company_id, requester_user_id=current.user_id,
        owner_department_type=DepartmentType.CUSTOMER_SUPPORT,
        active_department_type=DepartmentType.CUSTOMER_SUPPORT,
        request_type="faq", request_summary="What are support hours?",
        current_stage="customer_support_analysis",
    )
    result = asyncio.run(service.execute(context))
    query = retrieval.search_trusted.await_args.args[0]
    assert query.company_id == current.company_id
    assert query.departments == [KnowledgeDepartmentScope.CUSTOMER_SUPPORT, KnowledgeDepartmentScope.SHARED]
    assert query.allowed_access_scopes == [KnowledgeAccessScope.ALL_AUTHENTICATED]
    assert result.next_action.value == "complete_request"
    assert llm.generate.await_count == 1
    assert session.rollback.await_count == 2
