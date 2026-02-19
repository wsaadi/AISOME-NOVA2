"""
Workspaces API — Gestion des espaces de travail collaboratifs.

Endpoints:
    GET    /api/workspaces?agent_slug=...  — Lister les workspaces accessibles
    POST   /api/workspaces                 — Créer un workspace
    GET    /api/workspaces/{id}            — Détail d'un workspace
    PUT    /api/workspaces/{id}            — Modifier un workspace
    DELETE /api/workspaces/{id}            — Supprimer un workspace
    POST   /api/workspaces/{id}/members    — Ajouter un membre
    DELETE /api/workspaces/{id}/members/{user_id} — Retirer un membre
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


# =============================================================================
# Schemas
# =============================================================================

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    agent_slug: str = Field(..., min_length=1, max_length=200)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class WorkspaceMemberAdd(BaseModel):
    user_id: str = Field(..., description="UUID de l'utilisateur à ajouter")
    role: str = Field(default="member", pattern="^(owner|member)$")


class WorkspaceMemberResponse(BaseModel):
    id: str
    user_id: str
    username: str
    role: str
    joined_at: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    agent_slug: str
    created_by: Optional[str]
    created_at: str
    updated_at: str
    is_active: bool
    members: list[WorkspaceMemberResponse]


# =============================================================================
# Helpers
# =============================================================================

def _format_workspace(ws: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=str(ws.id),
        name=ws.name,
        description=ws.description,
        agent_slug=ws.agent_slug,
        created_by=str(ws.created_by) if ws.created_by else None,
        created_at=ws.created_at.isoformat() if ws.created_at else "",
        updated_at=ws.updated_at.isoformat() if ws.updated_at else "",
        is_active=ws.is_active,
        members=[
            WorkspaceMemberResponse(
                id=str(m.id),
                user_id=str(m.user_id),
                username=m.user.username if m.user else "unknown",
                role=m.role,
                joined_at=m.joined_at.isoformat() if m.joined_at else "",
            )
            for m in (ws.members or [])
        ],
    )


def _is_member(ws: Workspace, user_id) -> bool:
    return any(str(m.user_id) == str(user_id) for m in (ws.members or []))


def _is_owner(ws: Workspace, user_id) -> bool:
    return any(
        str(m.user_id) == str(user_id) and m.role == "owner"
        for m in (ws.members or [])
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    agent_slug: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste les workspaces dont l'utilisateur est membre."""
    query = (
        select(Workspace)
        .join(WorkspaceMember)
        .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        .where(
            WorkspaceMember.user_id == current_user.id,
            Workspace.is_active == True,
        )
    )
    if agent_slug:
        query = query.where(Workspace.agent_slug == agent_slug)

    query = query.order_by(Workspace.updated_at.desc())
    result = await db.execute(query)
    workspaces = result.scalars().unique().all()
    return [_format_workspace(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau workspace et ajoute le créateur comme owner."""
    ws = Workspace(
        name=data.name,
        description=data.description,
        agent_slug=data.agent_slug,
        created_by=current_user.id,
    )
    db.add(ws)
    await db.flush()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        .where(Workspace.id == ws.id)
    )
    ws = result.scalar_one()
    return _format_workspace(ws)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Récupère le détail d'un workspace."""
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        .where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    if not _is_member(ws, current_user.id):
        raise HTTPException(status_code=403, detail="Accès interdit")
    return _format_workspace(ws)


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour un workspace (owner uniquement)."""
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        .where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    if not _is_owner(ws, current_user.id):
        raise HTTPException(status_code=403, detail="Seul le owner peut modifier")

    if data.name is not None:
        ws.name = data.name
    if data.description is not None:
        ws.description = data.description

    await db.commit()
    await db.refresh(ws)
    return _format_workspace(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime un workspace (owner uniquement)."""
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members))
        .where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    if not _is_owner(ws, current_user.id):
        raise HTTPException(status_code=403, detail="Seul le owner peut supprimer")

    await db.delete(ws)
    await db.commit()


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse)
async def add_member(
    workspace_id: UUID,
    data: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ajoute un membre au workspace (owner uniquement)."""
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members))
        .where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    if not _is_owner(ws, current_user.id):
        raise HTTPException(status_code=403, detail="Seul le owner peut ajouter des membres")

    # Check user exists
    from app.models.user import User as UserModel
    user_result = await db.execute(select(UserModel).where(UserModel.id == data.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Check not already member
    if _is_member(ws, data.user_id):
        raise HTTPException(status_code=409, detail="Déjà membre")

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=UUID(data.user_id),
        role=data.role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return WorkspaceMemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        username=target_user.username,
        role=member.role,
        joined_at=member.joined_at.isoformat() if member.joined_at else "",
    )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retire un membre du workspace (owner ou soi-même)."""
    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members))
        .where(Workspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")

    is_self = str(current_user.id) == str(user_id)
    if not is_self and not _is_owner(ws, current_user.id):
        raise HTTPException(status_code=403, detail="Non autorisé")

    member = next(
        (m for m in ws.members if str(m.user_id) == str(user_id)),
        None,
    )
    if not member:
        raise HTTPException(status_code=404, detail="Membre non trouvé")

    await db.delete(member)
    await db.commit()
