import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Consumption(Base):
    __tablename__ = "consumptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id", ondelete="SET NULL"), nullable=True)
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_in = Column(Float, nullable=False, default=0.0)
    cost_out = Column(Float, nullable=False, default=0.0)
    session_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="consumptions")
    agent = relationship("Agent", back_populates="consumptions")
    model = relationship("LLMModel", back_populates="consumptions")
