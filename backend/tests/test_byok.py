"""BYOK encryption tests (Phase 6.E)."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _reset_fernet_cache(monkeypatch):
    """Force re-derivation of the Fernet key per test using a known SECRET_KEY."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-do-not-use-in-prod-32-chars-long")
    from backend.services.byok import keys

    keys._fernet.cache_clear()
    from backend.core import config as _cfg

    _cfg.settings.SECRET_KEY = os.environ["SECRET_KEY"]
    yield
    keys._fernet.cache_clear()


def test_encrypt_then_decrypt_round_trips():
    from backend.services.byok import decrypt, encrypt

    plaintext = "sk-ant-api03-test-1234567890abcdef"
    ciphertext = encrypt(plaintext)
    assert ciphertext != plaintext
    assert decrypt(ciphertext) == plaintext


def test_encrypt_empty_raises():
    from backend.services.byok import encrypt

    with pytest.raises(ValueError):
        encrypt("")


def test_decrypt_tampered_raises():
    from cryptography.fernet import InvalidToken

    from backend.services.byok import decrypt, encrypt

    ciphertext = encrypt("real-key")
    bad = ciphertext[:-4] + "AAAA"
    with pytest.raises(InvalidToken):
        decrypt(bad)


def test_hint_short_key_is_redacted():
    from backend.services.byok import hint

    assert hint("abc") == "ab***"


def test_hint_full_key_first4_last4():
    from backend.services.byok import hint

    assert hint("sk-anthropic-xxxxxxxxYZ12") == "sk-a...YZ12"


def test_secret_rotation_invalidates_old_ciphertext(monkeypatch):
    """Changing SECRET_KEY must make old ciphertext undecryptable."""
    from cryptography.fernet import InvalidToken

    from backend.services.byok import decrypt, encrypt, keys

    ct = encrypt("key-1")
    # Rotate.
    monkeypatch.setenv("SECRET_KEY", "rotated-secret-different-from-the-first-one")
    from backend.core import config as _cfg

    _cfg.settings.SECRET_KEY = os.environ["SECRET_KEY"]
    keys._fernet.cache_clear()

    with pytest.raises(InvalidToken):
        decrypt(ct)
