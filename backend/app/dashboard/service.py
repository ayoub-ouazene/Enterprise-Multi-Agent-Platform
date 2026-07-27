from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.companies.models import Company
from app.core.enums import ActorType
from app.departments.models import Department
from app.departments.service import DepartmentWorkspaceService
from app.employees.models import Employee
from app.human_actions.models import HumanAction
from app.notifications.models import Notification
from app.onboarding.service import CompanyOnboardingService
from app.requests.enums import RequestStatus, TERMINAL_REQUEST_STATUSES
from app.requests.models import BusinessRequest
from app.users.models import User

from .schemas import (
    DashboardActionItem,
    DashboardActivityItem,
    DashboardAttentionItem,
    DashboardDepartmentItem,
    DashboardIdentity,
    DashboardMetric,
    DashboardReadinessItem,
    DashboardRequestItem,
    DashboardResponse,
)

ACTIVE_STATUSES = tuple(status for status in RequestStatus if status not in TERMINAL_REQUEST_STATUSES)


class DashboardService:
    """Build one bounded, authorization-scoped dashboard projection."""

    def __init__(self, session: AsyncSession, current_user: AuthenticatedUser) -> None:
        self.session = session
        self.user = current_user

    def _request_scope(self):
        conditions = [BusinessRequest.company_id == self.user.company_id]
        if self.user.actor_type == ActorType.DEPARTMENT_MANAGER:
            conditions.append(
                or_(
                    BusinessRequest.owner_department_id == self.user.department_id,
                    BusinessRequest.active_department_id == self.user.department_id,
                )
            )
        elif self.user.actor_type in {ActorType.EMPLOYEE, ActorType.EXTERNAL_USER}:
            conditions.append(BusinessRequest.requester_user_id == self.user.user_id)
        return and_(*conditions)

    def _action_scope(self):
        conditions = [HumanAction.company_id == self.user.company_id]
        if self.user.actor_type == ActorType.DEPARTMENT_MANAGER:
            conditions.extend(
                [
                    HumanAction.request_id == BusinessRequest.id,
                    self._request_scope(),
                ]
            )
        elif self.user.actor_type in {ActorType.EMPLOYEE, ActorType.EXTERNAL_USER}:
            conditions.append(HumanAction.assigned_user_id == self.user.user_id)
        return and_(*conditions)

    async def get(self) -> DashboardResponse:
        company = await self.session.scalar(
            select(Company).where(Company.id == self.user.company_id)
        )
        department = None
        if self.user.department_id:
            department = await self.session.scalar(
                select(Department).where(
                    Department.id == self.user.department_id,
                    Department.company_id == self.user.company_id,
                )
            )

        status_rows = (
            await self.session.execute(
                select(BusinessRequest.status, func.count(BusinessRequest.id))
                .where(self._request_scope())
                .group_by(BusinessRequest.status)
            )
        ).all()
        counts = {status.value: int(count) for status, count in status_rows}

        pending_count = int(
            await self.session.scalar(
                select(func.count(HumanAction.id)).where(
                    self._action_scope(), HumanAction.status == "pending"
                )
            )
            or 0
        )
        unread_count = int(
            await self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.company_id == self.user.company_id,
                    Notification.recipient_user_id == self.user.user_id,
                    Notification.is_read.is_(False),
                )
            )
            or 0
        )

        active_count = sum(counts.get(status.value, 0) for status in ACTIVE_STATUSES)
        metrics = self._metrics(counts, active_count, pending_count, unread_count)
        active = await self._requests(active=True, limit=6)
        completed = await self._requests(active=False, limit=5)
        actions = await self._actions()
        activity = await self._activity()
        attention = await self._attention(actions)
        readiness: list[DashboardReadinessItem] = []
        departments: list[DashboardDepartmentItem] = []

        if self.user.actor_type == ActorType.COMPANY:
            onboarding = await CompanyOnboardingService(
                self.session, self.user.company_id
            ).get_status()
            readiness = [
                DashboardReadinessItem(
                    key=item.requirement,
                    label=item.requirement.replace("_", " ").title(),
                    ready=item.satisfied,
                    detail=item.details,
                )
                for item in onboarding.items
            ]
            for item in readiness:
                if not item.ready and len(attention) < 8:
                    attention.insert(
                        0,
                        DashboardAttentionItem(
                            id=f"readiness:{item.key}",
                            severity="warning",
                            title=f"{item.label} needs attention",
                            explanation=item.detail or "Complete this readiness requirement.",
                            resource_type="readiness",
                            action_label="Continue setup",
                            action_url="/app/onboarding",
                        ),
                    )
            departments = await self._departments()
        elif self.user.actor_type == ActorType.DEPARTMENT_MANAGER and department:
            result = await DepartmentWorkspaceService(
                self.session, self.user.company_id
            ).get_readiness(department.id, department.department_type)
            readiness = [
                DashboardReadinessItem(
                    key=item.name.lower().replace(" ", "_"),
                    label=item.name,
                    ready=item.ready,
                    detail=item.detail,
                )
                for item in result.items
            ]

        account_label = (
            self.user.email.split("@", 1)[0].replace(".", " ").title()
            or self.user.email
        )
        return DashboardResponse(
            role=self.user.actor_type.value,
            identity=DashboardIdentity(
                company_name=company.name if company else "Company workspace",
                company_active=bool(company and company.is_active),
                account_label=account_label,
                department_name=department.name if department else None,
                department_type=department.department_type.value if department else None,
            ),
            metrics=metrics,
            attention=attention[:8],
            active_requests=active,
            completed_requests=completed,
            pending_actions=actions,
            activity=activity,
            readiness=readiness,
            departments=departments,
            generated_at=datetime.now(UTC),
        )

    def _metrics(self, counts, active, pending, unread):
        common = [
            DashboardMetric(key="active", label="Active requests", value=active, detail="Currently in progress", status="info", href="/app/requests"),
            DashboardMetric(key="actions", label="Action required", value=pending, detail="Pending human actions", status="warning" if pending else "success", href="/app/human-actions"),
            DashboardMetric(key="completed", label="Completed", value=counts.get("completed", 0), detail="All completed requests", status="success", href="/app/requests?status=completed"),
            DashboardMetric(key="notifications", label="Unread updates", value=unread, detail="Unread notifications", status="warning" if unread else "neutral", href="/app/notifications"),
        ]
        if self.user.actor_type == ActorType.COMPANY:
            common.insert(2, DashboardMetric(key="review", label="Quality review", value=counts.get("under_review", 0), detail="Under independent review", status="info", href="/app/requests?status=under_review"))
            common.append(DashboardMetric(key="failed", label="Failed or rejected", value=counts.get("failed", 0) + counts.get("rejected", 0), detail="Needs investigation", status="danger", href="/app/requests?status=failed"))
        return common

    async def _requests(self, *, active: bool, limit: int):
        condition = (
            BusinessRequest.status.in_(ACTIVE_STATUSES)
            if active
            else BusinessRequest.status == RequestStatus.COMPLETED
        )
        rows = list(
            (
                await self.session.scalars(
                    select(BusinessRequest)
                    .where(self._request_scope(), condition)
                    .order_by(BusinessRequest.updated_at.desc())
                    .limit(limit)
                )
            ).all()
        )
        dept_ids = {row.owner_department_id for row in rows if row.owner_department_id}
        names = {}
        if dept_ids:
            names = dict(
                (
                    await self.session.execute(
                        select(Department.id, Department.name).where(
                            Department.company_id == self.user.company_id,
                            Department.id.in_(dept_ids),
                        )
                    )
                ).all()
            )
        return [
            DashboardRequestItem(
                id=row.id,
                title=row.title,
                status=row.status.value,
                priority=row.priority.value,
                current_stage=row.current_stage,
                owner_department=names.get(row.owner_department_id),
                action_required=row.status
                in {
                    RequestStatus.WAITING_FOR_HUMAN_ACTION,
                    RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
                },
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def _actions(self):
        statement = (
            select(HumanAction)
            .where(self._action_scope(), HumanAction.status == "pending")
            .order_by(HumanAction.due_date.asc().nullslast(), HumanAction.created_at.desc())
            .limit(6)
        )
        return [
            DashboardActionItem(
                id=row.id,
                request_id=row.request_id,
                title=row.title,
                action_type=row.action_type,
                due_at=row.due_date,
                created_at=row.created_at,
            )
            for row in (await self.session.scalars(statement)).all()
        ]

    async def _activity(self):
        rows = (
            await self.session.scalars(
                select(Notification)
                .where(
                    Notification.company_id == self.user.company_id,
                    Notification.recipient_user_id == self.user.user_id,
                )
                .order_by(Notification.created_at.desc())
                .limit(8)
            )
        ).all()
        return [
            DashboardActivityItem(
                id=row.id,
                title=row.title,
                message=row.message,
                severity=row.severity.value,
                resource_url=row.action_url,
                occurred_at=row.created_at,
            )
            for row in rows
        ]

    async def _attention(self, actions):
        items = [
            DashboardAttentionItem(
                id=f"action:{action.id}",
                severity="warning",
                title=action.title,
                explanation="A response is required before this work can continue.",
                resource_type="human_action",
                resource_id=action.id,
                action_label="Review action",
                action_url=f"/app/human-actions/{action.id}",
                occurred_at=action.created_at,
                due_at=action.due_at,
            )
            for action in actions[:4]
        ]
        notifications = (
            await self.session.scalars(
                select(Notification)
                .where(
                    Notification.company_id == self.user.company_id,
                    Notification.recipient_user_id == self.user.user_id,
                    Notification.is_read.is_(False),
                    or_(
                        Notification.action_required.is_(True),
                        Notification.severity.in_(("warning", "error")),
                    ),
                )
                .order_by(Notification.created_at.desc())
                .limit(max(0, 8 - len(items)))
            )
        ).all()
        items.extend(
            DashboardAttentionItem(
                id=f"notification:{row.id}",
                severity=row.severity.value,
                title=row.title,
                explanation=row.message,
                resource_type="notification",
                resource_id=row.id,
                action_label="Open update",
                action_url=row.action_url or "/app/notifications",
                occurred_at=row.created_at,
            )
            for row in notifications
        )
        return items

    async def _departments(self):
        departments = list(
            (
                await self.session.scalars(
                    select(Department)
                    .where(Department.company_id == self.user.company_id)
                    .order_by(Department.name)
                )
            ).all()
        )
        managers = dict(
            (
                await self.session.execute(
                    select(Employee.department_id, User.email)
                    .join(User, User.id == Employee.user_id)
                    .where(
                        Employee.company_id == self.user.company_id,
                        User.actor_type == ActorType.DEPARTMENT_MANAGER,
                        User.is_active.is_(True),
                    )
                )
            ).all()
        )
        request_counts = dict(
            (
                await self.session.execute(
                    select(BusinessRequest.owner_department_id, func.count(BusinessRequest.id))
                    .where(
                        BusinessRequest.company_id == self.user.company_id,
                        BusinessRequest.status.in_(ACTIVE_STATUSES),
                    )
                    .group_by(BusinessRequest.owner_department_id)
                )
            ).all()
        )
        action_counts = dict(
            (
                await self.session.execute(
                    select(
                        BusinessRequest.owner_department_id,
                        func.count(HumanAction.id),
                    )
                    .join(HumanAction, HumanAction.request_id == BusinessRequest.id)
                    .where(
                        BusinessRequest.company_id == self.user.company_id,
                        HumanAction.company_id == self.user.company_id,
                        HumanAction.status == "pending",
                    )
                    .group_by(BusinessRequest.owner_department_id)
                )
            ).all()
        )
        return [
            DashboardDepartmentItem(
                id=dept.id,
                name=dept.name,
                department_type=dept.department_type.value,
                enabled=dept.is_active,
                manager_label=managers.get(dept.id),
                ready=dept.is_active and dept.id in managers,
                active_requests=int(request_counts.get(dept.id, 0)),
                pending_actions=int(action_counts.get(dept.id, 0)),
            )
            for dept in departments
        ]
