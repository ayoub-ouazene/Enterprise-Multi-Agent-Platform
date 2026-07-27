from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
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
    BusinessRequestDetailResponse,
    BusinessRequestListFilters,
    BusinessRequestMetadataUpdate,
    BusinessRequestSummaryResponse,
    ConnectedHumanActionResponse,
    RequestClarificationResponse,
    RequestDepartmentResponse,
    RequestFinalResultResponse,
    RequestSourceReferenceResponse,
)
from app.departments.models import Department
from app.human_actions.models import HumanAction
from app.users.models import User
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.schemas import WorkflowEventCreate
from app.workflow.service import WorkflowEventService, actor_type_for_user
from app.workflow.state import build_initial_workflow_state
from app.departments.hr.repository import LeaveBalanceRepository, LeaveRequestRepository
from app.departments.hr.tools import release_leave_reservation


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

    async def create(
        self, payload: BusinessRequestCreate, *, request_id: UUID | None = None
    ) -> BusinessRequest:
        if (
            self.current_user.actor_type
            not in {ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER}
            and payload.priority != RequestPriority.NORMAL
        ):
            raise RequestPermissionError("This actor cannot assign request priority")
        if payload.custom_data and self.current_user.actor_type != ActorType.COMPANY:
            raise RequestPermissionError("This actor cannot assign custom request data")

        try:
            create_values = dict(
                requester_user_id=self.current_user.user_id,
                requester_employee_id=self.current_user.employee_id,
                request_type=payload.request_type,
                title=payload.title,
                summary=payload.summary,
                priority=payload.priority,
                workflow_state={},
                custom_data=payload.custom_data,
            )
            if request_id is not None:
                create_values["request_id"] = request_id
            business_request = await self.repository.create(**create_values)
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

    async def get_detail(self, request_id: UUID) -> BusinessRequestDetailResponse:
        business_request = await self._get_visible(request_id)
        summaries = await self._present_summaries([business_request])
        actions = await self._connected_actions(business_request)
        state = (
            business_request.workflow_state
            if isinstance(business_request.workflow_state, dict)
            else {}
        )
        routing = state.get("routing") if isinstance(state.get("routing"), dict) else {}
        collaboration = (
            state.get("collaboration")
            if isinstance(state.get("collaboration"), dict)
            else {}
        )
        review = state.get("review") if isinstance(state.get("review"), dict) else {}
        failure = state.get("failure") if isinstance(state.get("failure"), dict) else {}
        result = state.get("result") if isinstance(state.get("result"), dict) else {}
        execution = (
            state.get("execution") if isinstance(state.get("execution"), dict) else {}
        )

        clarification = None
        question = routing.get("latest_question")
        if routing.get("needs_clarification") is True and isinstance(question, str):
            count = routing.get("clarification_count")
            clarification = RequestClarificationResponse(
                question=question,
                number=max(1, min(int(count or 1), 3)),
            )

        collaboration_summary = None
        if collaboration.get("is_active") is True:
            collaboration_summary = (
                "Another authorized department is assisting with this request."
                if self.current_user.actor_type == ActorType.EXTERNAL_USER
                else "A collaborating department is currently assisting the owner department."
            )

        quality_check_summary = None
        review_status = review.get("status")
        if business_request.status == RequestStatus.UNDER_REVIEW or review_status in {
            "pending",
            "in_progress",
            "revision_required",
        }:
            quality_check_summary = (
                "Internal revision is in progress."
                if review_status == "revision_required"
                else "A quality check is in progress before the workflow continues."
            )
        elif review_status == "approved":
            quality_check_summary = "The quality check completed successfully."

        failure_summary = None
        safe_failure = failure.get("safe_message")
        if isinstance(safe_failure, str) and safe_failure.strip():
            failure_summary = safe_failure.strip()
        elif business_request.status in {RequestStatus.FAILED, RequestStatus.REJECTED}:
            failure_summary = (
                business_request.final_reason
                or "This request could not be completed. Review the safe timeline for details."
            )

        final_result = self._safe_final_result(
            business_request,
            result=result,
            execution=execution,
        )
        allowed_actions: list[str] = []
        if summaries[0].can_cancel:
            allowed_actions.append("cancel")
        if clarification is not None:
            allowed_actions.append("answer_clarification")

        return BusinessRequestDetailResponse(
            **summaries[0].model_dump(),
            requester_employee_id=business_request.requester_employee_id,
            final_decision=business_request.final_decision,
            final_reason=business_request.final_reason,
            completed_at=business_request.completed_at,
            cancelled_at=business_request.cancelled_at,
            failed_at=business_request.failed_at,
            clarification=clarification,
            collaboration_summary=collaboration_summary,
            quality_check_summary=quality_check_summary,
            failure_summary=failure_summary,
            final_result=final_result,
            connected_actions=actions,
            allowed_actions=allowed_actions,
        )

    async def list(self, filters: BusinessRequestListFilters) -> list[BusinessRequest]:
        requester_user_id: UUID | None = None
        department_id: UUID | None = None
        if self.current_user.actor_type != ActorType.COMPANY:
            requester_user_id = self.current_user.user_id
        if self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            department_id = self.current_user.department_id
        requester_filter_id = None
        if self.current_user.actor_type in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            requester_filter_id = filters.requester_user_id

        return await self.repository.list(
            status=filters.status,
            priority=filters.priority,
            request_type=filters.request_type,
            search=filters.search,
            owner_department_id=filters.owner_department_id,
            requester_filter_id=requester_filter_id,
            attention_required=filters.attention_required,
            created_from=filters.created_from,
            created_to=filters.created_to,
            requester_user_id=requester_user_id,
            department_id=department_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def list_summaries(
        self,
        filters: BusinessRequestListFilters,
    ) -> list[BusinessRequestSummaryResponse]:
        return await self.present_summaries(await self.list(filters))

    async def present_summaries(
        self,
        requests: list[BusinessRequest],
    ) -> list[BusinessRequestSummaryResponse]:
        """Build the shared safe summary projection for already-authorized records."""
        return await self._present_summaries(requests)

    async def _present_summaries(
        self,
        requests: list[BusinessRequest],
    ) -> list[BusinessRequestSummaryResponse]:
        if not requests:
            return []
        department_ids = {
            department_id
            for request in requests
            for department_id in (
                request.owner_department_id,
                request.active_department_id,
            )
            if department_id is not None
        }
        departments: dict[UUID, RequestDepartmentResponse] = {}
        if department_ids:
            rows = (
                await self.session.scalars(
                    select(Department).where(
                        Department.company_id == self.current_user.company_id,
                        Department.id.in_(department_ids),
                    )
                )
            ).all()
            departments = {
                row.id: RequestDepartmentResponse(
                    id=row.id,
                    name=row.name,
                    department_type=row.department_type.value,
                )
                for row in rows
            }

        pending_counts = dict(
            (
                await self.session.execute(
                    select(HumanAction.request_id, func.count(HumanAction.id))
                    .where(
                        HumanAction.company_id == self.current_user.company_id,
                        HumanAction.request_id.in_([request.id for request in requests]),
                        HumanAction.status == "pending",
                    )
                    .group_by(HumanAction.request_id)
                )
            ).all()
        )

        requester_labels: dict[UUID, str] = {}
        if self.current_user.actor_type in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            requester_ids = {request.requester_user_id for request in requests}
            requester_labels = dict(
                (
                    await self.session.execute(
                        select(User.id, User.email).where(
                            User.company_id == self.current_user.company_id,
                            User.id.in_(requester_ids),
                        )
                    )
                ).all()
            )

        hide_departments = self.current_user.actor_type == ActorType.EXTERNAL_USER
        return [
            BusinessRequestSummaryResponse(
                id=request.id,
                request_type=request.request_type,
                title=request.title,
                summary=request.summary,
                status=request.status,
                current_stage=request.current_stage,
                current_state_summary=self._current_state_summary(request.status),
                priority=request.priority,
                owner_department_id=request.owner_department_id,
                active_department_id=request.active_department_id,
                owner_department=(
                    None
                    if hide_departments
                    else departments.get(request.owner_department_id)
                ),
                active_department=(
                    None
                    if hide_departments
                    else departments.get(request.active_department_id)
                ),
                requester_user_id=(
                    request.requester_user_id
                    if self.current_user.actor_type
                    in {ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER}
                    else None
                ),
                requester_label=requester_labels.get(request.requester_user_id),
                attention_required=(
                    int(pending_counts.get(request.id, 0)) > 0
                    or request.status
                    in {
                        RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
                        RequestStatus.WAITING_FOR_HUMAN_ACTION,
                        RequestStatus.FAILED,
                        RequestStatus.REJECTED,
                    }
                ),
                pending_action_count=int(pending_counts.get(request.id, 0)),
                can_cancel=(
                    request.status not in TERMINAL_REQUEST_STATUSES
                    and not self._has_irreversible_operation(request)
                ),
                created_at=request.created_at,
                updated_at=request.updated_at,
            )
            for request in requests
        ]

    async def _connected_actions(
        self,
        business_request: BusinessRequest,
    ) -> list[ConnectedHumanActionResponse]:
        actions = (
            await self.session.scalars(
                select(HumanAction)
                .where(
                    HumanAction.company_id == self.current_user.company_id,
                    HumanAction.request_id == business_request.id,
                )
                .order_by(HumanAction.created_at.desc())
                .limit(50)
            )
        ).all()
        is_privileged = self.current_user.actor_type in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }
        return [
            ConnectedHumanActionResponse(
                id=action.id,
                title=action.title,
                action_type=action.action_type,
                status=action.status,
                due_at=action.due_date,
                assigned_role=action.assigned_role if is_privileged else None,
                can_respond=(
                    action.status == "pending"
                    and (
                        is_privileged
                        or action.assigned_user_id == self.current_user.user_id
                    )
                ),
                action_url=(
                    f"/app/human-actions/{action.id}"
                    if is_privileged
                    or action.assigned_user_id == self.current_user.user_id
                    else None
                ),
            )
            for action in actions
        ]

    @staticmethod
    def _current_state_summary(status: RequestStatus) -> str:
        return {
            RequestStatus.CREATED: "The request was received and is ready for routing.",
            RequestStatus.ROUTING: "The Router is selecting the appropriate owner department.",
            RequestStatus.PROCESSING: "The owner department is working on the request.",
            RequestStatus.WAITING_FOR_DEPARTMENT: "Another authorized department is assisting.",
            RequestStatus.WAITING_FOR_HUMAN_APPROVAL: "The request is waiting for an authorized approval.",
            RequestStatus.WAITING_FOR_HUMAN_ACTION: "The request is waiting for authorized manual work or information.",
            RequestStatus.UNDER_REVIEW: "A quality check is in progress.",
            RequestStatus.COMPLETED: "The request completed successfully.",
            RequestStatus.REJECTED: "The request was not approved.",
            RequestStatus.CANCELLED: "The request was cancelled and will not continue.",
            RequestStatus.FAILED: "The request could not be completed.",
        }[status]

    @staticmethod
    def _safe_final_result(
        business_request: BusinessRequest,
        *,
        result: dict,
        execution: dict,
    ) -> RequestFinalResultResponse | None:
        if business_request.status != RequestStatus.COMPLETED:
            return None
        summary = result.get("final_response")
        if not isinstance(summary, str) or not summary.strip():
            summary = business_request.final_reason or business_request.final_decision
        if not isinstance(summary, str) or not summary.strip():
            summary = "The request completed successfully."

        references = execution.get("retrieval_references")
        safe_sources: list[RequestSourceReferenceResponse] = []
        if isinstance(references, list):
            for reference in references[:20]:
                if not isinstance(reference, dict):
                    continue
                title = reference.get("title") or reference.get("document_title")
                if not isinstance(title, str) or not title.strip():
                    continue
                document_id = reference.get("document_id")
                try:
                    parsed_id = UUID(str(document_id)) if document_id else None
                except (TypeError, ValueError):
                    parsed_id = None
                safe_sources.append(
                    RequestSourceReferenceResponse(
                        document_id=parsed_id,
                        title=title.strip(),
                        version=(
                            str(reference["version"])[:100]
                            if reference.get("version") is not None
                            else None
                        ),
                        section=(
                            str(reference["section"])[:255]
                            if reference.get("section") is not None
                            else None
                        ),
                        scope=(
                            str(reference["scope"])[:100]
                            if reference.get("scope") is not None
                            else None
                        ),
                    )
                )
        return RequestFinalResultResponse(
            title="Request completed",
            summary=summary.strip(),
            sources=safe_sources,
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

            leave_requests = LeaveRequestRepository(self.session, self.current_user.company_id)
            leave = await leave_requests.get(request_id)
            if leave is not None:
                await release_leave_reservation(
                    LeaveBalanceRepository(self.session, self.current_user.company_id),
                    leave_requests,
                    request_id,
                )
                leave.cancelled_at = datetime.now(UTC)

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
