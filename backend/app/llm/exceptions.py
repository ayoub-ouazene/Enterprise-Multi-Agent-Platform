class RouterClientError(Exception):
    """Safe base exception for Router-provider failures."""


class RouterConfigurationError(RouterClientError):
    """Raised when Router functionality is not configured."""


class RouterProviderError(RouterClientError):
    """Raised for sanitized Groq provider failures."""


class RouterOutputError(RouterClientError):
    """Raised when model output remains invalid after correction."""
