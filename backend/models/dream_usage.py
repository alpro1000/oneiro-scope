"""Dream usage tracking model"""

from sqlalchemy import Column, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class DreamUsage(Base):
    """Track dream credit usage"""

    __tablename__ = "dream_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dream_id = Column(UUID(as_uuid=True), nullable=False)

    # Usage type
    used_free_tier = Column(Boolean, default=False, nullable=False)
    used_subscription = Column(Boolean, default=False, nullable=False)

    # References
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True, index=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="dream_usages")
    subscription = relationship("Subscription")
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<DreamUsage(id={self.id}, user_id={self.user_id}, dream_id={self.dream_id})>"
