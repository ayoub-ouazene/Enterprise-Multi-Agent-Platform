class KnowledgeError(Exception):
    """Base class for safe knowledge-domain failures."""


class KnowledgePermissionError(KnowledgeError):
    pass


class KnowledgeValidationError(KnowledgeError):
    pass


class KnowledgeConflictError(KnowledgeError):
    pass


class KnowledgeNotFoundError(KnowledgeError):
    pass


class KnowledgeProviderError(KnowledgeError):
    pass


class KnowledgeExtractionError(KnowledgeError):
    pass
