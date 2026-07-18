import pytest

from app.auth.passwords import (
    InvalidPasswordError,
    hash_password,
    verify_password,
)


VALID_PASSWORD = "correct horse battery staple"


def test_password_hash_does_not_return_original_password() -> None:
    encoded = hash_password(VALID_PASSWORD)

    assert encoded != VALID_PASSWORD
    assert encoded.startswith("$argon2id$")


def test_correct_password_verifies() -> None:
    encoded = hash_password(VALID_PASSWORD)

    assert verify_password(VALID_PASSWORD, encoded) is True


def test_incorrect_password_is_rejected() -> None:
    encoded = hash_password(VALID_PASSWORD)

    assert verify_password("different password", encoded) is False


@pytest.mark.parametrize("password", ["", "   ", "too-short"])
def test_empty_or_invalid_new_password_is_rejected(password: str) -> None:
    with pytest.raises(InvalidPasswordError):
        hash_password(password)
