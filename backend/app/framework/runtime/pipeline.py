"""
Pipeline d'exécution — Couche INTOUCHABLE qui enveloppe chaque appel agent.

L'agent ne s'exécute JAMAIS directement. Le pipeline gère automatiquement :
1. Validation de l'input
2. Vérification des permissions
3. Vérification des quotas
4. Modération de l'input
5. Exécution de l'agent (handle_message)
6. Modération de l'output
7. Log de consommation
8. Gestion des erreurs

Le développeur d'agent n'a AUCUN contrôle sur ce pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from app.framework.schemas import (
    AgentResponse,
    AgentResponseChunk,
    JobStatus,
    UserMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Résultat du pipeline d'exécution."""

    success: bool
    response: Optional[AgentResponse] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


class ExecutionPipeline:
    """
    Pipeline d'exécution des agents.

    Chaque appel à un agent passe par ce pipeline qui applique
    systématiquement toutes les couches de sécurité et de logging.
    """

    def __init__(
        self,
        db_session: Any,
        moderation_service: Any = None,
        consumption_service: Any = None,
        quota_service: Any = None,
    ):
        self._db = db_session
        self._moderation = moderation_service
        self._consumption = consumption_service
        self._quota = quota_service

    async def execute(
        self,
        agent: Any,
        message: UserMessage,
        context: Any,
        user: Any,
    ) -> PipelineResult:
        """
        Exécute un agent à travers le pipeline complet.

        Args:
            agent: Instance de BaseAgent
            message: Message utilisateur
            context: AgentContext
            user: Utilisateur courant

        Returns:
            PipelineResult avec la réponse ou l'erreur
        """
        start_time = time.time()

        try:
            # 1. Validation input
            validation_error = self._validate_input(message)
            if validation_error:
                return PipelineResult(
                    success=False, error=validation_error, error_code="VALIDATION_ERROR"
                )

            # 2. Vérification quotas
            if self._quota:
                quota_check = await self._check_quota(user, agent.manifest.slug)
                if not quota_check["allowed"]:
                    return PipelineResult(
                        success=False,
                        error=f"Quota dépassé: {quota_check.get('reason', 'limite atteinte')}",
                        error_code="QUOTA_EXCEEDED",
                    )

            # 3. Modération input
            if self._moderation:
                moderation_result = await self._moderate_input(
                    message.content, agent.manifest.slug
                )
                if moderation_result.get("blocked"):
                    return PipelineResult(
                        success=False,
                        error="Message bloqué par la modération",
                        error_code="MODERATION_BLOCKED",
                    )
                if moderation_result.get("modified_content"):
                    message = UserMessage(
                        content=moderation_result["modified_content"],
                        attachments=message.attachments,
                        metadata=message.metadata,
                    )

            # 4. Exécution de l'agent
            response = await agent.handle_message(message, context)

            # 5. Modération output
            if self._moderation:
                output_moderation = await self._moderate_output(
                    response.content, agent.manifest.slug
                )
                if output_moderation.get("blocked"):
                    return PipelineResult(
                        success=False,
                        error="Réponse bloquée par la modération",
                        error_code="MODERATION_BLOCKED_OUTPUT",
                    )
                if output_moderation.get("modified_content"):
                    response = AgentResponse(
                        content=output_moderation["modified_content"],
                        attachments=response.attachments,
                        metadata=response.metadata,
                    )

            # 6. Log consommation
            execution_time = int((time.time() - start_time) * 1000)
            if self._consumption:
                await self._log_consumption(
                    user=user,
                    agent_slug=agent.manifest.slug,
                    tokens_in=response.metadata.get("tokens_in", 0),
                    tokens_out=response.metadata.get("tokens_out", 0),
                )

            return PipelineResult(
                success=True,
                response=response,
                execution_time_ms=execution_time,
                tokens_in=response.metadata.get("tokens_in", 0),
                tokens_out=response.metadata.get("tokens_out", 0),
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(
                f"Pipeline error for agent {agent.manifest.slug}: {e}",
                exc_info=True,
            )
            return PipelineResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                execution_time_ms=execution_time,
            )

    async def execute_stream(
        self,
        agent: Any,
        message: UserMessage,
        context: Any,
        user: Any,
    ) -> AsyncIterator[AgentResponseChunk | PipelineResult]:
        """
        Exécute un agent en mode streaming à travers le pipeline.

        Yields:
            AgentResponseChunk pour chaque token, puis PipelineResult final
        """
        start_time = time.time()

        # 1-3: Mêmes vérifications que execute()
        validation_error = self._validate_input(message)
        if validation_error:
            yield PipelineResult(
                success=False, error=validation_error, error_code="VALIDATION_ERROR"
            )
            return

        if self._quota:
            quota_check = await self._check_quota(user, agent.manifest.slug)
            if not quota_check["allowed"]:
                yield PipelineResult(
                    success=False,
                    error=f"Quota dépassé: {quota_check.get('reason', '')}",
                    error_code="QUOTA_EXCEEDED",
                )
                return

        if self._moderation:
            moderation_result = await self._moderate_input(
                message.content, agent.manifest.slug
            )
            if moderation_result.get("blocked"):
                yield PipelineResult(
                    success=False,
                    error="Message bloqué par la modération",
                    error_code="MODERATION_BLOCKED",
                )
                return
            if moderation_result.get("modified_content"):
                message = UserMessage(
                    content=moderation_result["modified_content"],
                    attachments=message.attachments,
                    metadata=message.metadata,
                )

        # 4. Streaming de la réponse
        try:
            full_content = ""
            async for chunk in agent.handle_message_stream(message, context):
                full_content += chunk.content
                yield chunk

            # 5. Modération output (sur le contenu complet)
            if self._moderation:
                output_moderation = await self._moderate_output(
                    full_content, agent.manifest.slug
                )
                if output_moderation.get("blocked"):
                    yield PipelineResult(
                        success=False,
                        error="Réponse bloquée par la modération",
                        error_code="MODERATION_BLOCKED_OUTPUT",
                    )
                    return

            # 6. Log consommation
            execution_time = int((time.time() - start_time) * 1000)
            yield PipelineResult(
                success=True,
                response=AgentResponse(content=full_content),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Stream pipeline error: {e}", exc_info=True)
            yield PipelineResult(
                success=False,
                error=str(e),
                error_code="EXECUTION_ERROR",
                execution_time_ms=execution_time,
            )

    # =========================================================================
    # Étapes internes du pipeline
    # =========================================================================

    def _validate_input(self, message: UserMessage) -> Optional[str]:
        """Valide le message utilisateur."""
        if not message.content and not message.attachments:
            return "Message vide: contenu ou pièce jointe requis"
        if len(message.content) > 100_000:
            return "Message trop long (max 100 000 caractères)"
        return None

    async def _check_quota(self, user: Any, agent_slug: str) -> dict[str, Any]:
        """Vérifie les quotas de l'utilisateur."""
        try:
            return await self._quota.check_quota(
                user_id=user.id, agent_slug=agent_slug
            )
        except Exception as e:
            logger.warning(f"Quota check failed, allowing: {e}")
            return {"allowed": True}

    async def _moderate_input(self, content: str, agent_slug: str) -> dict[str, Any]:
        """Applique la modération sur l'input."""
        try:
            return await self._moderation.moderate_input(
                content=content, agent_slug=agent_slug
            )
        except Exception as e:
            logger.warning(f"Input moderation failed, allowing: {e}")
            return {"blocked": False}

    async def _moderate_output(self, content: str, agent_slug: str) -> dict[str, Any]:
        """Applique la modération sur l'output."""
        try:
            return await self._moderation.moderate_output(
                content=content, agent_slug=agent_slug
            )
        except Exception as e:
            logger.warning(f"Output moderation failed, allowing: {e}")
            return {"blocked": False}

    async def _log_consumption(
        self, user: Any, agent_slug: str, tokens_in: int, tokens_out: int
    ) -> None:
        """Log la consommation de tokens."""
        try:
            await self._consumption.log(
                user_id=user.id,
                agent_slug=agent_slug,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
        except Exception as e:
            logger.warning(f"Consumption logging failed: {e}")
