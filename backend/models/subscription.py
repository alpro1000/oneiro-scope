"""Subscription model"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class Subscription(Base):
    """User subscription model"""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Subscription details
    # tier: free / premium / pro — drives quota enforcement.
    tier = Column(String(20), default="free", nullable=False)
    # plan_id: lemon variant id, or legacy monthly/annual.
    plan_id = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # active, canceled, past_due, expired

    # Billing period
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)

    # Provider (Phase 6 pivot — Lemon Squeezy as MoR; stripe/yookassa kept
    # for legacy rows only, not used for new subscriptions).
    provider = Column(String(20), default="lemon", nullable=False)

    # Lemon Squeezy IDs (primary going forward).
    lemon_subscription_id = Column(String(255), nullable=True, index=True)
    lemon_variant_id = Column(String(255), nullable=True)
    lemon_customer_id = Column(String(255), nullable=True, index=True)

    # Legacy gateway IDs — kept nullable for historical rows.
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    yookassa_subscription_id = Column(String(255), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # The old check-one-gateway constraint is dropped: Lemon-only new rows
    # would violate it. Provider field carries the source of truth.

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan_id}, status={self.status})>"
