from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.cost import ModelCost
from app.schemas.cost import ModelCostCreate, ModelCostUpdate, ModelCostResponse
from app.middleware.auth import require_permission
from app.models.user import User

router = APIRouter(prefix="/api/costs", tags=["Costs"])


@router.get("", response_model=list[ModelCostResponse])
async def list_costs(
    model_id: UUID = Query(None),
    current_user: User = Depends(require_permission("costs", "read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(ModelCost)
    if model_id:
        query = query.where(ModelCost.model_id == model_id)
    result = await db.execute(query.order_by(ModelCost.effective_date.desc()))
    return result.scalars().all()


@router.post("", response_model=ModelCostResponse, status_code=status.HTTP_201_CREATED)
async def create_cost(
    cost_data: ModelCostCreate,
    current_user: User = Depends(require_permission("costs", "write")),
    db: AsyncSession = Depends(get_db),
):
    cost = ModelCost(**cost_data.model_dump())
    db.add(cost)
    await db.commit()
    await db.refresh(cost)
    return cost


@router.put("/{cost_id}", response_model=ModelCostResponse)
async def update_cost(
    cost_id: UUID, cost_data: ModelCostUpdate,
    current_user: User = Depends(require_permission("costs", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelCost).where(ModelCost.id == cost_id))
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost entry not found")
    for key, value in cost_data.model_dump(exclude_unset=True).items():
        setattr(cost, key, value)
    await db.commit()
    await db.refresh(cost)
    return cost


@router.delete("/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost(
    cost_id: UUID,
    current_user: User = Depends(require_permission("costs", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelCost).where(ModelCost.id == cost_id))
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost entry not found")
    await db.delete(cost)
    await db.commit()
