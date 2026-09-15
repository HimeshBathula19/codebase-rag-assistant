from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from hashlib import sha256
from base64 import urlsafe_b64encode

from app.config import get_settings


def _fernet() -> Fernet:
    digest = sha256(get_settings().app_secret_key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
