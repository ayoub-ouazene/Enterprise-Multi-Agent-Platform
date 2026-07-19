import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.requests.enums import RequestStatus
from app.workflow.nodes.collaboration import department_collaboration_node
from app.workflow.state import WorkflowState


def test_it_procurement_collaboration_preserves_request_and_owner() -> None:
    request_id = uuid4()
    owner_id = uuid4()
    state = WorkflowState.model_validate({
        "request": {
            "request_id": request_id, "company_id": uuid4(),
            "requester_user_id": uuid4(), "owner_department_id": owner_id,
            "active_department_id": owner_id, "request_type": "hardware_request",
            "status": "processing", "current_stage": "it_processing",
            "summary": "Find laptop suppliers",
        },
        "collaboration": {
            "request": DepartmentCollaborationRequest(
                request_id=request_id, sender_department=DepartmentType.IT,
                receiver_department=DepartmentType.PROCUREMENT,
                action="find_it_asset_suppliers", payload={}, expected_output={},
            ).model_dump(mode="json"),
            "is_active": True,
        },
    })
    result = {
        "request_id": str(request_id), "sender_department": "procurement",
        "receiver_department": "it", "action": "find_it_asset_suppliers",
        "status": "completed", "result": {"eligible_candidate_count": 2},
        "reason": "Shortlist returned.",
    }
    service = AsyncMock()
    service.execute_procurement_collaboration.return_value = type(
        "Result", (), {"model_dump": lambda self, **_: result}
    )()
    runtime = type("Runtime", (), {"context": type(
        "Context", (), {"department_execution_service": service}
    )()})()
    update = asyncio.run(department_collaboration_node(state, runtime))
    assert update["request"].request_id == request_id
    assert update["request"].owner_department_id == owner_id
    assert update["request"].status == RequestStatus.PROCESSING
    service.execute_procurement_collaboration.assert_awaited_once()
