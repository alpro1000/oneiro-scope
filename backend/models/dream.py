"""Dream and Dream Analysis models"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class Dream(Base):
    """Dream model - stores user's dream reports"""

    __tablename__ = "dreams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Dream content
    text = Column(Text, nullable=False)
    language = Column(String(5), nullable=False)  # en, ru

    # Source tracking
    source = Column(String(20), nullable=True)  # web, mobile, telegram, voice
    audio_url = Column(Text, nullable=True)  # S3/storage URL if from voice

    # Metadata
    dream_date = Column(DateTime(timezone=True), nullable=True)  # When dream occurred
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="dreams")
    analysis = relationship("DreamAnalysis", back_populates="dream", uselist=False, cascade="all, delete-orphan")
    embedding = relationship("DreamEmbedding", back_populates="dream", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Dream(id={self.id}, user_id={self.user_id})>"


class DreamAnalysis(Base):
    """Dream Analysis model - stores LLM analysis results"""

    __tablename__ = "dream_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dream_id = Column(UUID(as_uuid=True), ForeignKey("dreams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Analysis content
    interpretation = Column(Text, nullable=False)
    archetypes = Column(JSON, nullable=True)  # List of symbols/archetypes
    mood = Column(String(20), nullable=True)  # positive, negative, neutral

    # Lunar context
    lunar_day = Column(Integer, nullable=True)  # 1-30
    lunar_effect = Column(String(20), nullable=True)  # diagnostic, warning, positive, neutral

    # Quality metrics
    confidence = Column(Float, nullable=False)
    sources = Column(JSON, nullable=True)  # List of knowledge sources used

    # Model metadata
    model_used = Column(String(50), nullable=True)  # gpt-4o-mini, claude-3-haiku, etc.
    tokens_used = Column(JSON, nullable=True)  # {input: int, output: int}
    latency_ms = Column(Integer, nullable=True)

    # Flags
    requires_human_review = Column(Boolean, default=False, nullable=False)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    dream = relationship("Dream", back_populates="analysis")

    def __repr__(self):
        return f"<DreamAnalysis(id={self.id}, dream_id={self.dream_id}, confidence={self.confidence})>"


class DreamEmbedding(Base):
    """Dream embeddings for vector similarity search"""

    __tablename__ = "dream_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dream_id = Column(UUID(as_uuid=True), ForeignKey("dreams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    # Note: pgvector extension required
    # embedding = Column(Vector(1536), nullable=False)
    # Placeholder for now - will be added in migration with pgvector

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    dream = relationship("Dream", back_populates="embedding")

    def __repr__(self):
        return f"<DreamEmbedding(id={self.id}, dream_id={self.dream_id})>"
