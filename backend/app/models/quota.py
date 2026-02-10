import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Quota(Base):
    __tablename__ = "quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(String(50), nullable=False)  # user, role, agent, provider
    target_id = Column(UUID(as_uuid=True), nullable=False)
    quota_type = Column(String(50), nullable=False)  # token, financial
    period = Column(String(50), nullable=False)  # day, week, month, year
    limit_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
