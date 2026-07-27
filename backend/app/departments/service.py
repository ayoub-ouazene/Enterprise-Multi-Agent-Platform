from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
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
    DepartmentOperationalField,
    DepartmentOperationalRecordResponse,
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

    async def get_stats(
        self,
        department_id: UUID,
        *,
        current_user: AuthenticatedUser,
    ) -> DepartmentStatsResponse:
        today = datetime.now(UTC).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        if current_user.actor_type == ActorType.EMPLOYEE:
            all_requests = await self._request_repo.list(
                requester_user_id=current_user.user_id,
                limit=500,
            )
        else:
            all_requests = await self._request_repo.list(
                department_id=department_id,
                limit=500,
            )
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
            department_id=department_id,
            status="pending",
            limit=500,
        )
        if current_user.actor_type == ActorType.EMPLOYEE:
            request_ids = {request.id for request in all_requests}
            pending_actions = [
                action
                for action in pending_actions
                if action.request_id in request_ids
                or action.assigned_user_id == current_user.user_id
            ]

        collaborations = [
            r for r in all_requests
            if r.status == RequestStatus.WAITING_FOR_DEPARTMENT
        ]

        return DepartmentStatsResponse(
            active_requests=len(active_requests),
            pending_human_actions=len(pending_actions),
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
            department_id=department_id,
            status=status_filter or None,
            limit=500,
        )
        dept_actions = [a for a in actions if a.request_id in request_ids]
        if current_user.actor_type == ActorType.EMPLOYEE:
            dept_actions = [
                action
                for action in dept_actions
                if action.request.requester_user_id == current_user.user_id
                or action.assigned_user_id == current_user.user_id
            ]
        dept_actions = dept_actions[offset : offset + limit]

        ha_service = HumanActionService(self.session, current_user)
        return [ha_service._to_response(a) for a in dept_actions]

    async def get_readiness(
        self, department_id: UUID, dept_type: DepartmentType
    ) -> DepartmentReadinessResponse:
        items: list[DepartmentReadinessItem] = []

        # Check 1: Policies ingested for this department
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
        current_user: AuthenticatedUser,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DepartmentActivityResponse]:
        if current_user.actor_type == ActorType.EMPLOYEE:
            dept_requests = await self._request_repo.list(
                requester_user_id=current_user.user_id,
                limit=500,
            )
        else:
            dept_requests = await self._request_repo.list(
                department_id=department_id,
                limit=500,
            )
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

    async def list_operational_records(
        self,
        department_id: UUID,
        department_type: DepartmentType,
        *,
        current_user: AuthenticatedUser,
        kind: str | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        """Return only allowlisted, display-safe department extension fields."""
        visible_request_ids: set[UUID] | None = None
        if current_user.actor_type == ActorType.EMPLOYEE:
            own_requests = await self._request_repo.list(
                requester_user_id=current_user.user_id,
                limit=500,
            )
            visible_request_ids = {request.id for request in own_requests}

        builders = {
            DepartmentType.CUSTOMER_SUPPORT: self._support_records,
            DepartmentType.HR: self._hr_records,
            DepartmentType.IT: self._it_records,
            DepartmentType.FINANCE: self._finance_records,
            DepartmentType.PROCUREMENT: self._procurement_records,
        }
        records = await builders[department_type](
            department_id,
            visible_request_ids=visible_request_ids,
            limit=limit,
        )
        if kind:
            records = [record for record in records if record.record_type == kind]
        records.sort(
            key=lambda record: record.updated_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return records[:limit]

    @staticmethod
    def _value(value) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _field(
        label: str,
        value,
        emphasis: str = "default",
    ) -> DepartmentOperationalField:
        return DepartmentOperationalField(
            label=label,
            value=str(value),
            emphasis=emphasis,
        )

    async def _employee_codes(self) -> dict[UUID, str]:
        return {
            employee.id: employee.employee_code
            for employee in await self._employee_repo.list()
        }

    async def _support_records(
        self,
        _department_id: UUID,
        *,
        visible_request_ids: set[UUID] | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        from app.departments.customer_support.models import SupportIssue

        statement = select(SupportIssue).where(
            SupportIssue.company_id == self.company_id
        )
        if visible_request_ids is not None:
            statement = statement.where(SupportIssue.request_id.in_(visible_request_ids))
        rows = list(
            (
                await self.session.scalars(
                    statement.order_by(SupportIssue.updated_at.desc()).limit(limit)
                )
            ).all()
        )
        return [
            DepartmentOperationalRecordResponse(
                id=row.request_id,
                request_id=row.request_id,
                record_type="support_issue",
                title=row.issue_summary,
                summary=row.resolution_summary or row.customer_impact,
                status=self._value(row.issue_status),
                fields=[
                    self._field("Category", self._value(row.category)),
                    self._field(
                        "Troubleshooting",
                        f"{sum(bool(step.get('completed')) for step in row.troubleshooting_steps)} of {len(row.troubleshooting_steps)} steps completed",
                    ),
                    self._field("IT assistance", "Required" if row.requires_it else "Not required", "warning" if row.requires_it else "default"),
                    self._field("Human escalation", "Required" if row.requires_human_support else "Not required", "critical" if row.requires_human_support else "default"),
                ],
                action_url=f"/app/requests/{row.request_id}",
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def _hr_records(
        self,
        _department_id: UUID,
        *,
        visible_request_ids: set[UUID] | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        from app.departments.hr.models import (
            JobDescription,
            LeaveRequest,
            OnboardingRequest,
        )

        employee_codes = await self._employee_codes()
        records: list[DepartmentOperationalRecordResponse] = []
        leave_statement = select(LeaveRequest).where(
            LeaveRequest.company_id == self.company_id
        )
        onboarding_statement = select(OnboardingRequest).where(
            OnboardingRequest.company_id == self.company_id
        )
        job_statement = select(JobDescription).where(
            JobDescription.company_id == self.company_id
        )
        if visible_request_ids is not None:
            leave_statement = leave_statement.where(
                LeaveRequest.request_id.in_(visible_request_ids)
            )
            onboarding_statement = onboarding_statement.where(
                OnboardingRequest.request_id.in_(visible_request_ids)
            )
            job_statement = job_statement.where(
                JobDescription.request_id.in_(visible_request_ids)
            )
        leaves = (
            await self.session.scalars(
                leave_statement.order_by(LeaveRequest.updated_at.desc()).limit(limit)
            )
        ).all()
        for row in leaves:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="leave_request",
                    title=f"{employee_codes.get(row.employee_id, 'Employee')} · {self._value(row.leave_type)} leave",
                    summary=f"{row.start_date} to {row.end_date}",
                    status=self._value(row.approval_status),
                    fields=[
                        self._field("Workdays", row.requested_days),
                        self._field("Balance", self._value(row.balance_status)),
                        self._field("Staffing", self._value(row.staffing_status), "warning" if self._value(row.staffing_status) != "sufficient" else "positive"),
                        self._field("Reserved days", row.reserved_days),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        onboardings = (
            await self.session.scalars(
                onboarding_statement.order_by(OnboardingRequest.updated_at.desc()).limit(limit)
            )
        ).all()
        for row in onboardings:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="onboarding_case",
                    title=f"Onboarding · {employee_codes.get(row.employee_id, 'Employee')}",
                    summary=f"Starts {row.start_date}",
                    status=self._value(row.onboarding_status),
                    fields=[
                        self._field("Required actions", len(row.required_actions)),
                        self._field("Completed actions", len(row.completed_actions)),
                        self._field("Missing information", len(row.missing_data), "warning" if row.missing_data else "positive"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        jobs = (
            await self.session.scalars(
                job_statement.order_by(JobDescription.updated_at.desc()).limit(limit)
            )
        ).all()
        for row in jobs:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.id,
                    request_id=row.request_id,
                    record_type="job_description",
                    title=row.title,
                    summary=row.summary,
                    status=self._value(row.status),
                    fields=[
                        self._field("Employment type", row.employment_type),
                        self._field("Experience", row.experience_level),
                        self._field("Location", row.work_location or "Not specified"),
                    ],
                    action_url=(
                        f"/app/requests/{row.request_id}" if row.request_id else None
                    ),
                    updated_at=row.updated_at,
                )
            )
        return records

    async def _it_records(
        self,
        _department_id: UUID,
        *,
        visible_request_ids: set[UUID] | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        from app.departments.it.models import AccessRequest, HardwareRequest, ITIncident

        employee_codes = await self._employee_codes()
        records: list[DepartmentOperationalRecordResponse] = []
        models = (ITIncident, AccessRequest, HardwareRequest)
        rows_by_model = {}
        for model in models:
            statement = select(model).where(model.company_id == self.company_id)
            if visible_request_ids is not None:
                statement = statement.where(model.request_id.in_(visible_request_ids))
            rows_by_model[model] = (
                await self.session.scalars(
                    statement.order_by(model.updated_at.desc()).limit(limit)
                )
            ).all()
        for row in rows_by_model[ITIncident]:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="incident",
                    title=row.summary,
                    summary=f"{self._value(row.source).replace('_', ' ').title()} origin",
                    status=self._value(row.incident_status),
                    fields=[
                        self._field("Severity", self._value(row.impact), "critical" if self._value(row.impact) in {"high", "critical"} else "default"),
                        self._field("Diagnosis", f"{len(row.diagnostic_steps)} documented steps"),
                        self._field("Technician", "Required" if row.requires_human_technician else "Not required", "warning" if row.requires_human_technician else "default"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        for row in rows_by_model[AccessRequest]:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="access_request",
                    title=f"{row.target_system} access",
                    summary=employee_codes.get(row.employee_id, "Employee"),
                    status=self._value(row.provisioning_status),
                    fields=[
                        self._field("Access type", self._value(row.access_type)),
                        self._field("Policy", self._value(row.policy_decision)),
                        self._field("Approval", "Required" if row.approval_required else "Not required"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        for row in rows_by_model[HardwareRequest]:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="hardware_request",
                    title=f"{row.asset_type} request",
                    summary=employee_codes.get(row.employee_id, "Employee"),
                    status=self._value(row.assignment_status),
                    fields=[
                        self._field("Inventory", "Checked" if row.inventory_checked else "Pending"),
                        self._field("Finance", "Required" if row.budget_validation_required else "Not required", "warning" if row.budget_validation_required else "default"),
                        self._field("Procurement", "Required" if row.procurement_required else "Not required", "warning" if row.procurement_required else "default"),
                        self._field("Estimated cost", row.estimated_cost or "Not recorded"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        return records

    async def _finance_records(
        self,
        _department_id: UUID,
        *,
        visible_request_ids: set[UUID] | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        from app.departments.finance.models import FinanceRequest, FinancialTransaction

        records: list[DepartmentOperationalRecordResponse] = []
        request_statement = select(FinanceRequest).where(
            FinanceRequest.company_id == self.company_id
        )
        transaction_statement = select(FinancialTransaction).where(
            FinancialTransaction.company_id == self.company_id
        )
        if visible_request_ids is not None:
            request_statement = request_statement.where(
                FinanceRequest.request_id.in_(visible_request_ids)
            )
            transaction_statement = transaction_statement.where(
                FinancialTransaction.request_id.in_(visible_request_ids)
            )
        finance_requests = (
            await self.session.scalars(
                request_statement.order_by(FinanceRequest.updated_at.desc()).limit(limit)
            )
        ).all()
        for row in finance_requests:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="finance_request",
                    title=row.business_reason,
                    summary=self._value(row.category).replace("_", " ").title(),
                    status=self._value(row.decision),
                    fields=[
                        self._field("Requested", f"{row.currency or ''} {row.requested_amount or 'Not recorded'}".strip()),
                        self._field("Available", f"{row.currency or ''} {row.available_budget or 'Not recorded'}".strip()),
                        self._field("Reservation", self._value(row.reservation_status)),
                        self._field("Approval", self._value(row.approval_status), "warning" if row.approval_required else "default"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        transactions = (
            await self.session.scalars(
                transaction_statement.order_by(FinancialTransaction.created_at.desc()).limit(limit)
            )
        ).all()
        for row in transactions:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.id,
                    request_id=row.request_id,
                    record_type="financial_transaction",
                    title=row.description,
                    summary="Confirmed financial record; this does not expose banking details.",
                    status=self._value(row.status),
                    fields=[
                        self._field("Type", self._value(row.transaction_type)),
                        self._field("Amount", f"{row.currency} {row.amount}"),
                        self._field("Reference", row.reference),
                    ],
                    action_url=(
                        f"/app/requests/{row.request_id}" if row.request_id else None
                    ),
                    updated_at=row.confirmed_at or row.created_at,
                )
            )
        return records

    async def _procurement_records(
        self,
        _department_id: UUID,
        *,
        visible_request_ids: set[UUID] | None,
        limit: int,
    ) -> list[DepartmentOperationalRecordResponse]:
        from app.departments.procurement.models import ProcurementRequest, SupplierCandidate

        records: list[DepartmentOperationalRecordResponse] = []
        request_statement = select(ProcurementRequest).where(
            ProcurementRequest.company_id == self.company_id
        )
        candidate_statement = select(SupplierCandidate).where(
            SupplierCandidate.company_id == self.company_id
        )
        if visible_request_ids is not None:
            request_statement = request_statement.where(
                ProcurementRequest.request_id.in_(visible_request_ids)
            )
            candidate_statement = candidate_statement.where(
                SupplierCandidate.request_id.in_(visible_request_ids)
            )
        requests = (
            await self.session.scalars(
                request_statement.order_by(ProcurementRequest.updated_at.desc()).limit(limit)
            )
        ).all()
        for row in requests:
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.request_id,
                    request_id=row.request_id,
                    record_type="procurement_request",
                    title=row.item_or_service,
                    summary=f"Quantity {row.quantity}",
                    status=self._value(row.shortlist_status),
                    fields=[
                        self._field("Budget", f"{row.currency} {row.approved_budget or row.estimated_budget or 'Not recorded'}"),
                        self._field("Finance", self._value(row.finance_validation_status)),
                        self._field("Selection", self._value(row.selection_status), "warning" if self._value(row.selection_status) in {"required", "pending"} else "default"),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        candidates = (
            await self.session.scalars(
                candidate_statement.order_by(
                    SupplierCandidate.request_id,
                    SupplierCandidate.rank.asc().nulls_last(),
                ).limit(limit)
            )
        ).all()
        for row in candidates:
            eligible = (
                row.meets_minimum_specification
                and self._value(row.compliance_status) == "compliant"
            )
            records.append(
                DepartmentOperationalRecordResponse(
                    id=row.id,
                    request_id=row.request_id,
                    record_type="supplier_candidate",
                    title=row.supplier_name,
                    summary=row.item_or_service,
                    status="eligible" if eligible else "blocked",
                    fields=[
                        self._field("Total cost", f"{row.currency} {row.total_cost}"),
                        self._field("Score", row.overall_score or "Not scored"),
                        self._field("Rank", row.rank or "Not ranked"),
                        self._field("Compliance", self._value(row.compliance_status), "positive" if eligible else "warning"),
                        self._field("Availability", self._value(row.availability_status)),
                    ],
                    action_url=f"/app/requests/{row.request_id}",
                    updated_at=row.updated_at,
                )
            )
        return records
