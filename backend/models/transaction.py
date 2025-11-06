"""Transaction model"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class Transaction(Base):
    """Payment transaction model"""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Idempotency
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)

    # Transaction details
    type = Column(String(20), nullable=False)  # one_time, subscription, refund
    status = Column(String(20), nullable=False)  # pending, succeeded, failed, refunded

    # Amount
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)  # USD, RUB, EUR

    # Payment gateway
    gateway = Column(String(20), nullable=False)  # stripe, yookassa
    gateway_transaction_id = Column(String(255), nullable=True, index=True)
    gateway_customer_id = Column(String(255), nullable=True)

    # Description
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default={}, nullable=False)

    # Dreams purchased
    dreams_purchased = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, status={self.status}, amount={self.amount_cents/100:.2f} {self.currency})>"
