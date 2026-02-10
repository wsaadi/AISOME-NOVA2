from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class QuotaCreate(BaseModel):
    target_type: str  # user, role, agent, provider
    target_id: UUID
    quota_type: str  # token, financial
    period: str  # day, week, month, year
    limit_value: float
    is_active: bool = True


class QuotaUpdate(BaseModel):
    quota_type: Optional[str] = None
    period: Optional[str] = None
    limit_value: Optional[float] = None
    is_active: Optional[bool] = None


class QuotaResponse(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    quota_type: str
    period: str
    limit_value: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaUsage(BaseModel):
    quota: QuotaResponse
    current_usage: float
    percentage_used: float
    remaining: float
