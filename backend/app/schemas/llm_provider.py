from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class LLMModelCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True


class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class LLMModelResponse(BaseModel):
    id: UUID
    provider_id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LLMProviderCreate(BaseModel):
    name: str
    slug: str
    base_url: Optional[str] = None
    is_active: bool = True
    models: Optional[List[LLMModelCreate]] = []


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class LLMProviderResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    base_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    models: List[LLMModelResponse] = []
    has_api_key: bool = False

    class Config:
        from_attributes = True


class APIKeyRequest(BaseModel):
    api_key: str
