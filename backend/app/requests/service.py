from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.notifications.service import NotificationService
from app.requests.enums import (
    TERMINAL_REQUEST_STATUSES,
    RequestPriority,
    RequestStatus,
)
from app.requests.models import BusinessRequest
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.requests.schemas import (
    BusinessRequestCreate,
    BusinessRequestListFilters,
    BusinessRequestMetadataUpdate,
)
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.schemas import WorkflowEventCreate
from app.workflow.service import WorkflowEventService, actor_type_for_user
from app.workflow.state import build_initial_workflow_state


STATUS_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.CREATED: frozenset({RequestStatus.ROUTING, RequestStatus.CANCELLED}),
    RequestStatus.ROUTING: frozenset(
        {RequestStatus.PROCESSING, RequestStatus.CANCELLED}
    ),
    RequestStatus.PROCESSING: frozenset(
        {
            RequestStatus.WAITING_FOR_DEPARTMENT,
            RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
            RequestStatus.WAITING_FOR_HUMAN_ACTION,
            RequestStatus.UNDER_REVIEW,
            RequestStatus.COMPLETED,
            RequestStatus.CANCELLED,
        }
    ),
    RequestStatus.WAITING_FOR_DEPARTMENT: frozenset(
        {RequestStatus.PROCESSING, RequestStatus.CANCELLED}
    ),
    RequestStatus.WAITING_FOR_HUMAN_APPROVAL: frozenset(
        {RequestStatus.PROCESSING, RequestStatus.CANCELLED}
    ),
    RequestStatus.WAITING_FOR_HUMAN_ACTION: frozenset(
        {RequestStatus.PROCESSING, RequestStatus.CANCELLED}
    ),
    RequestStatus.UNDER_REVIEW: frozenset(
        {
            RequestStatus.PROCESSING,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
        }
    ),
    RequestStatus.COMPLETED: frozenset(),
    RequestStatus.REJECTED: frozenset(),
    RequestStatus.CANCELLED: frozenset(),
    RequestStatus.FAILED: frozenset(),
}


class RequestPermissionError(BusinessValidationError):
    pass


class InvalidStatusTransitionError(BusinessValidationError):
    pass


class CancellationNotAllowedError(BusinessValidationError):
    pass


