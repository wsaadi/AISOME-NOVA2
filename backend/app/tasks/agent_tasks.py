"""
Agent Tasks — Tâches Celery pour l'exécution asynchrone des agents.

Flux:
1. L'API reçoit un message → crée un job → envoie la tâche Celery
2. Le worker Celery exécute l'agent via le pipeline
3. Le worker publie la progression sur Redis pub/sub
4. Le WebSocket lit Redis pub/sub et pousse vers le frontend
5. Le résultat final est persisté en base
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import redis

from app.worker import celery_app

logger = logging.getLogger(__name__)


def get_redis_client():
    """Retourne un client Redis pour pub/sub."""
    from app.config import get_settings
    settings = get_settings()

    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )


def publish_progress(job_id: str, progress: int, message: str = "", status: str = "running"):
    """
    Publie la progression d'un job sur Redis pub/sub.

    Le WebSocket côté API écoute ce channel et push vers le frontend.

    Args:
        job_id: ID du job
        progress: Pourcentage (0-100)
        message: Message de statut
        status: Statut du job (running, streaming, completed, failed)
    """
    try:
        r = get_redis_client()
        r.publish(
            f"job:{job_id}",
            json.dumps(
                {
                    "job_id": job_id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to publish progress: {e}")


def publish_stream_chunk(job_id: str, content: str, is_final: bool = False):
    """
    Publie un chunk de streaming sur Redis pub/sub.

    Args:
        job_id: ID du job
        content: Contenu du chunk
        is_final: True si c'est le dernier chunk
    """
    try:
        r = get_redis_client()
        r.publish(
            f"stream:{job_id}",
            json.dumps(
                {
                    "job_id": job_id,
                    "content": content,
                    "is_final": is_final,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to publish stream chunk: {e}")


@celery_app.task(bind=True, name="app.tasks.agent_tasks.execute_agent_task")
def execute_agent_task(
    self,
    job_id: str,
    agent_slug: str,
    user_id: int,
    session_id: str,
    message_content: str,
    message_attachments: list | None = None,
    message_metadata: dict | None = None,
):
    """
    Tâche Celery : exécute un agent de manière asynchrone.

    Args:
        job_id: ID unique du job
        agent_slug: Slug de l'agent à exécuter
        user_id: ID de l'utilisateur
        session_id: ID de la session
        message_content: Contenu du message utilisateur
        message_attachments: Pièces jointes
        message_metadata: Métadonnées
    """
    publish_progress(job_id, 0, "Démarrage de l'agent...")

    try:
        # Exécuter l'agent dans une boucle asyncio
        result = asyncio.get_event_loop().run_until_complete(
            _run_agent(
                job_id=job_id,
                agent_slug=agent_slug,
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                message_attachments=message_attachments or [],
                message_metadata=message_metadata or {},
            )
        )

        publish_progress(job_id, 100, "Terminé", status="completed")
        return result

    except Exception as e:
        logger.error(f"Agent task failed: {e}", exc_info=True)
        publish_progress(job_id, 0, f"Erreur: {str(e)}", status="failed")
        return {"success": False, "error": str(e)}


@celery_app.task(bind=True, name="app.tasks.agent_tasks.execute_agent_stream_task")
def execute_agent_stream_task(
    self,
    job_id: str,
    agent_slug: str,
    user_id: int,
    session_id: str,
    message_content: str,
    message_attachments: list | None = None,
    message_metadata: dict | None = None,
):
    """
    Tâche Celery : exécute un agent en mode streaming.

    Les tokens sont publiés en temps réel sur Redis pub/sub.
    """
    publish_progress(job_id, 0, "Démarrage du streaming...")

    try:
        result = asyncio.get_event_loop().run_until_complete(
            _run_agent_stream(
                job_id=job_id,
                agent_slug=agent_slug,
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                message_attachments=message_attachments or [],
                message_metadata=message_metadata or {},
            )
        )

        publish_progress(job_id, 100, "Streaming terminé", status="completed")
        return result

    except Exception as e:
        logger.error(f"Stream task failed: {e}", exc_info=True)
        publish_progress(job_id, 0, f"Erreur: {str(e)}", status="failed")
        return {"success": False, "error": str(e)}


async def _run_agent(
    job_id: str,
    agent_slug: str,
    user_id: int,
    session_id: str,
    message_content: str,
    message_attachments: list,
    message_metadata: dict,
) -> dict:
    """Exécute l'agent via le moteur framework."""
    from app.database import async_session
    from app.framework.runtime.engine import AgentEngine
    from app.framework.schemas import UserMessage

    async with async_session() as db:
        # Construire le moteur (simplifié — sera enrichi avec DI)
        from app.framework.connectors.registry import ConnectorRegistry
        from app.framework.runtime.session import SessionManager
        from app.framework.tools.registry import ToolRegistry

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

        publish_progress(job_id, 20, "Agent chargé, exécution en cours...")

        message = UserMessage(
            content=message_content,
            metadata=message_metadata,
        )

        # Simuler un user object minimal
        class SimpleUser:
            def __init__(self, uid):
                self.id = uid

        result = await engine.execute(
            agent_slug=agent_slug,
            message=message,
            user=SimpleUser(user_id),
            session_id=session_id,
        )

        publish_progress(job_id, 90, "Finalisation...")

        if result.success and result.response:
            return {
                "success": True,
                "content": result.response.content,
                "attachments": [a.model_dump() for a in result.response.attachments],
                "metadata": result.response.metadata,
                "execution_time_ms": result.execution_time_ms,
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "error_code": result.error_code,
            }


async def _run_agent_stream(
    job_id: str,
    agent_slug: str,
    user_id: int,
    session_id: str,
    message_content: str,
    message_attachments: list,
    message_metadata: dict,
) -> dict:
    """Exécute l'agent en mode streaming via le moteur framework."""
    from app.database import async_session
    from app.framework.runtime.engine import AgentEngine
    from app.framework.schemas import UserMessage

    async with async_session() as db:
        from app.framework.connectors.registry import ConnectorRegistry
        from app.framework.runtime.session import SessionManager
        from app.framework.tools.registry import ToolRegistry

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

        agent = engine.get_agent(agent_slug)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_slug}' not found"}

        context = await engine.build_context(agent_slug, user_id, session_id)
        message = UserMessage(content=message_content, metadata=message_metadata)

        full_content = ""
        async for chunk in agent.handle_message_stream(message, context):
            full_content += chunk.content
            publish_stream_chunk(job_id, chunk.content, chunk.is_final)

        return {"success": True, "content": full_content}
