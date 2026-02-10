from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.moderation import ModerationRule
from app.schemas.moderation import ModerationRuleCreate, ModerationRuleUpdate, ModerationRuleResponse
from app.middleware.auth import require_permission
from app.services.moderation import get_moderation_service
from app.models.user import User

router = APIRouter(prefix="/api/moderation", tags=["Moderation"])


@router.get("/rules", response_model=list[ModerationRuleResponse])
async def list_rules(
    agent_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_permission("moderation", "read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(ModerationRule)
    if agent_id:
        query = query.where(ModerationRule.agent_id == agent_id)
    result = await db.execute(query.order_by(ModerationRule.created_at.desc()))
    return result.scalars().all()


@router.post("/rules", response_model=ModerationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: ModerationRuleCreate,
    current_user: User = Depends(require_permission("moderation", "write")),
    db: AsyncSession = Depends(get_db),
):
    rule = ModerationRule(**rule_data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=ModerationRuleResponse)
async def update_rule(
    rule_id: UUID, rule_data: ModerationRuleUpdate,
    current_user: User = Depends(require_permission("moderation", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModerationRule).where(ModerationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    for key, value in rule_data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    current_user: User = Depends(require_permission("moderation", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModerationRule).where(ModerationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.delete(rule)
    await db.commit()


@router.post("/test")
async def test_moderation(
    text: str = Body(..., embed=True),
    entity_types: list[str] = Body(default=["person", "email", "phone", "address"]),
    current_user: User = Depends(require_permission("moderation", "read")),
):
    service = get_moderation_service()
    entities = service.detect_entities(text, entity_types)
    redacted = service.redact_text(text, entity_types)
    return {"original": text, "redacted": redacted, "entities": entities}
