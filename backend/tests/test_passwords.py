"""Password hashing unit tests."""

from app.core.passwords import hash_password, needs_rehash, verify_password


def test_password_round_trip() -> None:
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)


def test_invalid_hash_does_not_verify() -> None:
    assert not verify_password("correct-horse-battery", "not-a-hash")
    assert needs_rehash("not-a-hash")
