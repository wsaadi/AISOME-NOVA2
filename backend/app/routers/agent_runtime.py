"""
Agent Runtime API — Endpoints d'exécution des agents.

Endpoints:
    POST /api/agent-runtime/{slug}/chat      — Envoyer un message (async job)
    POST /api/agent-runtime/{slug}/chat/sync  — Envoyer un message (synchrone)
    GET  /api/agent-runtime/{slug}/sessions   — Lister les sessions
    GET  /api/agent-runtime/sessions/{sid}    — Détail d'une session
    GET  /api/agent-runtime/jobs/{job_id}     — Statut d'un job
    GET  /api/agent-runtime/catalog           — Catalogue des agents chargés
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/agent-runtime", tags=["Agent Runtime"])


# =============================================================================
# Request / Response schemas
# =============================================================================


class ChatRequest(BaseModel):
    """Requête d'envoi de message à un agent."""

    message: str = Field(..., description="Contenu du message")
    session_id: Optional[str] = Field(None, description="ID session (crée une nouvelle si None)")
    metadata: dict[str, Any] = Field(default_factory=dict)
    stream: bool = Field(default=False, description="Activer le streaming")


class ChatResponse(BaseModel):
    """Réponse async — retourne un job_id pour suivre la progression."""

    job_id: str
    session_id: str
    status: str = "pending"
    message: str = "Job créé, suivez la progression via WebSocket ou GET /jobs/{job_id}"


class ChatSyncResponse(BaseModel):
    """Réponse synchrone — retourne directement le résultat."""

    session_id: str
    content: str
    attachments: list[dict] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: int = 0


class JobStatusResponse(BaseModel):
    """Statut d'un job."""

    job_id: str
    status: str
    progress: int = 0
    progress_message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None


class AgentInfo(BaseModel):
    """Info d'un agent dans le catalogue."""

    slug: str
    name: str
    description: str
    version: str
    icon: str = "smart_toy"
    category: str = "general"
    tags: list[str] = Field(default_factory=list)


class AgentLLMConfigRequest(BaseModel):
    """Requête de configuration LLM par agent."""
    model_config = {"protected_namespaces": ()}

    provider_id: str = Field(..., description="UUID du provider LLM")
    model_id: str = Field(..., description="UUID du modèle LLM")


class AgentLLMConfigResponse(BaseModel):
    """Réponse de configuration LLM par agent."""
    model_config = {"protected_namespaces": ()}

    id: str
    agent_slug: str
    provider_id: str
    model_id: str
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool = True


class SessionListResponse(BaseModel):
    """Liste des sessions."""

    sessions: list[dict[str, Any]]
    total: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/{slug}/chat", response_model=ChatResponse)
