import logging

from app.auth.passwords import hash_password, validate_new_password, InvalidPasswordError

logger = logging.getLogger(__name__)


def safe_hash_temporary_password(password: str) -> str:
    """Hash a temporary password without logging it.

    Raises InvalidPasswordError if the password does not meet minimum rules.
    """
    try:
        return hash_password(password)
    except InvalidPasswordError:
        raise
    except Exception:
        logger.exception("Password hashing failed")
        raise


def validate_password_strength(password: str) -> list[str]:
    """Validate a password and return a list of human-readable errors."""
    errors: list[str] = []
    try:
        validate_new_password(password)
    except InvalidPasswordError as exc:
        errors.append(str(exc))
    return errors


def sanitize_error_for_response(raw_error: str) -> str:
    """Remove any potentially sensitive data from error messages."""
    # Defensive: strip any mention of passwords from external errors
    lowered = raw_error.lower()
    if "password" in lowered:
        # Replace specific password values without exposing them
        return "Password validation failed"
    return raw_error
