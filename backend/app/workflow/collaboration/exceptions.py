class CollaborationError(Exception):
    """Base error with no confidential context in its message."""


class CollaborationValidationError(CollaborationError):
    pass


class CollaborationRouteError(CollaborationValidationError):
    pass


class CollaborationLimitError(CollaborationValidationError):
    pass


class CollaborationConflictError(CollaborationError):
    pass


class CollaborationExecutionError(CollaborationError):
    pass
