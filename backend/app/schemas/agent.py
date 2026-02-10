from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    version: str = "1.0.0"
    agent_type: str = "conversational"
    config: Dict[str, Any] = {}
    system_prompt: Optional[str] = None
    is_active: bool = True
    role_ids: Optional[List[UUID]] = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    agent_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[UUID]] = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    version: str
    agent_type: str
    config: Dict[str, Any]
    system_prompt: Optional[str]
    is_active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    permissions: List[dict] = []

    class Config:
        from_attributes = True


class AgentExport(BaseModel):
    name: str
    slug: str
    description: Optional[str]
    version: str
    agent_type: str
    config: Dict[str, Any]
    system_prompt: Optional[str]
    moderation_rules: List[dict] = []
    export_version: str = "1.0"
    exported_at: datetime


class AgentImport(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    data: Dict[str, Any]


class AgentPermissionUpdate(BaseModel):
    role_ids: List[UUID]
