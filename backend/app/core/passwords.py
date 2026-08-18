"""Argon2id password hashing.

Never log passwords or password hashes.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Argon2id is the PasswordHasher default. Parameters can be tightened later;
# login will rehash if the stored hash is out of date.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError):
        return True


def dummy_password_hash() -> str:
    """Valid Argon2id hash used to keep login timing similar when the user is unknown."""
    return hash_password("x" * 16)
