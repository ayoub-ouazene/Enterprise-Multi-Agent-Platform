from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.requests.enums import RequestStatus
from app.workflow.collaboration.enums import CollaborationRuntimeStatus
from app.workflow.collaboration.exceptions import (
    CollaborationConflictError,
    CollaborationExecutionError,
    CollaborationLimitError,
    CollaborationRouteError,
    CollaborationValidationError,
)
from app.workflow.collaboration.idempotency import (
    build_collaboration_idempotency_key,
    collaboration_route_signature,
)
from app.workflow.collaboration.registry import (
    CollaborationDefinition,
    CollaborationRegistry,
    build_default_collaboration_registry,
)
from app.workflow.collaboration.schemas import (
    CollaborationCallState,
    CollaborationHistoryEntry,
    CollaborationReceiverOutcome,
)


class CollaborationExecutor(Protocol):
    async def execute_collaboration_receiver(
        self,
        state: Any,
        request: DepartmentCollaborationRequest,
    ) -> CollaborationReceiverOutcome: ...


class CollaborationService:
    def __init__(
        self,
        settings: Settings,
        executor: CollaborationExecutor,
        registry: CollaborationRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.executor = executor
        self.registry = registry or build_default_collaboration_registry()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _department_id(state: Any, departments: dict[DepartmentType, Any], department: DepartmentType):
        context = departments.get(department)
        if context is None or not context.is_active:
            raise CollaborationValidationError("The collaborating department is unavailable")
        return context.department_id

    @staticmethod
    def _active_type(state: Any, departments: dict[DepartmentType, Any]) -> DepartmentType:
        active_id = state.request.active_department_id
        for department_type, context in departments.items():
            if context.department_id == active_id and context.is_active:
                return department_type
        raise CollaborationValidationError("The active department is unavailable")

    def prepare(self, state: Any, departments: dict[DepartmentType, Any]) -> dict[str, Any]:
        try:
            request = DepartmentCollaborationRequest.model_validate(
                state.collaboration.request
            )
        except Exception as exc:
            raise CollaborationValidationError("Invalid collaboration request") from exc
        if request.request_id != state.request.request_id:
            raise CollaborationValidationError("Collaboration Request ID is invalid")
        definition, payload = self.registry.validate_request(request)
        active_type = self._active_type(state, departments)
        if active_type != request.sender_department:
            raise CollaborationValidationError(
                "Only the active department may request collaboration"
            )

        stack = list(state.collaboration.return_stack)
        parent = state.collaboration.active
        if parent is not None:
            if parent.status != CollaborationRuntimeStatus.RUNNING:
                raise CollaborationConflictError("Parent collaboration is not running")
            if parent.receiver_department != request.sender_department:
                raise CollaborationValidationError("Invalid nested collaboration sender")
            if not self.registry.resolve(
                parent.sender_department, parent.receiver_department, parent.action
            ).allow_nested:
                raise CollaborationRouteError("Nested collaboration is not permitted")
            stack.append(parent)
        elif state.request.owner_department_id != state.request.active_department_id:
            raise CollaborationValidationError(
                "Root collaboration must start from the owner department"
            )

        depth = len(stack) + 1
        if depth > self.settings.workflow_max_collaboration_depth:
            raise CollaborationLimitError("Collaboration depth limit reached")
        if state.collaboration.total_call_count >= self.settings.workflow_max_collaboration_calls:
            raise CollaborationLimitError("Collaboration call limit reached")
        active_path = [item.sender_department for item in stack]
        active_path.extend(item.receiver_department for item in stack)
        if request.receiver_department in active_path:
            raise CollaborationLimitError("Collaboration cycle detected")

        key = build_collaboration_idempotency_key(
            request_id=request.request_id,
            sender=request.sender_department,
            receiver=request.receiver_department,
            action=request.action,
            payload=payload,
        )
        signature = collaboration_route_signature(
            request.sender_department, request.receiver_department, request.action
        )
        if any(item.idempotency_key == key for item in stack):
            raise CollaborationConflictError("Collaboration is already running")
        completed = next(
            (
                item
                for item in reversed(state.collaboration.history)
                if item.idempotency_key == key
                and item.status == CollaborationRuntimeStatus.COMPLETED
            ),
            None,
        )
        if completed is not None:
            call = CollaborationCallState(
                collaboration_id=completed.collaboration_id,
                parent_collaboration_id=(parent.collaboration_id if parent else None),
                status=CollaborationRuntimeStatus.COMPLETED,
                request_id=request.request_id,
                sender_department=request.sender_department,
                receiver_department=request.receiver_department,
                action=request.action,
                payload=payload,
                expected_output=request.expected_output,
                result=completed.safe_result,
                started_at=completed.started_at,
                completed_at=completed.completed_at,
                attempt_count=completed.attempt_count,
                depth=depth,
                return_stage=state.request.current_stage,
                idempotency_key=key,
                route_signature=signature,
            )
            total_count = state.collaboration.total_call_count
        else:
            failed_previous = next(
                (
                    item
                    for item in reversed(state.collaboration.history)
                    if item.idempotency_key == key
                    and item.status == CollaborationRuntimeStatus.FAILED
                ),
                None,
            )
            repeats = sum(
                item.route_signature == signature for item in state.collaboration.history
            )
            if (
                failed_previous is None
                and repeats >= self.settings.workflow_max_collaboration_attempts
            ):
                raise CollaborationLimitError("Collaboration route repetition limit reached")
            if (
                failed_previous is not None
                and failed_previous.attempt_count
                >= self.settings.workflow_max_collaboration_attempts
            ):
                raise CollaborationLimitError("Collaboration attempt limit reached")
            call = CollaborationCallState(
                collaboration_id=(
                    failed_previous.collaboration_id if failed_previous else uuid4()
                ),
                parent_collaboration_id=(parent.collaboration_id if parent else None),
                status=CollaborationRuntimeStatus.PENDING,
                request_id=request.request_id,
                sender_department=request.sender_department,
                receiver_department=request.receiver_department,
                action=request.action,
                payload=payload,
                expected_output=request.expected_output,
                started_at=(failed_previous.started_at if failed_previous else self._now()),
                attempt_count=(failed_previous.attempt_count if failed_previous else 0),
                depth=depth,
                return_stage=state.request.current_stage,
                idempotency_key=key,
                route_signature=signature,
            )
            total_count = state.collaboration.total_call_count + (
                0 if failed_previous else 1
            )

        receiver_id = self._department_id(state, departments, request.receiver_department)
        return {
            "request": state.request.model_copy(
                update={
                    "active_department_id": receiver_id,
                    "status": RequestStatus.WAITING_FOR_DEPARTMENT,
                    "current_stage": f"collaboration_{request.receiver_department.value}_pending",
                }
            ),
            "collaboration": state.collaboration.model_copy(
                update={
                    "active": call,
                    "return_stack": stack,
                    "total_call_count": total_count,
                    "is_active": True,
                    "last_replayed": completed is not None,
                }
            ),
        }

    async def execute(self, state: Any) -> dict[str, Any]:
        call = state.collaboration.active
        if call is None:
            raise CollaborationExecutionError("No collaboration is active")
        if call.status == CollaborationRuntimeStatus.COMPLETED:
            return {}
        if call.attempt_count >= self.settings.workflow_max_collaboration_attempts:
            raise CollaborationLimitError("Collaboration attempt limit reached")
        running = call.model_copy(
            update={
                "status": CollaborationRuntimeStatus.RUNNING,
                "attempt_count": call.attempt_count + 1,
            }
        )
        request = DepartmentCollaborationRequest(
            request_id=running.request_id,
            sender_department=running.sender_department,
            receiver_department=running.receiver_department,
            action=running.action,
            payload=running.payload,
            expected_output=running.expected_output,
        )
        try:
            outcome = await self.executor.execute_collaboration_receiver(state, request)
        except Exception as exc:
            failed = running.model_copy(
                update={
                    "status": CollaborationRuntimeStatus.FAILED,
                    "error_safe": "The collaborating department could not complete its work.",
                }
            )
            return {
                "collaboration": state.collaboration.model_copy(
                    update={"active": failed, "last_replayed": False}
                )
            }

        if outcome.nested_request is not None:
            tool_results = outcome.continuation_data.get("tool_results")
            execution = state.execution
            if isinstance(tool_results, list):
                execution = execution.model_copy(update={"tool_results": tool_results})
            return {
                "execution": execution,
                "collaboration": state.collaboration.model_copy(
                    update={
                        "active": running,
                        "request": outcome.nested_request.model_dump(mode="json"),
                        "structured_result": {},
                        "last_replayed": False,
                    }
                )
            }
        if outcome.human_action is not None:
            return {
                "request": state.request.model_copy(
                    update={
                        "status": RequestStatus.WAITING_FOR_HUMAN_ACTION,
                        "current_stage": "collaboration_waiting_for_human_action",
                    }
                ),
                "human_action": state.human_action.model_copy(
                    update={
                        "required": True,
                        "request": outcome.human_action,
                        "status": "pending",
                    }
                ),
                "collaboration": state.collaboration.model_copy(
                    update={"active": running, "last_replayed": False}
                ),
            }
        definition = self.registry.resolve(
            running.sender_department, running.receiver_department, running.action
        )
        try:
            validated = definition.validate_result(outcome.result or {})
        except Exception:
            failed = running.model_copy(
                update={
                    "status": CollaborationRuntimeStatus.FAILED,
                    "error_safe": "The collaborating department returned an invalid result.",
                }
            )
            return {
                "collaboration": state.collaboration.model_copy(
                    update={"active": failed, "last_replayed": False}
                )
            }
        completed = running.model_copy(
            update={
                "status": CollaborationRuntimeStatus.COMPLETED,
                "result": validated,
                "completed_at": self._now(),
                "error_safe": None,
            }
        )
        return {
            "collaboration": state.collaboration.model_copy(
                update={"active": completed, "last_replayed": False}
            )
        }

    def finish(self, state: Any, departments: dict[DepartmentType, Any]) -> dict[str, Any]:
        call = state.collaboration.active
        if call is None or call.status not in {
            CollaborationRuntimeStatus.COMPLETED,
            CollaborationRuntimeStatus.FAILED,
        }:
            raise CollaborationConflictError("Collaboration is not ready to return")
        summary = (
            "The collaborating department returned a validated result."
            if call.status == CollaborationRuntimeStatus.COMPLETED
            else call.error_safe or "The collaborating department could not complete its work."
        )
        history_entry = CollaborationHistoryEntry(
            collaboration_id=call.collaboration_id,
            parent_collaboration_id=call.parent_collaboration_id,
            sender_department=call.sender_department,
            receiver_department=call.receiver_department,
            action=call.action,
            status=call.status,
            idempotency_key=call.idempotency_key,
            route_signature=call.route_signature,
            depth=call.depth,
            attempt_count=call.attempt_count,
            started_at=call.started_at,
            completed_at=call.completed_at or self._now(),
            safe_summary=summary,
            safe_result=call.result,
        )
        history = list(state.collaboration.history)
        if not state.collaboration.last_replayed:
            history.append(history_entry)
        history = history[-self.settings.workflow_max_collaboration_calls :]
        stack = list(state.collaboration.return_stack)
        parent = stack.pop() if stack else None
        target = parent.receiver_department if parent else call.sender_department
        target_id = self._department_id(state, departments, target)
        result_envelope = {
            "request_id": str(call.request_id),
            "sender_department": call.receiver_department.value,
            "receiver_department": call.sender_department.value,
            "action": call.action,
            "status": "completed" if call.status == CollaborationRuntimeStatus.COMPLETED else "failed",
            "result": call.result,
            "reason": summary,
        }
        return {
            "request": state.request.model_copy(
                update={
                    "active_department_id": target_id,
                    "status": RequestStatus.PROCESSING,
                    "current_stage": parent.return_stage if parent else call.return_stage,
                }
            ),
            "collaboration": state.collaboration.model_copy(
                update={
                    "active": parent,
                    "return_stack": stack,
                    "history": history,
                    "structured_result": result_envelope,
                    "request": {},
                    "is_active": parent is not None,
                    "last_replayed": state.collaboration.last_replayed,
                }
            ),
            "execution": state.execution.model_copy(update={"department_result": {}}),
        }
