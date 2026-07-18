import re


DEFAULT_SAFE_FAILURE_MESSAGE = (
    "We could not complete this request because an unexpected problem occurred."
)

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)(password|secret|api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*\S+"
    ),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@[^\s]+"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
)

_UNSAFE_PUBLIC_PATTERNS = (
    re.compile(r"(?i)traceback|stack trace|sqlalchemy|asyncpg|psycopg"),
    re.compile(
        r"(?i)\b(select|insert|update|delete|alter|drop)\s+.+\b(from|into|table|set)\b"
    ),
    re.compile(r"(?i)\b(postgresql|postgres|mysql|redis|mongodb)://"),
    re.compile(r"[A-Za-z]:\\[^\s]+|/(?:home|var|etc|usr)/[^\s]+"),
)


def sanitize_internal_message(value: str) -> str:
    sanitized = value.strip()
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized or "No diagnostic message was provided."


def sanitize_safe_message(value: str) -> str:
    candidate = sanitize_internal_message(value)
    if "[REDACTED]" in candidate or any(
        pattern.search(candidate) for pattern in _UNSAFE_PUBLIC_PATTERNS
    ):
        return DEFAULT_SAFE_FAILURE_MESSAGE
    return candidate
