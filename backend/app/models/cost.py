import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ModelCost(Base):
    __tablename__ = "model_costs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False)
    cost_per_token_in = Column(Float, nullable=False, default=0.0)
    cost_per_token_out = Column(Float, nullable=False, default=0.0)
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("LLMModel", back_populates="costs")
