class DepartmentExecutionError(Exception):
    """Base error for safe department execution failures."""


class DuplicateDepartmentRegistrationError(DepartmentExecutionError):
    """Raised when two implementations claim the same department type."""


class DepartmentImplementationNotFoundError(DepartmentExecutionError):
    """Raised when no implementation is registered for a supported department."""


class DepartmentContextMismatchError(DepartmentExecutionError):
    """Raised when trusted department context is internally inconsistent."""


class DepartmentResultValidationError(DepartmentExecutionError):
    """Raised when a department returns malformed or contradictory output."""


class DepartmentStateUpdateError(DepartmentExecutionError):
    """Raised when a department attempts a prohibited workflow-state update."""