async def chat_async(
    slug: str,
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    """
    Envoie un message à un agent — exécution asynchrone.

    Le message est mis en queue (Redis/Celery) et exécuté par un worker.
    L'utilisateur reçoit un job_id pour suivre la progression via WebSocket.

    Returns:
        ChatResponse avec job_id et session_id
    """
    job_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())

    try:
        from app.tasks.agent_tasks import (
            execute_agent_stream_task,
            execute_agent_task,
        )

        task_fn = execute_agent_stream_task if request.stream else execute_agent_task

        task_fn.delay(
            job_id=job_id,
            agent_slug=slug,
            user_id=current_user.id,
            session_id=session_id,
            message_content=request.message,
            message_metadata=request.metadata,
        )

        return ChatResponse(
            job_id=job_id,
            session_id=session_id,
            status="pending",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de création du job: {str(e)}")


@router.post("/{slug}/chat/sync", response_model=ChatSyncResponse)
async def chat_sync(
    slug: str,
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    """
    Envoie un message à un agent — exécution synchrone.

    Attend la réponse complète avant de retourner.
    À utiliser pour les tests ou les agents rapides.

    Returns:
        ChatSyncResponse avec le contenu de la réponse
    """
    from app.database import async_session
    from app.framework.connectors.registry import ConnectorRegistry
    from app.framework.runtime.engine import AgentEngine
    from app.framework.runtime.session import SessionManager
    from app.framework.schemas import UserMessage
    from app.framework.tools.registry import ToolRegistry

    session_id = request.session_id or str(uuid.uuid4())

    async with async_session() as db:
        tool_registry = ToolRegistry()
        tool_registry.discover()
        connector_registry = ConnectorRegistry()
        connector_registry.discover()
        session_manager = SessionManager(db)

        from app.services.consumption import ConsumptionService
        consumption_service = ConsumptionService(db)

        engine = AgentEngine(
            db_session=db,
            tool_registry=tool_registry,
            connector_registry=connector_registry,
            session_manager=session_manager,
            consumption_service=consumption_service,
        )
        engine.discover_agents()

        message = UserMessage(content=request.message, metadata=request.metadata)

        result = await engine.execute(
            agent_slug=slug,
            message=message,
            user=current_user,
            session_id=session_id,
        )

        if not result.success:
            raise HTTPException(
                status_code=400,
                detail={"error": result.error, "code": result.error_code},
            )

        return ChatSyncResponse(
            session_id=session_id,
            content=result.response.content if result.response else "",
            attachments=[a.model_dump() for a in result.response.attachments] if result.response else [],
            metadata=result.response.metadata if result.response else {},
            execution_time_ms=result.execution_time_ms,
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """
    Récupère le statut d'un job.

    Utile quand l'utilisateur revient sur un agent et veut voir
    où en est l'exécution.
    """
    from app.worker import celery_app

    task_result = celery_app.AsyncResult(job_id)

    if task_result.ready():
        result = task_result.result
        if isinstance(result, dict) and result.get("success"):
            return JobStatusResponse(
                job_id=job_id,
                status="completed",
                progress=100,
                result=result,
            )
        else:
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                error=str(result.get("error", "Unknown error")) if isinstance(result, dict) else str(result),
            )

    return JobStatusResponse(
        job_id=job_id,
        status="running" if task_result.state == "STARTED" else "pending",
        progress=0,
    )


@router.get("/{slug}/sessions", response_model=SessionListResponse)
async def list_sessions(
    slug: str,
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(get_current_user),
):
    """Liste les sessions d'un utilisateur pour un agent."""
    from app.database import async_session
    from app.framework.runtime.session import SessionManager

    async with async_session() as db:
        session_manager = SessionManager(db)
        sessions = await session_manager.list_sessions(
            agent_slug=slug,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        return SessionListResponse(
            sessions=[s.model_dump() for s in sessions],
            total=len(sessions),
        )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Récupère le détail d'une session avec ses messages."""
    from app.database import async_session
    from app.framework.runtime.session import SessionManager

    async with async_session() as db:
        session_manager = SessionManager(db)
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")

        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Accès interdit")

        return session.model_dump()


@router.get("/catalog", response_model=list[AgentInfo])
async def get_agent_catalog(
    current_user=Depends(get_current_user),
):
    """
    Retourne le catalogue des agents chargés.

    Liste tous les agents disponibles avec leurs métadonnées.
    """
    from app.framework.runtime.engine import AgentEngine, AGENTS_ROOT
    from app.framework.connectors.registry import ConnectorRegistry
    from app.framework.runtime.session import SessionManager
    from app.framework.tools.registry import ToolRegistry
    from app.database import async_session

    async with async_session() as db:
        tool_registry = ToolRegistry()
        connector_registry = ConnectorRegistry()
        session_manager = SessionManager(db)

        engine = AgentEngine(
            db_session=db,
            tool_registry=tool_registry,
            connector_registry=connector_registry,
            session_manager=session_manager,
        )
        engine.discover_agents()

        return [
            AgentInfo(
                slug=m.slug,
                name=m.name,
                description=m.description,
                version=m.version,
                icon=m.icon,
                category=m.category,
                tags=m.tags,
            )
            for m in engine.list_agents()
        ]


# =============================================================================
# Per-agent LLM Configuration
# =============================================================================


@router.get("/config/llm", response_model=list[AgentLLMConfigResponse])
async def list_agent_llm_configs(
    current_user=Depends(get_current_user),
):
    """Liste toutes les configurations LLM par agent."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.agent_llm_config import AgentLLMConfig

    async with async_session() as db:
        result = await db.execute(select(AgentLLMConfig).where(AgentLLMConfig.is_active == True))
        configs = result.scalars().all()
        return [
            AgentLLMConfigResponse(
                id=str(c.id),
                agent_slug=c.agent_slug,
                provider_id=str(c.provider_id),
                model_id=str(c.model_id),
                provider_name=c.provider.name if c.provider else None,
                model_name=c.model.name if c.model else None,
                is_active=c.is_active,
            )
            for c in configs
        ]


@router.get("/config/llm/{agent_slug}", response_model=Optional[AgentLLMConfigResponse])
async def get_agent_llm_config(
    agent_slug: str,
    current_user=Depends(get_current_user),
):
    """Récupère la config LLM pour un agent spécifique."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.agent_llm_config import AgentLLMConfig

    async with async_session() as db:
        result = await db.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.agent_slug == agent_slug)
        )
        config = result.scalar_one_or_none()
        if not config:
            return None
        return AgentLLMConfigResponse(
            id=str(config.id),
            agent_slug=config.agent_slug,
            provider_id=str(config.provider_id),
            model_id=str(config.model_id),
            provider_name=config.provider.name if config.provider else None,
            model_name=config.model.name if config.model else None,
            is_active=config.is_active,
        )


@router.put("/config/llm/{agent_slug}", response_model=AgentLLMConfigResponse)
async def set_agent_llm_config(
    agent_slug: str,
    request: AgentLLMConfigRequest,
    current_user=Depends(get_current_user),
):
    """Définit ou met à jour la config LLM pour un agent."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.agent_llm_config import AgentLLMConfig

    async with async_session() as db:
        result = await db.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.agent_slug == agent_slug)
        )
        config = result.scalar_one_or_none()

        if config:
            config.provider_id = request.provider_id
            config.model_id = request.model_id
            config.is_active = True
        else:
            config = AgentLLMConfig(
                agent_slug=agent_slug,
                provider_id=request.provider_id,
                model_id=request.model_id,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)

        return AgentLLMConfigResponse(
            id=str(config.id),
            agent_slug=config.agent_slug,
            provider_id=str(config.provider_id),
            model_id=str(config.model_id),
            provider_name=config.provider.name if config.provider else None,
            model_name=config.model.name if config.model else None,
            is_active=config.is_active,
        )


@router.delete("/config/llm/{agent_slug}")
async def delete_agent_llm_config(
    agent_slug: str,
    current_user=Depends(get_current_user),
):
    """Supprime la config LLM spécifique d'un agent (revient au défaut plateforme)."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.agent_llm_config import AgentLLMConfig

    async with async_session() as db:
        result = await db.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.agent_slug == agent_slug)
        )
        config = result.scalar_one_or_none()
        if config:
            await db.delete(config)
            await db.commit()
        return {"ok": True}
