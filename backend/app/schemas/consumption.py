from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ConsumptionCreate(BaseModel):
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_in: float = 0.0
    cost_out: float = 0.0
    session_id: Optional[str] = None


class ConsumptionResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    agent_id: Optional[UUID]
    provider_id: Optional[UUID]
    model_id: Optional[UUID]
    tokens_in: int
    tokens_out: int
    cost_in: float
    cost_out: float
    session_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConsumptionFilter(BaseModel):
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    group_by: Optional[str] = None  # user, agent, provider, model, day, week, month


class ConsumptionSummary(BaseModel):
    group_key: str
    group_value: str
    total_tokens_in: int
    total_tokens_out: int
    total_cost_in: float
    total_cost_out: float
    count: int
