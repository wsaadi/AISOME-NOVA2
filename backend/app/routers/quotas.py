from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.quota import Quota
from app.schemas.quota import QuotaCreate, QuotaUpdate, QuotaResponse, QuotaUsage
from app.middleware.auth import require_permission
from app.services.consumption import check_quota
from app.models.user import User

router = APIRouter(prefix="/api/quotas", tags=["Quotas"])


@router.get("", response_model=list[QuotaResponse])
async def list_quotas(
    target_type: str = Query(None),
    target_id: UUID = Query(None),
    current_user: User = Depends(require_permission("quotas", "read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Quota)
    if target_type:
        query = query.where(Quota.target_type == target_type)
    if target_id:
        query = query.where(Quota.target_id == target_id)
    result = await db.execute(query.order_by(Quota.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=QuotaResponse, status_code=status.HTTP_201_CREATED)
async def create_quota(
    quota_data: QuotaCreate,
    current_user: User = Depends(require_permission("quotas", "write")),
    db: AsyncSession = Depends(get_db),
):
    quota = Quota(**quota_data.model_dump())
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return quota


@router.put("/{quota_id}", response_model=QuotaResponse)
async def update_quota(
    quota_id: UUID, quota_data: QuotaUpdate,
    current_user: User = Depends(require_permission("quotas", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quota).where(Quota.id == quota_id))
    quota = result.scalar_one_or_none()
    if not quota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quota not found")
    for key, value in quota_data.model_dump(exclude_unset=True).items():
        setattr(quota, key, value)
    await db.commit()
    await db.refresh(quota)
    return quota


@router.delete("/{quota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quota(
    quota_id: UUID,
    current_user: User = Depends(require_permission("quotas", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quota).where(Quota.id == quota_id))
    quota = result.scalar_one_or_none()
    if not quota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quota not found")
    await db.delete(quota)
    await db.commit()


@router.get("/usage/{target_type}/{target_id}")
async def get_quota_usage(
    target_type: str, target_id: UUID,
    current_user: User = Depends(require_permission("quotas", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Quota).where(Quota.target_type == target_type, Quota.target_id == target_id)
    )
    quotas = result.scalars().all()
    usage_list = []
    for quota in quotas:
        check = await check_quota(db, target_type, target_id)
        usage_list.append({"quota": QuotaResponse.model_validate(quota), "allowed": check["allowed"]})
    return usage_list
