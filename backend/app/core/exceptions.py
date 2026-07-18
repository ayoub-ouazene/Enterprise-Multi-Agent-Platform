class DomainError(Exception):
    """Base exception for expected domain-layer failures."""


class NotFoundError(DomainError):
    """Raised when an entity is absent or outside the active tenant."""


class ConflictError(DomainError):
    """Raised when a business or uniqueness constraint would be violated."""


class BusinessValidationError(DomainError):
    """Raised when an operation violates a domain rule."""
