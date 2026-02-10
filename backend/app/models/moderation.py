import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class ModerationRule(Base):
    __tablename__ = "moderation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True)
    rule_type = Column(String(100), nullable=False)  # anonymization, content_filter, pii_detection
    config = Column(JSONB, default={})
    entity_types = Column(JSONB, default=[])  # GLiNER entity types to detect
    action = Column(String(50), default="redact")  # redact, block, flag, replace
    replacement_template = Column(String(200), nullable=True, default="[REDACTED]")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="moderation_rules")
