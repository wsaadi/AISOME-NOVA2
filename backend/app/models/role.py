import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


DEFAULT_PERMISSIONS = {
    "users": {"read": False, "write": False, "delete": False},
    "roles": {"read": False, "write": False, "delete": False},
    "llm_config": {"read": False, "write": False},
    "consumption": {"read": False},
    "quotas": {"read": False, "write": False},
    "costs": {"read": False, "write": False},
    "moderation": {"read": False, "write": False},
    "agents": {"read": True, "write": False, "delete": False, "export": False, "import": False},
    "catalog_management": {"read": False, "write": False},
    "system": {"read": False, "update": False},
}


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    permissions = Column(JSONB, default=DEFAULT_PERMISSIONS)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", secondary="user_roles", back_populates="roles", lazy="selectin")
    agent_permissions = relationship("AgentPermission", back_populates="role", lazy="selectin")
