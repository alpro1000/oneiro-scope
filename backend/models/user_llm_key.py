"""Encrypted per-user LLM provider keys (BYOK — Phase 6.E).

Stored as Fernet-encrypted blobs. The Fernet key is derived from
`settings.SECRET_KEY` so rotating the secret invalidates all stored
BYOK keys (users would need to re-enter them) — acceptable for the
threat model.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class UserLLMKey(Base):
    """One row per (user, provider) pair holding an encrypted API key."""

    __tablename__ = "user_llm_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider enum mirrors backend/core/llm_provider.py LLMProvider:
    # groq, gemini, vertex, together, openai, anthropic, bedrock.
    provider = Column(String(20), nullable=False)

    # Fernet ciphertext — opaque to the DB, decrypted only via byok.keys.
    encrypted_key = Column(String(2048), nullable=False)

    # Last-4 + first-4 for UI ("sk-...x9k2"); never stored as full plaintext.
    hint = Column(String(32), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="llm_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_llm_key_provider"),
    )

    def __repr__(self):
        return f"<UserLLMKey(user_id={self.user_id}, provider={self.provider})>"
