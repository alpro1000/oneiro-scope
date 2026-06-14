"""Fernet encryption for per-user BYOK LLM keys.

The Fernet key is derived deterministically from `settings.SECRET_KEY`
via SHA-256 → urlsafe_b64encode (Fernet requires a 32-byte base64 key).
That means rotating SECRET_KEY invalidates all stored BYOK keys — an
intentional security property (forces users to re-enter on rotation).

This module is import-light: cryptography is the only dependency.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Derive the Fernet key from SECRET_KEY (cached)."""
    secret = settings.SECRET_KEY or ""
    if not secret:
        raise RuntimeError(
            "settings.SECRET_KEY is empty — BYOK encryption refuses to "
            "operate without a real secret. Set SECRET_KEY in env."
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext LLM key. Returns the Fernet token as utf-8."""
    if not plaintext:
        raise ValueError("Cannot encrypt empty key")
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token. Raises InvalidToken on tamper or rotation."""
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("BYOK decrypt failed — secret rotated or tampered")
        raise


def hint(plaintext: str) -> str:
    """Return a 'sk-foo...bar9' preview safe to show in the UI."""
    if not plaintext:
        return ""
    if len(plaintext) <= 10:
        return plaintext[:2] + "***"
    return f"{plaintext[:4]}...{plaintext[-4:]}"
