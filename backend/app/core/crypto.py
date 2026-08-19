"""Authenticated encryption for OAuth tokens at rest.

Uses Fernet (AES-128-CBC + HMAC). ENCRYPTION_KEY is a Fernet key, not SECRET_KEY.
Never log plaintext or ciphertext of tokens.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError


class EncryptionUnavailableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("ENCRYPTION_UNAVAILABLE", message, status_code=501)


def fernet_from_key(encryption_key: str) -> Fernet:
    if not encryption_key.strip():
        raise EncryptionUnavailableError(
            "ENCRYPTION_KEY is not set. Strava tokens cannot be stored until it is."
        )
    try:
        return Fernet(encryption_key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise EncryptionUnavailableError(
            "ENCRYPTION_KEY is not a valid Fernet key. Generate one with "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        ) from exc


def encrypt_secret(encryption_key: str, plaintext: str) -> str:
    token = fernet_from_key(encryption_key).encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(encryption_key: str, ciphertext: str) -> str:
    try:
        return fernet_from_key(encryption_key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionUnavailableError(
            "Stored Strava tokens could not be decrypted. "
            "Reconnect Strava after checking ENCRYPTION_KEY."
        ) from exc
