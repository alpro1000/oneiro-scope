"""User model"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)

    # Email + password auth (Phase 6.A). Nullable so existing telegram-only
    # users keep working; web users authenticate via email + password.
    password_hash = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)

    # Connector identity (Phase 6, chart-core gate). The MCP surface
    # authenticates via an EXTERNAL OAuth authorization server, so its
    # principal is an opaque `sub` string, not this row's UUID. A connector
    # user is a User keyed on that subject: free tier, one chart, tracked
    # durably here. Nullable + unique so web (email) and connector (subject)
    # accounts coexist as distinct rows until a future account-merge links
    # them. Never overlaps a password account — the two identity spaces are
    # separate providers.
    oauth_subject = Column(String(255), unique=True, nullable=True, index=True)

    # Lemon Squeezy customer id — assigned on first successful checkout.
    lemon_customer_id = Column(String(255), nullable=True, index=True)

    # User preferences (extended to 5 locales — Phase 6.F).
    # Stored as 2-letter ISO 639-1 code: ru/en/de/es/fr.
    language = Column(String(5), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Freemium model
    free_dream_used = Column(Boolean, default=False, nullable=False)
    free_natal_used = Column(Boolean, default=False, nullable=False)
    # Which natal chart the free grant was spent on — the birth-instant
    # identity from `chart_core.chart_identity`. Re-issuing THIS chart stays
    # free forever (the account owns it); a different chart is what the flag
    # above refuses. Null until the first chart is issued.
    free_natal_chart_key = Column(String(128), nullable=True)
    dream_balance = Column(Integer, default=0, nullable=False)  # Prepaid dreams

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # GDPR: pending hard-delete (soft-delete + cron purge after 30 days).
    pending_deletion_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dreams = relationship("Dream", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    dream_usages = relationship("DreamUsage", back_populates="user", cascade="all, delete-orphan")
    llm_keys = relationship("UserLLMKey", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
