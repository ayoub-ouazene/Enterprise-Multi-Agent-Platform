from typing import NoReturn

from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def inactive_tool_node(_: WorkflowState) -> NoReturn:
    raise InactiveWorkflowNodeError("Department tools are not active in Step 11")
