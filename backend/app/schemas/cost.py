from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class ModelCostCreate(BaseModel):
    model_id: UUID
    cost_per_token_in: float
    cost_per_token_out: float
    effective_date: date


class ModelCostUpdate(BaseModel):
    cost_per_token_in: Optional[float] = None
    cost_per_token_out: Optional[float] = None
    effective_date: Optional[date] = None


class ModelCostResponse(BaseModel):
    id: UUID
    model_id: UUID
    cost_per_token_in: float
    cost_per_token_out: float
    effective_date: date
    created_at: datetime

    class Config:
        from_attributes = True
