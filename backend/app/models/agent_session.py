import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    session_id = Column(String(255), primary_key=True)
    agent_slug = Column(String(200), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=True, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "AgentSessionMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AgentSessionMessage(Base):
    __tablename__ = "agent_session_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(255),
        ForeignKey("agent_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False, default="")
    attachments = Column(Text, nullable=True, default="[]")
    metadata = Column(Text, nullable=True, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    session = relationship("AgentSession", back_populates="messages")
