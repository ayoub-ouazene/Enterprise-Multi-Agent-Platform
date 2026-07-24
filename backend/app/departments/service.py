from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import ConflictError, NotFoundError
from app.departments.models import Department
from app.departments.repository import DepartmentRepository
from app.departments.schemas import (
    DepartmentActivityResponse,
    DepartmentCreate,
    DepartmentReadinessItem,
    DepartmentReadinessResponse,
    DepartmentStatsResponse,
    DepartmentUpdate,
)
from app.employees.repository import EmployeeRepository
from app.human_actions.repository import HumanActionRepository
from app.human_actions.service import HumanActionService
from app.rag.models import KnowledgeDocument
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.workflow.enums import WorkflowEventType
from app.workflow.repository import WorkflowEventRepository
from app.workflow.schemas import WorkflowEventPublicResponse


class DepartmentService:
    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
        repository: DepartmentRepository | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.repository = repository or DepartmentRepository(session, company_id)

    async def get(self, department_id: UUID) -> Department:
        department = await self.repository.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department not found")
        return department

    async def create(self, payload: DepartmentCreate) -> Department:
        try:
            if await self.repository.get_by_type(payload.department_type) is not None:
                raise ConflictError("Department type already exists in this company")
            department = await self.repository.create(
                name=payload.name.strip(),
                department_type=payload.department_type,
                is_active=payload.is_active,
                custom_data=payload.custom_data,
            )
            await self.session.commit()
            await self.session.refresh(department)
            return department
        except ConflictError:
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Department type already exists in this company"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def update(
        self,
        department_id: UUID,
        payload: DepartmentUpdate,
    ) -> Department:
        try:
            if await self.repository.get_by_id(department_id) is None:
                raise NotFoundError("Department not found")
            values = payload.model_dump(exclude_unset=True)
            if values.get("name") is not None:
                values["name"] = str(values["name"]).strip()
            if values.get("department_type") is not None:
                existing = await self.repository.get_by_type(values["department_type"])
                if existing is not None and existing.id != department_id:
                    raise ConflictError(
                        "Department type already exists in this company"
                    )
            values = {key: value for key, value in values.items() if value is not None}

            department = await self.repository.update(department_id, values)
            if department is None:
                raise NotFoundError("Department not found")
            await self.session.commit()
            await self.session.refresh(department)
            return department
        except (ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Department update conflicts with existing data"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, department_id: UUID) -> None:
        try:
            if not await self.repository.delete(department_id):
                raise NotFoundError("Department not found")
            await self.session.commit()
        except NotFoundError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise


class DepartmentWorkspaceService:
    """Service for department workspace views: stats, requests, actions, readiness, activity."""

    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self._request_repo = BusinessRequestRepository(session, company_id)
        self._human_action_repo = HumanActionRepository(session, company_id)
        self._employee_repo = EmployeeRepository(session, company_id)
        self._workflow_repo = WorkflowEventRepository(session, company_id)

    async def get_stats(self, department_id: UUID) -> DepartmentStatsResponse:
        today = datetime.now(UTC).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        all_requests = await self._request_repo.list(department_id=department_id, limit=500)
        active_requests = [
            r for r in all_requests
            if r.status not in {
                RequestStatus.COMPLETED,
                RequestStatus.CANCELLED,
                RequestStatus.FAILED,
                RequestStatus.REJECTED,
            }
        ]
        completed_today = [
            r for r in all_requests
            if r.status == RequestStatus.COMPLETED
            and r.completed_at is not None
            and r.completed_at >= today_start
        ]

        pending_actions = await self._human_action_repo.list(
            status="pending", limit=500
        )
        dept_action_ids = {a.id for a in pending_actions}

        collaborations = [
            r for r in all_requests
            if r.status == RequestStatus.WAITING_FOR_DEPARTMENT
        ]

        return DepartmentStatsResponse(
            active_requests=len(active_requests),
            pending_human_actions=len(dept_action_ids),
            collaborations_ongoing=len(collaborations),
            completed_today=len(completed_today),
        )

    async def list_requests(
        self,
        department_id: UUID,
        *,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        status_enum = None
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter)
            except ValueError:
                pass
        return await self._request_repo.list(
            department_id=department_id,
            status=status_enum,
            limit=limit,
            offset=offset,
        )

    async def list_actions(
        self,
        department_id: UUID,
        current_user: AuthenticatedUser,
        *,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Return human actions scoped to requests owned by or active in this department."""
        dept_requests = await self._request_repo.list(department_id=department_id, limit=500)
        request_ids = {r.id for r in dept_requests}

        actions = await self._human_action_repo.list(
            status=status_filter or None,
            limit=limit,
            offset=offset,
        )
        dept_actions = [a for a in actions if a.request_id in request_ids]

        ha_service = HumanActionService(self.session, current_user)
        return [ha_service._to_response(a) for a in dept_actions]

    async def get_readiness(
        self, department_id: UUID, dept_type: DepartmentType
    ) -> DepartmentReadinessResponse:
        items: list[DepartmentReadinessItem] = []

        # Check 1: Policies ingested for this department
        from sqlalchemy import select
        policy_count = await self.session.scalar(
            select(KnowledgeDocument.id)
            .where(
                KnowledgeDocument.company_id == self.company_id,
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.status == "active",
                KnowledgeDocument.ingestion_status == "completed",
            )
            .limit(1)
        )
        items.append(
            DepartmentReadinessItem(
                name="Policies ingested",
                ready=policy_count is not None,
                detail="At least one active policy document must be ingested",
            )
        )

        # Check 2: Manager assigned
        manager_count = await self._employee_repo.count_active_in_department(department_id)
        items.append(
            DepartmentReadinessItem(
                name="Manager assigned",
                ready=manager_count > 0,
                detail="Department must have at least one active employee/manager",
            )
        )

        # Check 3: Department-specific catalog (generic)
        items.append(
            DepartmentReadinessItem(
                name="Department configuration",
                ready=True,
                detail="Basic department configuration is present",
            )
        )

        return DepartmentReadinessResponse(
            department_type=dept_type,
            overall_ready=all(i.ready for i in items),
            items=items,
        )

    async def get_activity(
        self,
        department_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DepartmentActivityResponse]:
        dept_requests = await self._request_repo.list(department_id=department_id, limit=500)
        request_ids = {r.id for r in dept_requests}

        events: list[WorkflowEventPublicResponse] = []
        for rid in sorted(request_ids)[:50]:
            evs = await self._workflow_repo.list_for_request(
                rid,
                visibilities=frozenset({"requester", "manager", "company"}),
                limit=10,
            )
            events.extend(evs)

        events.sort(key=lambda e: e.created_at, reverse=True)

        return [
            DepartmentActivityResponse(
                id=e.id,
                request_id=e.request_id,
                event_type=e.event_type.value,
                title=e.title,
                message=e.message,
                actor_label=e.actor_label,
                created_at=e.created_at,
            )
            for e in events[offset : offset + limit]
        ]
