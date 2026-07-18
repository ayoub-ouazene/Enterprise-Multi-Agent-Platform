class WorkflowError(Exception):
    """Base exception for workflow-control failures."""


class WorkflowPermissionError(WorkflowError):
    """Raised when an actor cannot control a workflow."""


class WorkflowConflictError(WorkflowError):
    """Raised when workflow state conflicts with the requested operation."""


class WorkflowAlreadyStartedError(WorkflowConflictError):
    """Raised when a workflow start marker already exists."""


class WorkflowTerminalError(WorkflowConflictError):
    """Raised when a terminal workflow is started or resumed."""


class WorkflowNotStartedError(WorkflowConflictError):
    """Raised when resume is requested before workflow start."""


class WorkflowClarificationAnswerRequiredError(WorkflowConflictError):
    """Raised when a paused Router workflow is resumed without an answer."""


class InvalidWorkflowStateError(WorkflowConflictError):
    """Raised when persisted workflow state is malformed or inconsistent."""


class UnsupportedWorkflowStateVersionError(InvalidWorkflowStateError):
    """Raised when persisted state uses an unsupported schema version."""


class PlaceholderRouteUnavailableError(WorkflowConflictError):
    """Raised when Step 9 has no controlled deterministic route."""


class RouterDepartmentUnavailableError(WorkflowError):
    """Raised when a selected tenant department is absent or inactive."""


class RouterOwnerConflictError(WorkflowError):
    """Raised when routing attempts to replace an established owner."""


class WorkflowPersistenceError(WorkflowError):
    """Raised when a workflow checkpoint cannot be persisted."""


class WorkflowExecutionFailedError(WorkflowError):
    """Raised after a graph failure has been recorded safely."""


class InactiveWorkflowNodeError(WorkflowError):
    """Raised if an intentionally inactive future node is invoked."""
