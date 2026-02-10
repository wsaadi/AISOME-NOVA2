from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.consumption import ConsumptionResponse
from app.middleware.auth import require_permission
from app.services.consumption import get_consumption_data, get_consumption_summary
from app.models.user import User

router = APIRouter(prefix="/api/consumption", tags=["Consumption"])


@router.get("", response_model=list[ConsumptionResponse])
async def list_consumption(
    user_id: Optional[UUID] = Query(None),
    agent_id: Optional[UUID] = Query(None),
    provider_id: Optional[UUID] = Query(None),
    model_id: Optional[UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("consumption", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = await get_consumption_data(
        db, user_id=user_id, agent_id=agent_id, provider_id=provider_id,
        model_id=model_id, date_from=date_from, date_to=date_to, skip=skip, limit=limit,
    )
    return data


@router.get("/summary")
async def consumption_summary(
    group_by: str = Query("day", regex="^(user|agent|provider|model|day)$"),
    user_id: Optional[UUID] = Query(None),
    agent_id: Optional[UUID] = Query(None),
    provider_id: Optional[UUID] = Query(None),
    model_id: Optional[UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("consumption", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = await get_consumption_summary(
        db, group_by=group_by, user_id=user_id, agent_id=agent_id,
        provider_id=provider_id, model_id=model_id, date_from=date_from, date_to=date_to,
    )
    return [
        {
            "group_key": group_by,
            "group_value": str(row.group_value),
            "total_tokens_in": row.total_tokens_in or 0,
            "total_tokens_out": row.total_tokens_out or 0,
            "total_cost_in": float(row.total_cost_in or 0),
            "total_cost_out": float(row.total_cost_out or 0),
            "count": row.count,
        }
        for row in data
    ]
