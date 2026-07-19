import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType
from app.departments.repository import DepartmentRepository
from app.rag.enums import KnowledgeDepartmentScope
from app.rag.exceptions import KnowledgePermissionError, KnowledgeProviderError
from app.rag.namespace import build_company_namespace
from app.rag.permissions import (
    COMPANY_ACCESS_SCOPES,
    MANAGER_ACCESS_SCOPES,
    trusted_manager_department,
)
from app.rag.pinecone import PineconeProvider
from app.rag.repository import KnowledgeDocumentRepository
from app.rag.schemas import (
    KnowledgeChunkResult,
    KnowledgeRetrievalQuery,
    KnowledgeSearchRequest,
)


logger = logging.getLogger(__name__)


class KnowledgeRetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        settings: Settings,
        provider: PineconeProvider,
        *,
        repository: KnowledgeDocumentRepository | None = None,
        department_repository: DepartmentRepository | None = None,
    ) -> None:
        self.current_user = current_user
        self.settings = settings
        self.provider = provider
        self.repository = repository or KnowledgeDocumentRepository(
            session, current_user.company_id
        )
        self.department_repository = department_repository or DepartmentRepository(
            session, current_user.company_id
        )

    async def trusted_query(
        self, request: KnowledgeSearchRequest
    ) -> KnowledgeRetrievalQuery:
        if self.current_user.actor_type == ActorType.COMPANY:
            if request.department is None:
                departments = list(KnowledgeDepartmentScope)
            elif request.department == KnowledgeDepartmentScope.SHARED:
                departments = [KnowledgeDepartmentScope.SHARED]
            else:
                departments = [request.department, KnowledgeDepartmentScope.SHARED]
            scopes = list(COMPANY_ACCESS_SCOPES)
        elif self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            own = await trusted_manager_department(
                self.current_user, self.department_repository
            )
            if request.department not in (None, own, KnowledgeDepartmentScope.SHARED):
                raise KnowledgePermissionError("Managers cannot search another department")
            departments = [own, KnowledgeDepartmentScope.SHARED]
            scopes = list(MANAGER_ACCESS_SCOPES)
        else:
            raise KnowledgePermissionError("Knowledge search access is required")
        top_k = min(request.top_k or self.settings.rag_top_k, self.settings.rag_top_k)
        return KnowledgeRetrievalQuery(
            company_id=self.current_user.company_id,
            query_text=request.query_text,
            departments=departments,
            allowed_access_scopes=scopes,
            document_types=request.document_types,
            top_k=top_k,
            effective_at=request.effective_at,
        )

    def _filter(self, query: KnowledgeRetrievalQuery) -> dict:
        conditions: list[dict] = [
            {"company_id": {"$eq": str(query.company_id)}},
            {"is_active": {"$eq": True}},
            {"departments": {"$in": [item.value for item in query.departments]}},
            {
                "access_scope": {
                    "$in": [item.value for item in query.allowed_access_scopes]
                }
            },
        ]
        if query.document_types:
            conditions.append(
                {"document_type": {"$in": [item.value for item in query.document_types]}}
            )
        effective_at = query.effective_at or date.today()
        timestamp = int(datetime.combine(effective_at, datetime.min.time(), tzinfo=UTC).timestamp())
        conditions.append(
            {
                "$or": [
                    {"effective_date_epoch": {"$exists": False}},
                    {"effective_date_epoch": {"$lte": timestamp}},
                ]
            }
        )
        return {"$and": conditions}

    async def search(self, request: KnowledgeSearchRequest) -> list[KnowledgeChunkResult]:
        query = await self.trusted_query(request)
        return await self.search_trusted(query)

    async def search_trusted(
        self, query: KnowledgeRetrievalQuery
    ) -> list[KnowledgeChunkResult]:
        """Execute a query whose tenant and access filters were derived internally."""
        if query.company_id != self.current_user.company_id:
            raise KnowledgePermissionError("Knowledge tenant scope is invalid")
        namespace = build_company_namespace(
            query.company_id, self.settings.pinecone_namespace_prefix
        )
        hits = await self.provider.search(
            namespace,
            query_text=query.query_text,
            top_k=query.top_k,
            metadata_filter=self._filter(query),
        )
        parsed: list[tuple[dict, UUID]] = []
        malformed = 0
        for hit in hits:
            try:
                if hit.get("company_id") != str(query.company_id):
                    malformed += 1
                    continue
                document_id = UUID(str(hit["document_id"]))
                parsed.append((hit, document_id))
            except (KeyError, TypeError, ValueError):
                malformed += 1
        active = await self.repository.active_by_ids({item[1] for item in parsed})
        results: list[KnowledgeChunkResult] = []
        for hit, document_id in parsed:
            document = active.get(document_id)
            try:
                if document is None or int(hit["version"]) != document.version:
                    continue
                result = KnowledgeChunkResult(
                    record_id=str(hit["_id"]),
                    document_id=document_id,
                    title=str(hit["document_title"]),
                    document_type=hit["document_type"],
                    department_scope=hit["departments"],
                    access_scope=hit["access_scope"],
                    version=int(hit["version"]),
                    chunk_index=int(hit["chunk_index"]),
                    chunk_text=str(hit["chunk_text"]),
                    similarity_score=float(hit["_score"]),
                    source_filename=str(hit["source_filename"]),
                    effective_date=hit.get("effective_date"),
                )
                if result.access_scope not in query.allowed_access_scopes:
                    continue
                if not set(result.department_scope).intersection(query.departments):
                    continue
                results.append(result)
            except (KeyError, TypeError, ValueError):
                malformed += 1
        if malformed:
            logger.warning(
                "Malformed knowledge results ignored company_id=%s count=%s",
                query.company_id,
                malformed,
            )
        return results[: query.top_k]
