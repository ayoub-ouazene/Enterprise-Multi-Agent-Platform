import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.failures.enums import CapabilityGapStatus
from app.failures.models import CapabilityGap, FailureLog
from app.failures.repository import CapabilityGapRepository, FailureLogRepository
from app.failures.schemas import (
    CapabilityGapCreate,
    CapabilityGapListFilters,
    CapabilityGapStatusUpdate,
    FailureCreate,
    FailureListFilters,
)
from app.notifications.enums import (
    NotificationActionType,
    NotificationSeverity,
    NotificationType,
)
from app.notifications.schemas import NotificationCreate
from app.notifications.service import NotificationService
from app.requests.enums import TERMINAL_REQUEST_STATUSES, RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.users.models import User
from app.users.repository import UserRepository
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.schemas import WorkflowEventCreate
from app.workflow.service import WorkflowEventService


class FailurePermissionError(BusinessValidationError):
    pass


def normalize_operation(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    if not normalized:
        raise BusinessValidationError("Requested operation cannot be normalized")
    return normalized[:255]


class _OperationalNotificationMixin:
    current_user: AuthenticatedUser
    user_repository: UserRepository
    notification_service: NotificationService

    async def _review_recipients(self, department_id: UUID | None) -> list[User]:
        if department_id is not None:
            managers = await self.user_repository.list_department_managers(
                department_id
            )
            if managers:
                return managers
        return await self.user_repository.list_company_accounts()

    async def _notify_reviewers(
        self,
        *,
        department_id: UUID | None,
        request_id: UUID | None,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_url: str | None = None,
    ) -> None:
        for recipient in await self._review_recipients(department_id):
            await self.notification_service.create(
                NotificationCreate(
                    recipient_user_id=recipient.id,
                    request_id=request_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    severity=NotificationSeverity.ERROR
                    if notification_type == NotificationType.REQUEST_FAILED
                    else NotificationSeverity.WARNING,
                    action_required=action_url is not None,
                    action_type=NotificationActionType.REVIEW_FAILURE
                    if action_url
                    else None,
                    action_url=action_url,
                    metadata={},
                ),
                commit=False,
            )


class FailureService(_OperationalNotificationMixin):
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: FailureLogRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
        workflow_event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or FailureLogRepository(
            session, current_user.company_id
        )
        self.request_repository = request_repository or BusinessRequestRepository(
            session, current_user.company_id
        )
        self.workflow_event_service = workflow_event_service or WorkflowEventService(
            session, current_user
        )
        self.notification_service = notification_service or NotificationService(
            session, current_user.company_id
        )
        self.user_repository = user_repository or UserRepository(
            session, current_user.company_id
        )

    def _manager_department(self) -> UUID | None:
        if self.current_user.actor_type == ActorType.COMPANY:
            return None
        if (
            self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER
            and self.current_user.is_manager
            and self.current_user.department_id
        ):
            return self.current_user.department_id
        raise FailurePermissionError("Internal failure access is not permitted")

    async def record(
        self,
        payload: FailureCreate,
        *,
        terminate_request: bool = False,
        commit: bool = True,
    ) -> FailureLog:
        try:
            business_request = None
            if payload.request_id is not None:
                business_request = await self.request_repository.get_by_id(
                    payload.request_id
                )
                if business_request is None:
                    raise NotFoundError("Business request not found")
            if terminate_request:
                if not payload.is_terminal or business_request is None:
                    raise BusinessValidationError(
                        "Terminal request failure requires a terminal failure and request"
                    )
                if business_request.status in TERMINAL_REQUEST_STATUSES:
                    raise BusinessValidationError("Terminal requests cannot fail again")
                if payload.department_id is not None and payload.department_id not in {
                    business_request.owner_department_id,
                    business_request.active_department_id,
                }:
                    raise BusinessValidationError(
                        "Failure department is not relevant to the request"
                    )
                await self.request_repository.update(
                    business_request.id,
                    {
                        "status": RequestStatus.FAILED,
                        "current_stage": RequestStatus.FAILED.value,
                        "final_reason": payload.safe_message,
                        "failed_at": datetime.now(UTC),
                    },
                )

            failure = await self.repository.create(
                request_id=payload.request_id,
                department_id=payload.department_id,
                failure_type=payload.failure_type,
                failure_source=payload.failure_source,
                failed_operation=payload.failed_operation,
                internal_message=payload.internal_message,
                safe_message=payload.safe_message,
                error_code=payload.error_code,
                technical_data=payload.technical_data,
                alternative_attempted=payload.alternative_attempted,
                alternative_description=payload.alternative_description,
                is_terminal=payload.is_terminal,
            )
            if failure is None:
                raise NotFoundError("Failure reference not found")

            event_type = (
                WorkflowEventType.REQUEST_FAILED
                if terminate_request
                else WorkflowEventType.FAILURE_RECORDED
            )
            visibility = (
                WorkflowEventVisibility.REQUESTER
                if terminate_request
                else (
                    WorkflowEventVisibility.MANAGER
                    if payload.department_id
                    else WorkflowEventVisibility.COMPANY
                )
            )
            if payload.request_id is not None:
                await self.workflow_event_service.append(
                    payload.request_id,
                    WorkflowEventCreate(
                        event_type=event_type,
                        stage="failed" if terminate_request else "failure_handling",
                        title="Request failed"
                        if terminate_request
                        else "Failure recorded",
                        message=payload.safe_message
                        if terminate_request
                        else "A processing issue was recorded for internal review.",
                        actor_type=WorkflowEventActorType.SYSTEM,
                        department_id=payload.department_id,
                        visibility=visibility,
                        event_data={
                            "failure_type": payload.failure_type.value,
                            "error_code": payload.error_code,
                        },
                    ),
                    commit=False,
                )

            if terminate_request and business_request is not None:
                await self.notification_service.create(
                    NotificationCreate(
                        recipient_user_id=business_request.requester_user_id,
                        request_id=business_request.id,
                        notification_type=NotificationType.REQUEST_FAILED,
                        title="Request failed",
                        message=payload.safe_message,
                        severity=NotificationSeverity.ERROR,
                        metadata={"request_status": RequestStatus.FAILED.value},
                    ),
                    commit=False,
                )
            await self._notify_reviewers(
                department_id=payload.department_id,
                request_id=payload.request_id,
                notification_type=NotificationType.REQUEST_FAILED,
                title="Failure requires review",
                message="A request processing failure requires authorized review.",
                action_url=f"/failures/{failure.id}",
            )
            if commit:
                await self.session.commit()
                await self.session.refresh(failure)
            return failure
        except Exception:
            if commit:
                await self.session.rollback()
            raise

    async def list(self, filters: FailureListFilters) -> list[FailureLog]:
        return await self.repository.list(
            department_id=self._manager_department(),
            failure_type=filters.failure_type,
            failure_source=filters.failure_source,
            resolved=filters.resolved,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get(self, failure_id: UUID) -> FailureLog:
        failure = await self.repository.get_by_id(
            failure_id, department_id=self._manager_department()
        )
        if failure is None:
            raise NotFoundError("Failure log not found")
        return failure

    async def resolve(self, failure_id: UUID) -> FailureLog:
        if self.current_user.actor_type != ActorType.COMPANY:
            raise FailurePermissionError("Only Company accounts can resolve failures")
        try:
            failure = await self.repository.resolve(
                failure_id,
                resolved_at=datetime.now(UTC),
                resolved_by_user_id=self.current_user.user_id,
            )
            if failure is None:
                raise NotFoundError("Failure log not found")
            await self.session.commit()
            await self.session.refresh(failure)
            return failure
        except Exception:
            await self.session.rollback()
            raise


class CapabilityGapService(_OperationalNotificationMixin):
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: CapabilityGapRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
        workflow_event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or CapabilityGapRepository(
            session, current_user.company_id
        )
        self.request_repository = request_repository or BusinessRequestRepository(
            session, current_user.company_id
        )
        self.workflow_event_service = workflow_event_service or WorkflowEventService(
            session, current_user
        )
        self.notification_service = notification_service or NotificationService(
            session, current_user.company_id
        )
        self.user_repository = user_repository or UserRepository(
            session, current_user.company_id
        )

    def _manager_department(self) -> UUID | None:
        if self.current_user.actor_type == ActorType.COMPANY:
            return None
        if (
            self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER
            and self.current_user.is_manager
            and self.current_user.department_id
        ):
            return self.current_user.department_id
        raise FailurePermissionError("Capability-gap access is not permitted")

    async def record(
        self,
        payload: CapabilityGapCreate,
        *,
        no_alternative: bool = False,
        commit: bool = True,
    ) -> CapabilityGap:
        try:
            business_request = None
            if payload.request_id is not None:
                business_request = await self.request_repository.get_by_id(
                    payload.request_id
                )
                if business_request is None:
                    raise NotFoundError("Business request not found")
                if payload.department_id is not None and payload.department_id not in {
                    business_request.owner_department_id,
                    business_request.active_department_id,
                }:
                    raise BusinessValidationError(
                        "Capability-gap department is not relevant to the request"
                    )
            normalized = normalize_operation(payload.requested_operation)
            scope = str(payload.department_id) if payload.department_id else "company"
            key = hashlib.sha256(f"{scope}:{normalized}".encode()).hexdigest()
            result = await self.repository.create_or_increment(
                request_id=payload.request_id,
                department_id=payload.department_id,
                requested_operation=payload.requested_operation,
                normalized_operation=normalized,
                deduplication_key=key,
                description=payload.description,
                safe_user_message=payload.safe_user_message,
                metadata=payload.metadata,
                now=datetime.now(UTC),
            )
            if result is None:
                raise NotFoundError("Capability-gap reference not found")
            gap, _ = result

            if payload.request_id is not None:
                await self.workflow_event_service.append(
                    payload.request_id,
                    WorkflowEventCreate(
                        event_type=WorkflowEventType.CAPABILITY_GAP_DETECTED,
                        stage="capability_gap",
                        title="Capability gap detected",
                        message="An unsupported operation was recorded for authorized review.",
                        actor_type=WorkflowEventActorType.SYSTEM,
                        department_id=payload.department_id,
                        visibility=WorkflowEventVisibility.MANAGER
                        if payload.department_id
                        else WorkflowEventVisibility.COMPANY,
                        event_data={"operation": normalized},
                    ),
                    commit=False,
                )
            await self._notify_reviewers(
                department_id=payload.department_id,
                request_id=payload.request_id,
                notification_type=NotificationType.CAPABILITY_GAP,
                title="Capability gap detected",
                message="An unsupported platform operation requires review.",
            )

            if no_alternative:
                if business_request is None:
                    raise BusinessValidationError(
                        "A request is required when no alternative exists"
                    )
                if business_request.status in TERMINAL_REQUEST_STATUSES:
                    raise BusinessValidationError("Terminal requests cannot fail again")
                now = datetime.now(UTC)
                await self.request_repository.update(
                    business_request.id,
                    {
                        "status": RequestStatus.FAILED,
                        "current_stage": RequestStatus.FAILED.value,
                        "final_reason": payload.safe_user_message,
                        "failed_at": now,
                    },
                )
                await self.workflow_event_service.append(
                    business_request.id,
                    WorkflowEventCreate(
                        event_type=WorkflowEventType.REQUEST_FAILED,
                        stage="failed",
                        title="Request failed",
                        message=payload.safe_user_message,
                        actor_type=WorkflowEventActorType.SYSTEM,
                        department_id=payload.department_id,
                        visibility=WorkflowEventVisibility.REQUESTER,
                        event_data={
                            "safe_failure_code": "required_capability_unavailable"
                        },
                    ),
                    commit=False,
                )
                await self.notification_service.create(
                    NotificationCreate(
                        recipient_user_id=business_request.requester_user_id,
                        request_id=business_request.id,
                        notification_type=NotificationType.REQUEST_FAILED,
                        title="Request could not be completed",
                        message=payload.safe_user_message,
                        severity=NotificationSeverity.ERROR,
                        metadata={"request_status": RequestStatus.FAILED.value},
                    ),
                    commit=False,
                )
            if commit:
                await self.session.commit()
                await self.session.refresh(gap)
            return gap
        except Exception:
            if commit:
                await self.session.rollback()
            raise

    async def list(self, filters: CapabilityGapListFilters) -> list[CapabilityGap]:
        return await self.repository.list(
            department_id=self._manager_department(),
            status=filters.status,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get(self, gap_id: UUID) -> CapabilityGap:
        gap = await self.repository.get_by_id(
            gap_id, department_id=self._manager_department()
        )
        if gap is None:
            raise NotFoundError("Capability gap not found")
        return gap

    async def update_status(
        self, gap_id: UUID, payload: CapabilityGapStatusUpdate
    ) -> CapabilityGap:
        if self.current_user.actor_type != ActorType.COMPANY:
            raise FailurePermissionError(
                "Only Company accounts can manage capability gaps"
            )
        try:
            closed = payload.status in {
                CapabilityGapStatus.RESOLVED,
                CapabilityGapStatus.REJECTED,
            }
            gap = await self.repository.update_status(
                gap_id,
                status=payload.status,
                resolution_notes=payload.resolution_notes,
                resolved_at=datetime.now(UTC) if closed else None,
                resolved_by_user_id=self.current_user.user_id if closed else None,
            )
            if gap is None:
                raise NotFoundError("Capability gap not found")
            await self.session.commit()
            await self.session.refresh(gap)
            return gap
        except Exception:
            await self.session.rollback()
            raise
