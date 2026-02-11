from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.llm_provider import LLMProvider, LLMModel
from app.schemas.llm_provider import (
    LLMProviderCreate, LLMProviderUpdate, LLMProviderResponse,
    LLMModelCreate, LLMModelUpdate, LLMModelResponse, APIKeyRequest,
)
from app.middleware.auth import require_permission
from app.services.vault import get_vault_service
from app.models.user import User

router = APIRouter(prefix="/api/llm", tags=["LLM Configuration"])


@router.post("/sync")
async def sync_from_connectors(
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Synchronise les connecteurs AI du framework vers la DB (auto-discovery)."""
    from app.services.connector_sync import sync_connectors_to_db
    summary = await sync_connectors_to_db(db)
    return summary


@router.get("/providers", response_model=list[LLMProviderResponse])
async def list_providers(
    current_user: User = Depends(require_permission("llm_config", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).options(selectinload(LLMProvider.models)).order_by(LLMProvider.name))
    providers = result.scalars().all()
    vault = get_vault_service()
    response = []
    for p in providers:
        resp = LLMProviderResponse.model_validate(p)
        resp.has_api_key = vault.has_api_key(p.slug)
        response.append(resp)
    return response


@router.post("/providers", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: LLMProviderCreate,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    provider = LLMProvider(name=provider_data.name, slug=provider_data.slug, base_url=provider_data.base_url, is_active=provider_data.is_active)
    db.add(provider)
    await db.flush()
    for model_data in (provider_data.models or []):
        db.add(LLMModel(provider_id=provider.id, name=model_data.name, slug=model_data.slug, is_active=model_data.is_active))
    await db.commit()
    result = await db.execute(select(LLMProvider).options(selectinload(LLMProvider.models)).where(LLMProvider.id == provider.id))
    return result.scalar_one()


@router.put("/providers/{provider_id}", response_model=LLMProviderResponse)
async def update_provider(
    provider_id: UUID, provider_data: LLMProviderUpdate,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).options(selectinload(LLMProvider.models)).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    for key, value in provider_data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.post("/providers/{provider_id}/api-key")
async def set_api_key(
    provider_id: UUID, request: APIKeyRequest,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    vault = get_vault_service()
    success = vault.store_api_key(provider.slug, request.api_key)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store API key")
    return {"status": "ok", "message": "API key stored successfully"}


@router.get("/providers/{provider_id}/api-key/status")
async def check_api_key(
    provider_id: UUID,
    current_user: User = Depends(require_permission("llm_config", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    vault = get_vault_service()
    return {"has_api_key": vault.has_api_key(provider.slug)}


@router.delete("/providers/{provider_id}/api-key")
async def delete_api_key(
    provider_id: UUID,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    vault = get_vault_service()
    vault.delete_api_key(provider.slug)
    return {"status": "ok"}


@router.post("/providers/{provider_id}/models", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
async def add_model(
    provider_id: UUID, model_data: LLMModelCreate,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    model = LLMModel(provider_id=provider_id, name=model_data.name, slug=model_data.slug, is_active=model_data.is_active)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.put("/models/{model_id}", response_model=LLMModelResponse)
async def update_model(
    model_id: UUID, model_data: LLMModelUpdate,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMModel).where(LLMModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    for key, value in model_data.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(require_permission("llm_config", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMModel).where(LLMModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    await db.delete(model)
    await db.commit()