class BusinessRequestService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: BusinessRequestRepository | None = None,
        workflow_event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or BusinessRequestRepository(
            session, current_user.company_id
        )
        self.workflow_event_service = workflow_event_service or WorkflowEventService(
            session,
            current_user,
        )
        self.notification_service = notification_service or NotificationService(
            session,
            current_user.company_id,
        )

    def _can_view(self, business_request: BusinessRequest) -> bool:
        return can_view_business_request(self.current_user, business_request)

    def _user_event_actor_type(self) -> WorkflowEventActorType:
        return actor_type_for_user(self.current_user)

    @staticmethod
    def _status_event(
        previous_status: RequestStatus,
        target_status: RequestStatus,
        *,
        stage: str,
        department_id: UUID | None,
    ) -> WorkflowEventCreate:
        if target_status == RequestStatus.ROUTING:
            event_type = WorkflowEventType.ROUTING_STARTED
            title = "Routing started"
            message = "The request is being routed to the appropriate department."
        elif target_status == RequestStatus.PROCESSING:
            if previous_status in {
                RequestStatus.WAITING_FOR_DEPARTMENT,
                RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
                RequestStatus.WAITING_FOR_HUMAN_ACTION,
                RequestStatus.UNDER_REVIEW,
            }:
                event_type = WorkflowEventType.REQUEST_RESUMED
                title = "Request resumed"
                message = "Processing has resumed."
            else:
                event_type = WorkflowEventType.STAGE_STARTED
                title = "Processing started"
                message = "The request is now being processed."
        elif target_status == RequestStatus.WAITING_FOR_DEPARTMENT:
            event_type = WorkflowEventType.DEPARTMENT_COLLABORATION_STARTED
            title = "Department collaboration started"
            message = "Another authorized department is contributing to the request."
        elif target_status == RequestStatus.WAITING_FOR_HUMAN_APPROVAL:
            event_type = WorkflowEventType.WAITING_FOR_HUMAN_APPROVAL
            title = "Waiting for approval"
            message = "The request is waiting for an authorized approval."
        elif target_status == RequestStatus.WAITING_FOR_HUMAN_ACTION:
            event_type = WorkflowEventType.WAITING_FOR_HUMAN_ACTION
            title = "Waiting for action"
            message = "The request is waiting for an authorized action."
        elif target_status == RequestStatus.UNDER_REVIEW:
            event_type = WorkflowEventType.REVIEW_STARTED
            title = "Review started"
            message = "The request has entered review."
        elif target_status == RequestStatus.COMPLETED:
            event_type = WorkflowEventType.REQUEST_COMPLETED
            title = "Request completed"
            message = "The request has been completed."
        elif target_status == RequestStatus.REJECTED:
            event_type = WorkflowEventType.REQUEST_REJECTED
            title = "Request rejected"
            message = "The request has been rejected."
        elif target_status == RequestStatus.FAILED:
            event_type = WorkflowEventType.REQUEST_FAILED
            title = "Request failed"
            message = "The request could not be completed."
        else:
            raise InvalidStatusTransitionError(
                f"No workflow event is defined for {target_status.value}"
            )

        return WorkflowEventCreate(
            event_type=event_type,
            stage=stage,
            title=title,
            message=message,
            actor_type=WorkflowEventActorType.SYSTEM,
            department_id=department_id,
            visibility=WorkflowEventVisibility.REQUESTER,
            event_data={
                "previous_status": previous_status.value,
                "new_status": target_status.value,
            },
        )

    async def _get_visible(self, request_id: UUID) -> BusinessRequest:
        business_request = await self.repository.get_by_id(request_id)
        if business_request is None or not self._can_view(business_request):
            raise NotFoundError("Business request not found")
        return business_request

    async def create(self, payload: BusinessRequestCreate) -> BusinessRequest:
        if (
            self.current_user.actor_type
            not in {ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER}
            and payload.priority != RequestPriority.NORMAL
        ):
            raise RequestPermissionError("This actor cannot assign request priority")
        if payload.custom_data and self.current_user.actor_type != ActorType.COMPANY:
            raise RequestPermissionError("This actor cannot assign custom request data")

        try:
            business_request = await self.repository.create(
                requester_user_id=self.current_user.user_id,
                requester_employee_id=self.current_user.employee_id,
                request_type=payload.request_type,
                title=payload.title,
                summary=payload.summary,
                priority=payload.priority,
                workflow_state={},
                custom_data=payload.custom_data,
            )
            business_request.workflow_state = build_initial_workflow_state(
                business_request
            ).to_storage()
            await self.workflow_event_service.append(
                business_request.id,
                WorkflowEventCreate(
                    event_type=WorkflowEventType.REQUEST_CREATED,
                    stage=business_request.current_stage,
                    title="Request created",
                    message="The request has been created.",
                    actor_type=self._user_event_actor_type(),
                    department_id=self.current_user.department_id,
                    visibility=WorkflowEventVisibility.REQUESTER,
                    event_data={},
                ),
                commit=False,
            )
            await self.notification_service.notify_request_created(
                business_request,
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(business_request)
            return business_request
        except Exception:
            await self.session.rollback()
            raise

    async def get(self, request_id: UUID) -> BusinessRequest:
        return await self._get_visible(request_id)

    async def list(self, filters: BusinessRequestListFilters) -> list[BusinessRequest]:
        requester_user_id: UUID | None = None
        department_id: UUID | None = None
        if self.current_user.actor_type != ActorType.COMPANY:
            requester_user_id = self.current_user.user_id
        if self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            department_id = self.current_user.department_id

        return await self.repository.list(
            status=filters.status,
            priority=filters.priority,
            request_type=filters.request_type,
            requester_user_id=requester_user_id,
            department_id=department_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update_metadata(
        self,
        request_id: UUID,
        payload: BusinessRequestMetadataUpdate,
    ) -> BusinessRequest:
        try:
            business_request = await self._get_visible(request_id)
            if business_request.status in TERMINAL_REQUEST_STATUSES:
                raise BusinessValidationError("Terminal requests cannot be modified")

            values = payload.model_dump(exclude_unset=True, exclude_none=True)
            is_requester = (
                business_request.requester_user_id == self.current_user.user_id
            )
            is_company = self.current_user.actor_type == ActorType.COMPANY
            is_manager = self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER

            if is_requester and not is_company and not is_manager:
                if business_request.status != RequestStatus.CREATED:
                    raise RequestPermissionError(
                        "Requester metadata can only be changed before routing"
                    )
                disallowed = set(values) - {"title", "summary"}
                if disallowed:
                    raise RequestPermissionError(
                        "Requester cannot change protected metadata"
                    )
            elif not (is_company or is_manager):
                raise RequestPermissionError("Request metadata update is not allowed")

            if values.get("custom_data") and not is_company:
                raise RequestPermissionError(
                    "Only a Company account can change custom request data"
                )

            updated = await self.repository.update(request_id, values)
            if updated is None:
                raise NotFoundError("Business request not found")
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except Exception:
            await self.session.rollback()
            raise

    async def transition_status(
        self,
        request_id: UUID,
        target_status: RequestStatus,
    ) -> BusinessRequest:
        if target_status == RequestStatus.CANCELLED:
            return await self.cancel(request_id)
        if target_status == RequestStatus.FAILED:
            raise InvalidStatusTransitionError(
                "Terminal failures must be recorded through FailureService"
            )

        try:
            business_request = await self._get_visible(request_id)
            allowed = STATUS_TRANSITIONS[business_request.status]
            if target_status not in allowed:
                raise InvalidStatusTransitionError(
                    f"Cannot transition from {business_request.status.value} "
                    f"to {target_status.value}"
                )
            if (
                target_status
                not in {
                    RequestStatus.ROUTING,
                    RequestStatus.CANCELLED,
                }
                and business_request.owner_department_id is None
            ):
                raise InvalidStatusTransitionError(
                    "An owner department is required for this status"
                )

            now = datetime.now(UTC)
            values: dict[str, object] = {
                "status": target_status,
                "current_stage": target_status.value,
            }
            if target_status == RequestStatus.COMPLETED:
                values["completed_at"] = now
            updated = await self.repository.update(request_id, values)
            if updated is None:
                raise NotFoundError("Business request not found")
            await self.workflow_event_service.append(
                request_id,
                self._status_event(
                    business_request.status,
                    target_status,
                    stage=target_status.value,
                    department_id=(
                        updated.active_department_id or updated.owner_department_id
                    ),
                ),
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except Exception:
            await self.session.rollback()
            raise

    @staticmethod
    def _has_irreversible_operation(business_request: BusinessRequest) -> bool:
        execution = business_request.workflow_state.get("execution", {})
        return isinstance(execution, dict) and (
            execution.get("irreversible_operation_completed") is True
        )

    async def cancel(self, request_id: UUID) -> BusinessRequest:
        try:
            business_request = await self._get_visible(request_id)
            if business_request.status in TERMINAL_REQUEST_STATUSES:
                raise CancellationNotAllowedError(
                    "Terminal requests cannot be cancelled"
                )
            if self._has_irreversible_operation(business_request):
                raise CancellationNotAllowedError(
                    "Request cannot be cancelled after an irreversible operation"
                )

            is_requester = (
                business_request.requester_user_id == self.current_user.user_id
            )
            is_company = self.current_user.actor_type == ActorType.COMPANY
            is_manager = (
                self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER
                and self._can_view(business_request)
            )
            if not (is_requester or is_company or is_manager):
                raise NotFoundError("Business request not found")

            if is_requester:
                reason = "Cancelled by requester"
            elif is_company:
                reason = "Cancelled by authorized Company account"
            else:
                reason = "Cancelled by authorized department manager"

            updated = await self.repository.update(
                request_id,
                {
                    "status": RequestStatus.CANCELLED,
                    "current_stage": RequestStatus.CANCELLED.value,
                    "cancelled_at": datetime.now(UTC),
                    "final_reason": reason,
                },
            )
            if updated is None:
                raise NotFoundError("Business request not found")
            await self.workflow_event_service.append(
                request_id,
                WorkflowEventCreate(
                    event_type=WorkflowEventType.REQUEST_CANCELLED,
                    stage=RequestStatus.CANCELLED.value,
                    title="Request cancelled",
                    message=reason,
                    actor_type=self._user_event_actor_type(),
                    department_id=self.current_user.department_id,
                    visibility=WorkflowEventVisibility.REQUESTER,
                    event_data={
                        "previous_status": business_request.status.value,
                        "new_status": RequestStatus.CANCELLED.value,
                    },
                ),
                commit=False,
            )
            await self.notification_service.notify_request_cancelled(
                updated,
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except Exception:
            await self.session.rollback()
            raise
