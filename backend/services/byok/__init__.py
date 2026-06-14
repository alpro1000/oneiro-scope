"""BYOK (Bring Your Own Key) — encrypted per-user LLM provider keys.

See Phase 6.E in docs/PLAN.md. Plaintext keys never touch the DB:
- `keys.encrypt(plaintext)` → Fernet ciphertext (stored in UserLLMKey).
- `keys.decrypt(ciphertext)` → plaintext (used only inside the request).
- `keys.hint(plaintext)` → "sk-...x9k2" for UI confirmation.
"""

from backend.services.byok.keys import decrypt, encrypt, hint

__all__ = ["encrypt", "decrypt", "hint"]
