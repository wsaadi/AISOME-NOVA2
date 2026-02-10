from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class ModerationRuleCreate(BaseModel):
    name: str
    agent_id: Optional[UUID] = None
    rule_type: str  # anonymization, content_filter, pii_detection
    config: Dict[str, Any] = {}
    entity_types: List[str] = []  # person, email, phone, address, credit_card, etc.
    action: str = "redact"  # redact, block, flag, replace
    replacement_template: str = "[REDACTED]"
    is_active: bool = True


class ModerationRuleUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    entity_types: Optional[List[str]] = None
    action: Optional[str] = None
    replacement_template: Optional[str] = None
    is_active: Optional[bool] = None


class ModerationRuleResponse(BaseModel):
    id: UUID
    name: str
    agent_id: Optional[UUID]
    rule_type: str
    config: Dict[str, Any]
    entity_types: List[str]
    action: str
    replacement_template: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
