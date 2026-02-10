from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.agent import Agent, AgentPermission
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.middleware.auth import get_current_user, require_permission
from app.services.rbac import get_accessible_agent_ids
from app.services.agent_manager import get_agent_manager

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_ids = await get_accessible_agent_ids(db, current_user)
    query = select(Agent).options(selectinload(Agent.permissions)).where(Agent.is_active == True)
    if accessible_ids is not None:
        query = query.where(Agent.id.in_(accessible_ids))
    result = await db.execute(query.order_by(Agent.name))
    agents = result.scalars().all()
    return [
        AgentResponse(
            id=a.id, name=a.name, slug=a.slug, description=a.description,
            version=a.version, agent_type=a.agent_type, config=a.config,
            system_prompt=a.system_prompt, is_active=a.is_active,
            created_by=a.created_by, created_at=a.created_at, updated_at=a.updated_at,
            permissions=[{"id": str(p.id), "role_id": str(p.role_id)} for p in a.permissions],
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).options(selectinload(Agent.permissions)).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse(
        id=agent.id, name=agent.name, slug=agent.slug, description=agent.description,
        version=agent.version, agent_type=agent.agent_type, config=agent.config,
        system_prompt=agent.system_prompt, is_active=agent.is_active,
        created_by=agent.created_by, created_at=agent.created_at, updated_at=agent.updated_at,
        permissions=[{"id": str(p.id), "role_id": str(p.role_id)} for p in agent.permissions],
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(require_permission("agents", "write")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Agent).where(Agent.slug == agent_data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent slug already exists")
    agent = Agent(
        name=agent_data.name, slug=agent_data.slug, description=agent_data.description,
        version=agent_data.version, agent_type=agent_data.agent_type, config=agent_data.config,
        system_prompt=agent_data.system_prompt, is_active=agent_data.is_active,
        created_by=current_user.id,
    )
    db.add(agent)
    await db.flush()
    for role_id in (agent_data.role_ids or []):
        db.add(AgentPermission(agent_id=agent.id, role_id=role_id))
    await db.commit()
    await db.refresh(agent)
    return AgentResponse(
        id=agent.id, name=agent.name, slug=agent.slug, description=agent.description,
        version=agent.version, agent_type=agent.agent_type, config=agent.config,
        system_prompt=agent.system_prompt, is_active=agent.is_active,
        created_by=agent.created_by, created_at=agent.created_at, updated_at=agent.updated_at,
        permissions=[],
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID, agent_data: AgentUpdate,
    current_user: User = Depends(require_permission("agents", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    update_data = agent_data.model_dump(exclude_unset=True)
    role_ids = update_data.pop("role_ids", None)
    for key, value in update_data.items():
        setattr(agent, key, value)
    if role_ids is not None:
        await db.execute(AgentPermission.__table__.delete().where(AgentPermission.agent_id == agent_id))
        for role_id in role_ids:
            db.add(AgentPermission(agent_id=agent.id, role_id=role_id))
    await db.commit()
    await db.refresh(agent)
    return AgentResponse(
        id=agent.id, name=agent.name, slug=agent.slug, description=agent.description,
        version=agent.version, agent_type=agent.agent_type, config=agent.config,
        system_prompt=agent.system_prompt, is_active=agent.is_active,
        created_by=agent.created_by, created_at=agent.created_at, updated_at=agent.updated_at,
        permissions=[],
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(require_permission("agents", "delete")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(
    agent_id: UUID, new_name: str, new_slug: str,
    current_user: User = Depends(require_permission("agents", "write")),
    db: AsyncSession = Depends(get_db),
):
    manager = get_agent_manager()
    agent = await manager.duplicate_agent(db, agent_id, new_name, new_slug, current_user.id)
    return AgentResponse(
        id=agent.id, name=agent.name, slug=agent.slug, description=agent.description,
        version=agent.version, agent_type=agent.agent_type, config=agent.config,
        system_prompt=agent.system_prompt, is_active=agent.is_active,
        created_by=agent.created_by, created_at=agent.created_at, updated_at=agent.updated_at,
        permissions=[],
    )


@router.post("/{agent_id}/export")
async def export_agent(
    agent_id: UUID,
    current_user: User = Depends(require_permission("agents", "export")),
    db: AsyncSession = Depends(get_db),
):
    manager = get_agent_manager()
    data = await manager.export_agent(db, agent_id)
    return Response(
        content=data, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=agent_{agent_id}.zip"},
    )


@router.post("/import", response_model=AgentResponse)
async def import_agent(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("agents", "import")),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    manager = get_agent_manager()
    agent = await manager.import_agent(db, content, created_by=current_user.id)
    return AgentResponse(
        id=agent.id, name=agent.name, slug=agent.slug, description=agent.description,
        version=agent.version, agent_type=agent.agent_type, config=agent.config,
        system_prompt=agent.system_prompt, is_active=agent.is_active,
        created_by=agent.created_by, created_at=agent.created_at, updated_at=agent.updated_at,
        permissions=[],
    )
