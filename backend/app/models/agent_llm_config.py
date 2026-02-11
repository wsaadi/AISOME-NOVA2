import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AgentLLMConfig(Base):
    """Per-agent LLM provider/model configuration.

    Maps an agent slug to a specific LLM provider and model.
    When set, the agent will use this provider/model instead of the platform default.
    """
    __tablename__ = "agent_llm_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_slug = Column(String(200), unique=True, nullable=False, index=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("LLMProvider", lazy="selectin")
    model = relationship("LLMModel", lazy="selectin")
