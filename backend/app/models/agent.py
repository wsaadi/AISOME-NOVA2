import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AgentPermission(Base):
    __tablename__ = "agent_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    agent = relationship("Agent", back_populates="permissions")
    role = relationship("Role", back_populates="agent_permissions")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0.0")
    agent_type = Column(String(100), nullable=False, default="conversational")
    config = Column(JSONB, default={})
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    permissions = relationship("AgentPermission", back_populates="agent", lazy="selectin", cascade="all, delete-orphan")
    consumptions = relationship("Consumption", back_populates="agent", lazy="selectin")
    moderation_rules = relationship("ModerationRule", back_populates="agent", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by])
