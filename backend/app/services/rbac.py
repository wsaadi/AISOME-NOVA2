from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.role import Role


def check_permission(user: User, resource: str, action: str) -> bool:
    if user.is_superadmin:
        return True
    for role in user.roles:
        perms = role.permissions or {}
        resource_perms = perms.get(resource, {})
        if resource_perms.get(action, False):
            return True
    return False


def get_user_permissions(user: User) -> dict:
    if user.is_superadmin:
        return {
            "users": {"read": True, "write": True, "delete": True},
            "roles": {"read": True, "write": True, "delete": True},
            "llm_config": {"read": True, "write": True},
            "consumption": {"read": True},
            "quotas": {"read": True, "write": True},
            "costs": {"read": True, "write": True},
            "moderation": {"read": True, "write": True},
            "agents": {"read": True, "write": True, "delete": True, "export": True, "import": True},
            "catalog_management": {"read": True, "write": True},
            "system": {"read": True, "update": True},
        }
    merged = {}
    for role in user.roles:
        for resource, actions in (role.permissions or {}).items():
            if resource not in merged:
                merged[resource] = {}
            for action, allowed in actions.items():
                if allowed:
                    merged[resource][action] = True
    return merged


async def get_accessible_agent_ids(db: AsyncSession, user: User) -> Optional[List[UUID]]:
    if user.is_superadmin:
        return None  # None means all agents
    role_ids = [role.id for role in user.roles]
    if not role_ids:
        return []
    from app.models.agent import AgentPermission
    result = await db.execute(
        select(AgentPermission.agent_id).where(AgentPermission.role_id.in_(role_ids))
    )
    return list(set(row[0] for row in result.all()))
