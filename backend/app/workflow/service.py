from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import NotFoundError
from app.departments.repository import DepartmentRepository
from app.departments.contracts import DepartmentExecutionResult
from app.departments.execution import DepartmentExecutionService
from app.failures.enums import FailureSource, FailureType
from app.failures.schemas import CapabilityGapCreate, FailureCreate
from app.llm.exceptions import (
    CustomerSupportClientError,
    CustomerSupportOutputError,
    FinanceClientError,
    FinanceOutputError,
    ITClientError,
    ITOutputError,
    RouterConfigurationError,
)
from app.rag.exceptions import KnowledgeProviderError
from app.llm.groq import GroqRouterClient
from app.notifications.service import NotificationService
from app.notifications.enums import NotificationActionType, NotificationSeverity, NotificationType
from app.notifications.schemas import NotificationCreate
from app.rag.pinecone import PineconeProvider
from app.users.repository import UserRepository
from app.requests.enums import TERMINAL_REQUEST_STATUSES, RequestStatus
from app.requests.models import BusinessRequest
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.exceptions import (
    WorkflowAlreadyStartedError,
    WorkflowClarificationAnswerRequiredError,
    WorkflowExecutionFailedError,
    WorkflowNotStartedError,
    WorkflowPermissionError,
    WorkflowPersistenceError,
    WorkflowTerminalError,
)
from app.workflow.graph import workflow_graph
from app.workflow.models import WorkflowEvent
from app.workflow.persistence import WorkflowPersistence
from app.workflow.repository import WorkflowEventRepository
from app.workflow.router_output import RouterMessageCategory, RouterOutput
from app.workflow.schemas import (
    WorkflowControlResponse,
    WorkflowEventCreate,
    WorkflowEventPublicResponse,
)
from app.workflow.state import (
    COMPLETED_STEP,
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    ROUTED_STEP,
    WORKFLOW_STARTED_STEP,
    DepartmentRuntimeContext,
    WorkflowFailureState,
    WorkflowResultState,
    WorkflowRuntimeContext,
    WorkflowState,
    add_completed_step,
    apply_state_update,
)


ACTOR_LABELS: dict[WorkflowEventActorType, str] = {
    WorkflowEventActorType.SYSTEM: "System",
    WorkflowEventActorType.ROUTER: "Platform assistant",
    WorkflowEventActorType.DEPARTMENT_AGENT: "Department",
    WorkflowEventActorType.REVIEWER: "Reviewer",
    WorkflowEventActorType.USER: "Requester",
    WorkflowEventActorType.MANAGER: "Department manager",
    WorkflowEventActorType.COMPANY_ACCOUNT: "Company account",
    WorkflowEventActorType.TOOL: "System tool",
}


def actor_type_for_user(current_user: AuthenticatedUser) -> WorkflowEventActorType:
    if current_user.actor_type == ActorType.COMPANY:
        return WorkflowEventActorType.COMPANY_ACCOUNT
    if current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
        return WorkflowEventActorType.MANAGER
    return WorkflowEventActorType.USER


