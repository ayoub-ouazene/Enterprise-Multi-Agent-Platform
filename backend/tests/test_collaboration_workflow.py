from app.requests.enums import RequestStatus
from app.workflow.collaboration.enums import CollaborationRuntimeStatus
from app.workflow.routing import route_next_skeleton_node

from tests.test_collaboration_service import initial_state, settings, Executor
from app.workflow.collaboration.service import CollaborationService
from app.workflow.state import apply_state_update


def test_restart_routes_pending_call_to_receiver_and_completed_call_to_return() -> None:
    state, departments = initial_state()
    service = CollaborationService(settings(), Executor())
    state = apply_state_update(state, service.prepare(state, departments))
    assert route_next_skeleton_node(state) == "collaboration_receiver"
    state.collaboration.active = state.collaboration.active.model_copy(
        update={"status": CollaborationRuntimeStatus.COMPLETED,
                "result": {"diagnosis_status": "done"}}
    )
    assert route_next_skeleton_node(state) == "collaboration_return"


def test_human_pause_ends_until_authorized_runtime_resumes_it() -> None:
    state, _ = initial_state()
    state.request.status = RequestStatus.WAITING_FOR_HUMAN_ACTION
    state.human_action.required = True
    assert route_next_skeleton_node(state) == "__end__"
