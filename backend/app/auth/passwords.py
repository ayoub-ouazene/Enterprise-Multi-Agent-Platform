from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash(
    "dummy-password-used-only-to-equalize-authentication-work"
)


class InvalidPasswordError(ValueError):
    """Raised when a new password does not meet the minimum safety rules."""


def validate_new_password(password: str) -> None:
    if not password or not password.strip():
        raise InvalidPasswordError("Password must not be empty")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain at least {MIN_PASSWORD_LENGTH} characters"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain at most {MAX_PASSWORD_LENGTH} characters"
        )


def hash_password(password: str) -> str:
    validate_new_password(password)
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password or not password.strip() or len(password) > MAX_PASSWORD_LENGTH:
        return False
    encoded_hash = password_hash or DUMMY_PASSWORD_HASH
    try:
        return password_hasher.verify(password, encoded_hash)
    except (UnknownHashError, ValueError):
        return False