class WorkflowEventService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: WorkflowEventRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or WorkflowEventRepository(
            session,
            current_user.company_id,
        )
        self.request_repository = request_repository or BusinessRequestRepository(
            session,
            current_user.company_id,
        )

    async def append(
        self,
        request_id: UUID,
        payload: WorkflowEventCreate,
        *,
        commit: bool = True,
    ) -> WorkflowEvent:
        actor_user_id = None
        if payload.actor_type in {
            WorkflowEventActorType.USER,
            WorkflowEventActorType.MANAGER,
            WorkflowEventActorType.COMPANY_ACCOUNT,
        }:
            actor_user_id = self.current_user.user_id

        try:
            event = await self.repository.append(
                request_id=request_id,
                event_type=payload.event_type,
                stage=payload.stage,
                title=payload.title,
                message=payload.message,
                actor_type=payload.actor_type,
                actor_user_id=actor_user_id,
                department_id=payload.department_id,
                visibility=payload.visibility,
                event_data=payload.event_data,
            )
            if event is None:
                raise NotFoundError("Business request not found")
            if commit:
                await self.session.commit()
                await self.session.refresh(event)
            return event
        except Exception:
            if commit:
                await self.session.rollback()
            raise

    def _allowed_visibilities(self) -> frozenset[WorkflowEventVisibility]:
        if self.current_user.actor_type == ActorType.COMPANY:
            return frozenset(
                {
                    WorkflowEventVisibility.REQUESTER,
                    WorkflowEventVisibility.MANAGER,
                    WorkflowEventVisibility.COMPANY,
                }
            )
        if self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            return frozenset(
                {
                    WorkflowEventVisibility.REQUESTER,
                    WorkflowEventVisibility.MANAGER,
                }
            )
        return frozenset({WorkflowEventVisibility.REQUESTER})

    async def timeline(
        self,
        request_id: UUID,
        *,
        event_type: WorkflowEventType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEventPublicResponse]:
        business_request = await self.request_repository.get_by_id(request_id)
        if business_request is None or not can_view_business_request(
            self.current_user,
            business_request,
        ):
            raise NotFoundError("Business request not found")

        allowed_visibilities = self._allowed_visibilities()
        events = await self.repository.list_for_request(
            request_id,
            visibilities=allowed_visibilities,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
        return [
            WorkflowEventPublicResponse(
                id=event.id,
                request_id=event.request_id,
                event_type=event.event_type,
                stage=event.stage,
                title=event.title,
                message=event.message,
                actor_label=ACTOR_LABELS[event.actor_type],
                department_id=event.department_id,
                event_data=event.event_data,
                sequence_number=event.sequence_number,
                created_at=event.created_at,
            )
            for event in events
            if event.visibility in allowed_visibilities
        ]


class WorkflowService:
    """Start and resume the centralized graph using durable short checkpoints."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        *,
        settings: Settings | None = None,
        router_client: Any | None = None,
        persistence: WorkflowPersistence | None = None,
        department_repository: DepartmentRepository | None = None,
        department_execution_service: DepartmentExecutionService | None = None,
        workflow_event_service: WorkflowEventService | None = None,
        notification_service: NotificationService | None = None,
        failure_service: Any | None = None,
        capability_gap_service: Any | None = None,
        graph: Any | None = None,
        pinecone_provider: PineconeProvider | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.settings = settings
        self.router_client = router_client
        self.persistence = persistence or WorkflowPersistence(session, current_user)
        self.department_repository = department_repository or DepartmentRepository(
            session,
            current_user.company_id,
        )
        self.department_execution_service = (
            department_execution_service
            if department_execution_service is not None
            else DepartmentExecutionService(
                session,
                current_user,
                department_repository=self.department_repository,
                settings=settings,
                pinecone_provider=pinecone_provider or (
                    PineconeProvider(settings) if settings is not None else None
                ),
            )
        )
        self.workflow_event_service = workflow_event_service or WorkflowEventService(
            session,
            current_user,
        )
        self.notification_service = notification_service or NotificationService(
            session,
            current_user.company_id,
        )
        if failure_service is None or capability_gap_service is None:
            from app.failures.service import CapabilityGapService, FailureService

            failure_service = failure_service or FailureService(session, current_user)
            capability_gap_service = capability_gap_service or CapabilityGapService(
                session,
                current_user,
            )
        self.failure_service = failure_service
        self.capability_gap_service = capability_gap_service
        self.graph = graph or workflow_graph

    def _get_router_client(self) -> Any:
        if self.router_client is None:
            if self.settings is None:
                raise RouterConfigurationError(
                    "Router settings are unavailable for this invocation"
                )
            self.router_client = GroqRouterClient(self.settings)
        self.router_client.validate_configuration()
        return self.router_client

    @staticmethod
    def _response(state: WorkflowState) -> WorkflowControlResponse:
        response = state.result.final_response
        if state.routing.needs_clarification:
            response = state.routing.latest_question
        return WorkflowControlResponse(
            request_id=state.request.request_id,
            status=state.request.status,
            current_stage=state.request.current_stage,
            owner_department_id=state.request.owner_department_id,
            active_department_id=state.request.active_department_id,
            state_version=state.state_version,
            message_category=state.routing.message_category,
            owner_department=state.routing.selected_department,
            needs_clarification=state.routing.needs_clarification,
            clarification_question=state.routing.latest_question,
            response=response,
        )

    def _authorize_control(
        self,
        business_request: BusinessRequest,
        *,
        allow_requester: bool = False,
    ) -> None:
        if self.current_user.actor_type == ActorType.COMPANY:
            return
        if allow_requester and business_request.requester_user_id == self.current_user.user_id:
            return
        if (
            self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER
            and self.current_user.is_manager
            and self.current_user.department_id is not None
            and self.current_user.department_id
            in {
                business_request.owner_department_id,
                business_request.active_department_id,
            }
        ):
            return
        raise WorkflowPermissionError("Workflow control is not permitted")

    async def _load_department_context(
        self,
    ) -> dict[DepartmentType, DepartmentRuntimeContext]:
        departments = await self.department_repository.list()
        return {
            department.department_type: DepartmentRuntimeContext(
                department_id=department.id,
                is_active=department.is_active,
            )
            for department in departments
        }

    async def _rollback_and_raise(self, exc: Exception) -> None:
        await self.session.rollback()
        raise exc

    async def start(self, request_id: UUID) -> WorkflowControlResponse:
        return await self._start(request_id, allow_requester=False)

    async def start_for_submission(
        self,
        request_id: UUID,
        *,
        preclassified_output: RouterOutput,
        precomputed_department_result: dict[str, Any] | None = None,
    ) -> WorkflowControlResponse:
        return await self._start(
            request_id,
            allow_requester=True,
            preclassified_output=preclassified_output,
            precomputed_department_result=precomputed_department_result,
        )

    async def _start(
        self,
        request_id: UUID,
        *,
        allow_requester: bool,
        preclassified_output: RouterOutput | None = None,
        precomputed_department_result: dict[str, Any] | None = None,
    ) -> WorkflowControlResponse:
        try:
            business_request = await self.persistence.load_request(
                request_id,
                for_update=True,
            )
            if business_request is None:
                raise NotFoundError("Business request not found")
            self._authorize_control(
                business_request,
                allow_requester=allow_requester,
            )
            if business_request.status in TERMINAL_REQUEST_STATUSES:
                raise WorkflowTerminalError("Terminal requests cannot be started")
            if business_request.status != RequestStatus.CREATED:
                raise WorkflowAlreadyStartedError("Workflow has already started")

            state = self.persistence.load_state(business_request)
            if WORKFLOW_STARTED_STEP in state.planning.completed_steps:
                raise WorkflowAlreadyStartedError("Workflow has already started")
            router_client = self._get_router_client()
            departments = await self._load_department_context()

            request_state = state.request.model_copy(
                update={
                    "status": RequestStatus.ROUTING,
                    "current_stage": RequestStatus.ROUTING.value,
                }
            )
            planning = add_completed_step(state, WORKFLOW_STARTED_STEP).model_copy(
                update={
                    "pending_steps": [
                        ROUTED_STEP,
                        DEPARTMENT_STARTED_STEP,
                        DEPARTMENT_COMPLETED_STEP,
                        COMPLETED_STEP,
                    ],
                    "current_step": "initialize",
                }
            )
            state = apply_state_update(
                state,
                {"request": request_state, "planning": planning},
            )
            await self.persistence.save_checkpoint(state)
            await self.workflow_event_service.append(
                request_id,
                WorkflowEventCreate(
                    event_type=WorkflowEventType.ROUTING_STARTED,
                    stage=RequestStatus.ROUTING.value,
                    title="Routing started",
                    message="The request is being routed to the appropriate department.",
                    actor_type=WorkflowEventActorType.ROUTER,
                    visibility=WorkflowEventVisibility.REQUESTER,
                    event_data={},
                ),
                commit=False,
            )
            await self.session.commit()
        except Exception as exc:
            await self._rollback_and_raise(exc)

        return await self._execute_graph(
            state,
            router_client=router_client,
            departments=departments,
            preclassified_output=preclassified_output,
            precomputed_department_result=precomputed_department_result,
        )

    async def resume(self, request_id: UUID) -> WorkflowControlResponse:
        return await self._resume(request_id, allow_requester=False)

    async def resume_for_requester(
        self,
        request_id: UUID,
        *,
        clarification_answer: str,
    ) -> WorkflowControlResponse:
        return await self._resume(
            request_id,
            allow_requester=True,
            clarification_answer=clarification_answer,
        )

    async def _resume(
        self,
        request_id: UUID,
        *,
        allow_requester: bool,
        clarification_answer: str | None = None,
    ) -> WorkflowControlResponse:
        try:
            business_request = await self.persistence.load_request(
                request_id,
                for_update=True,
            )
            if business_request is None:
                raise NotFoundError("Business request not found")
            self._authorize_control(
                business_request,
                allow_requester=allow_requester,
            )
            if business_request.status in TERMINAL_REQUEST_STATUSES:
                raise WorkflowTerminalError("Terminal requests cannot be resumed")
            if business_request.status == RequestStatus.CREATED:
                raise WorkflowNotStartedError("Workflow has not been started")

            state = self.persistence.load_state(business_request)
            if WORKFLOW_STARTED_STEP not in state.planning.completed_steps:
                raise WorkflowNotStartedError("Workflow has no start checkpoint")
            router_client = self._get_router_client()
            if (
                state.routing.needs_clarification
                and clarification_answer is None
            ):
                raise WorkflowClarificationAnswerRequiredError(
                    "A clarification answer is required"
                )
            if clarification_answer is not None:
                if not (
                    state.routing.needs_clarification
                ):
                    raise WorkflowClarificationAnswerRequiredError(
                        "The workflow is not waiting for clarification"
                    )
                routing = state.routing.model_copy(
                    update={
                        "latest_answer": clarification_answer,
                        "needs_clarification": False,
                    }
                )
                state = apply_state_update(state, {"routing": routing})
                await self.persistence.save_checkpoint(state)

            departments = await self._load_department_context()
            await self.workflow_event_service.append(
                request_id,
                WorkflowEventCreate(
                    event_type=WorkflowEventType.REQUEST_RESUMED,
                    stage=state.request.current_stage,
                    title="Request resumed",
                    message="Workflow processing has resumed.",
                    actor_type=WorkflowEventActorType.ROUTER,
                    department_id=state.request.active_department_id,
                    visibility=WorkflowEventVisibility.REQUESTER,
                    event_data={},
                ),
                commit=False,
            )
            await self.session.commit()
        except Exception as exc:
            await self._rollback_and_raise(exc)

        return await self._execute_graph(
            state,
            router_client=router_client,
            departments=departments,
        )

    async def _execute_graph(
        self,
        state: WorkflowState,
        *,
        router_client: Any,
        departments: dict[DepartmentType, DepartmentRuntimeContext],
        preclassified_output: RouterOutput | None = None,
        precomputed_department_result: dict[str, Any] | None = None,
    ) -> WorkflowControlResponse:
        current_state = state
        runtime_context = WorkflowRuntimeContext(
            router_client=router_client,
            departments=departments,
            preclassified_output=preclassified_output,
            department_execution_service=self.department_execution_service,
            precomputed_department_result=precomputed_department_result,
        )
        try:
            async for part in self.graph.astream(
                current_state,
                context=runtime_context,
                stream_mode="updates",
                version="v2",
            ):
                if part["type"] != "updates":
                    continue
                for node_name, update in part["data"].items():
                    current_state = apply_state_update(current_state, update or {})
                    current_state = await self._persist_node_checkpoint(
                        node_name,
                        current_state,
                    )
        except RouterConfigurationError:
            raise
        except WorkflowPersistenceError as exc:
            await self._record_graph_failure(current_state, exc)
            raise WorkflowExecutionFailedError(
                "Workflow persistence failed and was recorded safely"
            ) from exc
        except Exception as exc:
            await self._record_graph_failure(current_state, exc)
            raise WorkflowExecutionFailedError(
                "Workflow execution failed and was recorded safely"
            ) from exc
        return self._response(current_state)

    async def _persist_node_checkpoint(
        self,
        node_name: str,
        state: WorkflowState,
    ) -> WorkflowState:
        try:
            if (
                node_name == "router"
                and state.routing.message_category == RouterMessageCategory.UNSUPPORTED
                and state.routing.is_capability_gap
            ):
                state = await self._record_capability_gap(state)
            if node_name == "department_execution" and state.execution.department_result:
                department_result = DepartmentExecutionResult.model_validate(
                    state.execution.department_result)
                if department_result.status.value == "unsupported":
                    state = await self._record_department_capability_gap(
                        state, department_result)

            business_request = await self.persistence.save_checkpoint(state)
            if node_name == "department_execution":
                persist_support = getattr(
                    self.department_execution_service,
                    "persist_department_result",
                    None,
                )
                if persist_support is not None:
                    await persist_support(state)
            if node_name == "collaboration":
                persist_collaboration = getattr(self.department_execution_service,
                    "persist_it_collaboration_result", None)
                if persist_collaboration is not None:
                    await persist_collaboration(state)
                persist_finance = getattr(
                    self.department_execution_service,
                    "persist_finance_collaboration_result",
                    None,
                )
                if persist_finance is not None:
                    await persist_finance(state)
            event = self._event_for_node(node_name, state)
            if event is not None:
                await self.workflow_event_service.append(
                    state.request.request_id,
                    event,
                    commit=False,
                )
            if node_name == "completion":
                await self.notification_service.notify_terminal_request(
                    business_request,
                    RequestStatus.COMPLETED,
                    commit=False,
                )
            if node_name == "human_action":
                await self._notify_human_escalation(state)
            await self.session.commit()
            return state
        except Exception as exc:
            await self.session.rollback()
            if isinstance(exc, WorkflowPersistenceError):
                raise
            raise WorkflowPersistenceError(
                "Workflow checkpoint transaction failed"
            ) from exc

    async def _notify_human_escalation(self, state: WorkflowState) -> None:
        users = UserRepository(self.session, self.current_user.company_id)
        recipients = []
        target_department_id = state.request.owner_department_id
        raw_result = state.execution.department_result
        if raw_result.get("department_type") == DepartmentType.FINANCE.value:
            finance = await DepartmentRepository(
                self.session, self.current_user.company_id
            ).get_by_type(DepartmentType.FINANCE)
            if finance is not None:
                target_department_id = finance.id
        if target_department_id is not None:
            recipients = await users.list_department_managers(target_department_id)
        if not recipients:
            recipients = await users.list_company_accounts()
        for recipient in recipients:
            await self.notification_service.create(
                NotificationCreate(
                    recipient_user_id=recipient.id,
                    request_id=state.request.request_id,
                    notification_type=NotificationType.HUMAN_ACTION_REQUIRED,
                    title="Department action required",
                    message="A department request needs authorized human assistance.",
                    severity=NotificationSeverity.WARNING,
                    action_required=True,
                    action_type=NotificationActionType.VIEW_REQUEST,
                    action_url=f"/requests/{state.request.request_id}",
                    metadata={"stage": state.request.current_stage},
                ),
                commit=False,
            )

    @staticmethod
    def _event_for_node(
        node_name: str,
        state: WorkflowState,
    ) -> WorkflowEventCreate | None:
        router_common = {
            "actor_type": WorkflowEventActorType.ROUTER,
            "department_id": state.request.active_department_id,
            "visibility": WorkflowEventVisibility.REQUESTER,
            "event_data": {},
        }
        if (
            node_name == "router"
            and state.routing.message_category
            in {
                RouterMessageCategory.DEPARTMENT_QUESTION,
                RouterMessageCategory.BUSINESS_REQUEST,
            }
        ):
            return WorkflowEventCreate(
                event_type=WorkflowEventType.REQUEST_ROUTED,
                stage=state.request.current_stage,
                title="Request routed",
                message="The request was routed to its owner department.",
                event_data={
                    "owner_department": state.routing.selected_department.value,
                    "request_type": state.request.request_type,
                },
                **{
                    key: value
                    for key, value in router_common.items()
                    if key != "event_data"
                },
            )
        if node_name == "department_stage_start":
            return WorkflowEventCreate(
                event_type=WorkflowEventType.STAGE_STARTED,
                stage=state.request.current_stage,
                title="Department processing started",
                message="The owner department started processing the request.",
                actor_type=WorkflowEventActorType.DEPARTMENT_AGENT,
                department_id=state.request.active_department_id,
                visibility=WorkflowEventVisibility.REQUESTER,
                event_data={},
            )
        if node_name == "department_execution":
            result = DepartmentExecutionResult.model_validate(
                state.execution.department_result
            )
            return WorkflowEventCreate(
                event_type=WorkflowEventType.STAGE_COMPLETED,
                stage=state.request.current_stage,
                title=result.safe_event_title,
                message=result.safe_event_message,
                actor_type=WorkflowEventActorType.DEPARTMENT_AGENT,
                department_id=state.request.active_department_id,
                visibility=WorkflowEventVisibility.REQUESTER,
                event_data={"department_type": result.department_type.value},
            )
        if node_name == "collaboration":
            request = state.collaboration.request
            receiver = request.get("receiver_department") if request else None
            return WorkflowEventCreate(
                event_type=WorkflowEventType.DEPARTMENT_COLLABORATION_STARTED,
                stage=state.request.current_stage,
                title="Department collaboration updated",
                message=(
                    "A collaborating department returned a structured result."
                    if state.collaboration.structured_result
                    else f"A collaboration with {receiver or 'another department'} was prepared."
                ),
                actor_type=WorkflowEventActorType.DEPARTMENT_AGENT,
                department_id=state.request.owner_department_id,
                visibility=WorkflowEventVisibility.REQUESTER,
                event_data={"owner_department": state.routing.selected_department.value if state.routing.selected_department else "unknown"},
            )
        if node_name == "human_action":
            department = state.execution.department_result.get("department_type")
            return WorkflowEventCreate(
                event_type=WorkflowEventType.WAITING_FOR_HUMAN_ACTION,
                stage=state.request.current_stage,
                title="Authorized action prepared",
                message=(
                    "Finance prepared this request for authorized spending approval."
                    if department == DepartmentType.FINANCE.value
                    else "The department prepared this request for authorized human assistance."
                ),
                actor_type=WorkflowEventActorType.DEPARTMENT_AGENT,
                department_id=state.request.owner_department_id,
                visibility=WorkflowEventVisibility.MANAGER,
                event_data={},
            )
        if node_name == "completion":
            return WorkflowEventCreate(
                event_type=WorkflowEventType.REQUEST_COMPLETED,
                stage=state.request.current_stage,
                title="Request completed",
                message="The request completed its current workflow.",
                actor_type=WorkflowEventActorType.SYSTEM,
                department_id=state.request.active_department_id,
                visibility=WorkflowEventVisibility.REQUESTER,
                event_data={},
            )
        return None

    async def _record_capability_gap(self, state: WorkflowState) -> WorkflowState:
        safe_message = (
            state.routing.unsupported_reason
            or "This operation is not currently supported by the platform."
        )
        await self.capability_gap_service.record(
            CapabilityGapCreate(
                request_id=state.request.request_id,
                department_id=state.request.owner_department_id,
                requested_operation=state.routing.request_type
                or "unsupported_platform_operation",
                description=state.routing.routing_reason
                or "A meaningful unsupported capability was identified.",
                safe_user_message=safe_message,
                metadata={"source": "router"},
            ),
            no_alternative=True,
            commit=False,
        )
        request = state.request.model_copy(
            update={
                "status": RequestStatus.FAILED,
                "current_stage": RequestStatus.FAILED.value,
            }
        )
        failure = WorkflowFailureState(
            has_failure=True,
            failure_type="capability_gap",
            safe_message=safe_message,
            alternative_attempted=False,
            terminal=True,
        )
        result = WorkflowResultState(
            decision=RequestStatus.FAILED.value,
            reason=safe_message,
            final_response=safe_message,
        )
        return apply_state_update(
            state,
            {"request": request, "failure": failure, "result": result},
        )

    async def _record_department_capability_gap(
        self, state: WorkflowState, department_result: DepartmentExecutionResult
    ) -> WorkflowState:
        await self.capability_gap_service.record(CapabilityGapCreate(
            request_id=state.request.request_id,
            department_id=state.request.owner_department_id,
            requested_operation=department_result.decision,
            description=department_result.reason,
            safe_user_message=department_result.user_message,
            metadata={"source": department_result.department_type.value}),
            no_alternative=True, commit=False)
        request = state.request.model_copy(update={"status": RequestStatus.FAILED,
            "current_stage": RequestStatus.FAILED.value})
        failure = WorkflowFailureState(has_failure=True, failure_type="capability_gap",
            safe_message=department_result.user_message, terminal=True)
        result = WorkflowResultState(decision=RequestStatus.FAILED.value,
            reason=department_result.reason, final_response=department_result.user_message)
        return apply_state_update(state, {"request": request, "failure": failure, "result": result})

    async def _record_graph_failure(
        self,
        state: WorkflowState,
        exc: Exception,
    ) -> None:
        safe_message = (
            "The workflow could not be completed due to an internal processing error."
        )
        failure_type = FailureType.WORKFLOW_FAILURE
        failure_source = FailureSource.WORKFLOW
        if isinstance(exc, KnowledgeProviderError):
            failure_type = FailureType.RETRIEVAL_FAILURE
            failure_source = FailureSource.RAG
            safe_message = "Company knowledge is temporarily unavailable."
        elif isinstance(exc, CustomerSupportOutputError):
            failure_type = FailureType.VALIDATION_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "Customer Support could not validate its response."
        elif isinstance(exc, CustomerSupportClientError):
            failure_type = FailureType.EXTERNAL_SERVICE_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "Customer Support is temporarily unavailable."
        elif isinstance(exc, ITOutputError):
            failure_type = FailureType.VALIDATION_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "IT could not validate its response."
        elif isinstance(exc, ITClientError):
            failure_type = FailureType.EXTERNAL_SERVICE_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "IT is temporarily unavailable."
        elif isinstance(exc, FinanceOutputError):
            failure_type = FailureType.VALIDATION_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "Finance could not validate its response."
        elif isinstance(exc, FinanceClientError):
            failure_type = FailureType.EXTERNAL_SERVICE_FAILURE
            failure_source = FailureSource.LLM
            safe_message = "Finance is temporarily unavailable."
        try:
            failure = await self.failure_service.record(
                FailureCreate(
                    request_id=state.request.request_id,
                    department_id=(
                        state.request.active_department_id
                        or state.request.owner_department_id
                    ),
                    failure_type=failure_type,
                    failure_source=failure_source,
                    failed_operation=state.request.current_stage,
                    internal_message=type(exc).__name__,
                    safe_message=safe_message,
                    alternative_attempted=False,
                    is_terminal=True,
                ),
                terminate_request=True,
                commit=False,
            )
            request_state = state.request.model_copy(
                update={
                    "status": RequestStatus.FAILED,
                    "current_stage": RequestStatus.FAILED.value,
                }
            )
            failure_state = WorkflowFailureState(
                has_failure=True,
                failure_type=failure_type.value,
                safe_message=safe_message,
                failure_log_id=failure.id,
                alternative_attempted=False,
                terminal=True,
            )
            result = WorkflowResultState(
                decision=RequestStatus.FAILED.value,
                reason=safe_message,
                final_response=safe_message,
                completed_at=None,
            )
            failed_state = apply_state_update(
                state,
                {
                    "request": request_state,
                    "failure": failure_state,
                    "result": result,
                },
            )
            await self.persistence.save_checkpoint(failed_state)
            await self.session.commit()
        except Exception as persistence_exc:
            await self.session.rollback()
            raise WorkflowPersistenceError(
                "Terminal workflow failure could not be persisted"
            ) from persistence_exc
