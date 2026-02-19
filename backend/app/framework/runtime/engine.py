"""
Engine — Moteur de chargement et d'exécution des agents.

Responsabilités:
- Découvre et charge les agents depuis le filesystem
- Crée les AgentContext pour chaque exécution
- Orchestre le pipeline d'exécution
- Gère les appels inter-agents (orchestration)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

from app.framework.base.agent import BaseAgent
from app.framework.runtime.context import (
    AgentContext,
    AgentService,
    ConnectorService,
    LLMService,
    MemoryService,
    StorageService,
    ToolService,
)
from app.framework.runtime.pipeline import ExecutionPipeline, PipelineResult
from app.framework.runtime.session import SessionManager
from app.framework.schemas import AgentManifest, AgentResponse, UserMessage

logger = logging.getLogger(__name__)

# Chemin racine des agents
AGENTS_ROOT = Path(__file__).parent.parent.parent / "agents"


class AgentEngine:
    """
    Moteur d'exécution des agents.

    Charge dynamiquement les agents depuis le filesystem,
    crée les contextes d'exécution et orchestre le pipeline.
    """

    def __init__(
        self,
        db_session: Any,
        tool_registry: Any,
        connector_registry: Any,
        session_manager: SessionManager,
        vault_service: Any = None,
        moderation_service: Any = None,
        consumption_service: Any = None,
        quota_service: Any = None,
        redis_client: Any = None,
        storage_service: Any = None,
    ):
        self._db = db_session
        self._tool_registry = tool_registry
        self._connector_registry = connector_registry
        self._session_manager = session_manager
        self._vault = vault_service
        self._moderation = moderation_service
        self._consumption = consumption_service
        self._quota = quota_service
        self._redis = redis_client
        self._storage = storage_service

        # Cache des agents chargés
        self._agents: dict[str, BaseAgent] = {}

        # Pipeline d'exécution
        self._pipeline = ExecutionPipeline(
            db_session=db_session,
            moderation_service=moderation_service,
            consumption_service=consumption_service,
            quota_service=quota_service,
        )

    def discover_agents(self) -> dict[str, AgentManifest]:
        """
        Découvre tous les agents disponibles sur le filesystem.

        Scanne backend/app/agents/ et charge chaque agent.py qui étend BaseAgent.

        Returns:
            Dict slug → AgentManifest des agents découverts
        """
        discovered = {}

        if not AGENTS_ROOT.exists():
            logger.warning(f"Agents directory not found: {AGENTS_ROOT}")
            return discovered

        for agent_dir in AGENTS_ROOT.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue

            agent_py = agent_dir / "agent.py"
            if not agent_py.exists():
                logger.warning(f"No agent.py found in {agent_dir.name}, skipping")
                continue

            try:
                agent = self._load_agent(agent_dir.name, agent_py)
                if agent:
                    self._agents[agent.manifest.slug] = agent
                    discovered[agent.manifest.slug] = agent.manifest
                    logger.info(f"Agent discovered: {agent.manifest.slug} v{agent.manifest.version}")
            except Exception as e:
                logger.error(f"Failed to load agent {agent_dir.name}: {e}")

        logger.info(f"Total agents discovered: {len(discovered)}")
        return discovered

    def _load_agent(self, dir_name: str, agent_py: Path) -> Optional[BaseAgent]:
        """
        Charge un agent depuis son fichier agent.py.

        Args:
            dir_name: Nom du dossier de l'agent
            agent_py: Chemin vers le fichier agent.py

        Returns:
            Instance de BaseAgent ou None
        """
        spec = importlib.util.spec_from_file_location(
            f"agents.{dir_name}.agent", agent_py
        )
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Chercher la classe qui étend BaseAgent
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseAgent)
                and attr is not BaseAgent
            ):
                return attr()

        logger.warning(f"No BaseAgent subclass found in {agent_py}")
        return None

    def get_agent(self, slug: str) -> Optional[BaseAgent]:
        """
        Récupère un agent chargé par son slug.

        Args:
            slug: Slug de l'agent

        Returns:
            Instance de BaseAgent ou None
        """
        return self._agents.get(slug)

    def list_agents(self) -> list[AgentManifest]:
        """
        Liste tous les agents chargés.

        Returns:
            Liste de AgentManifest
        """
        return [agent.manifest for agent in self._agents.values()]

    async def build_context(
        self,
        agent_slug: str,
        user_id: int,
        session_id: str,
        lang: str = "en",
        workspace_id: Optional[str] = None,
    ) -> AgentContext:
        """
        Construit un AgentContext pour une exécution.

        Récupère la config LLM depuis la base et les clés depuis Vault,
        instancie tous les services et retourne le contexte.

        Args:
            agent_slug: Slug de l'agent
            user_id: ID de l'utilisateur
            session_id: ID de la session
            lang: Langue préférée de l'utilisateur (en, fr, es)
            workspace_id: ID du workspace (optionnel, pour le mode collaboratif)

        Returns:
            AgentContext prêt à l'emploi
        """
        # Récupérer config LLM depuis la base
        llm_config = await self._get_llm_config(agent_slug)

        llm_service = LLMService(
            provider_slug=llm_config["provider_slug"],
            model_slug=llm_config["model_slug"],
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
        )

        connector_service = ConnectorService(self._connector_registry)
        agent_service = AgentService(self)
        memory_service = MemoryService(session_id, self._session_manager)

        # Stockage scopé: workspace si fourni, sinon user × agent
        storage_service = None
        if self._storage:
            storage_service = StorageService(
                self._storage.scoped(
                    user_id=user_id,
                    agent_slug=agent_slug,
                    workspace_id=workspace_id,
                )
            )

        # ToolService reçoit les services pour construire un ToolContext
        # complet quand un agent exécute un tool
        tool_service = ToolService(
            registry=self._tool_registry,
            user_id=user_id,
            storage=storage_service,
            connectors=connector_service,
            llm=llm_service,
        )

        return AgentContext(
            session_id=session_id,
            user_id=user_id,
            agent_slug=agent_slug,
            llm=llm_service,
            tools=tool_service,
            connectors=connector_service,
            agents=agent_service,
            storage=storage_service,
            memory=memory_service,
            lang=lang,
        )

    async def execute(
        self,
        agent_slug: str,
        message: UserMessage,
        user: Any,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> PipelineResult:
        """
        Exécute un agent avec un message utilisateur.

        Point d'entrée principal pour l'exécution synchrone.

        Args:
            agent_slug: Slug de l'agent
            message: Message utilisateur
            user: Utilisateur courant
            session_id: ID de session (crée une nouvelle si None)
            workspace_id: ID du workspace (optionnel)

        Returns:
            PipelineResult avec la réponse ou l'erreur
        """
        agent = self.get_agent(agent_slug)
        if not agent:
            return PipelineResult(
                success=False,
                error=f"Agent '{agent_slug}' non trouvé",
                error_code="AGENT_NOT_FOUND",
            )

        # Créer ou récupérer la session
        if not session_id:
            session = await self._session_manager.create_session(
                agent_slug=agent_slug, user_id=user.id
            )
            session_id = session.session_id
        else:
            # Le frontend peut fournir un session_id custom ;
            # s'il n'existe pas encore en base, on le crée.
            existing = await self._session_manager.get_session(session_id)
            if not existing:
                await self._session_manager.create_session_with_id(
                    session_id=session_id,
                    agent_slug=agent_slug,
                    user_id=user.id,
                )

        # Construire le contexte (avec la langue préférée de l'utilisateur)
        user_lang = getattr(user, "preferred_language", "en") or "en"
        context = await self.build_context(
            agent_slug=agent_slug,
            user_id=user.id,
            session_id=session_id,
            lang=user_lang,
            workspace_id=workspace_id,
        )

        # Sauvegarder le message utilisateur dans la session
        await self._session_manager.add_message(
            session_id=session_id,
            role="user",
            content=message.content,
        )

        # Exécuter via le pipeline
        result = await self._pipeline.execute(agent, message, context, user)

        # Sauvegarder la réponse dans la session
        if result.success and result.response:
            await self._session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=result.response.content,
            )

        return result

    async def execute_sub_agent(
        self,
        agent_slug: str,
        message: str,
        metadata: Optional[dict] = None,
    ) -> AgentResponse:
        """
        Exécute un sous-agent (appel inter-agents pour l'orchestration).

        Args:
            agent_slug: Slug de l'agent à appeler
            message: Message à envoyer
            metadata: Métadonnées supplémentaires

        Returns:
            AgentResponse de l'agent appelé
        """
        # Pour l'orchestration, on crée un contexte simplifié
        agent = self.get_agent(agent_slug)
        if not agent:
            return AgentResponse(
                content=f"Erreur: agent '{agent_slug}' non trouvé",
                metadata={"error": True},
            )

        user_message = UserMessage(content=message, metadata=metadata or {})
        # Les sous-agents utilisent un contexte parent simplifié
        # TODO: Implémenter le contexte d'orchestration complet
        return AgentResponse(content="", metadata={"error": "not_implemented"})

    async def _get_llm_config(self, agent_slug: str) -> dict[str, Any]:
        """
        Récupère la configuration LLM pour un agent.

        Cherche d'abord une config spécifique à l'agent (table agent_llm_configs),
        sinon utilise la config par défaut (premier provider/model actif).

        Returns:
            Dict avec provider_slug, model_slug, api_key, base_url
        """
        from sqlalchemy import text

        # 1. Chercher une config spécifique à l'agent
        agent_config_result = await self._db.execute(
            text(
                """
                SELECT p.slug as provider_slug, p.base_url, m.slug as model_slug
                FROM agent_llm_configs alc
                JOIN llm_providers p ON p.id = alc.provider_id
                JOIN llm_models m ON m.id = alc.model_id
                WHERE alc.agent_slug = :agent_slug
                  AND alc.is_active = true
                  AND p.is_active = true
                  AND m.is_active = true
                LIMIT 1
                """
            ),
            {"agent_slug": agent_slug},
        )
        row = agent_config_result.fetchone()

        # 2. Fallback: premier provider/model actif qui possède une clé API
        if not row:
            result = await self._db.execute(
                text(
                    """
                    SELECT p.slug as provider_slug, p.base_url, m.slug as model_slug
                    FROM llm_providers p
                    JOIN llm_models m ON m.provider_id = p.id
                    WHERE p.is_active = true AND m.is_active = true
                    ORDER BY p.id ASC, m.id ASC
                    """
                )
            )
            rows = result.fetchall()

            # Prefer the first provider that actually has an API key in Vault
            if self._vault and rows:
                for candidate in rows:
                    try:
                        key = self._vault.get_api_key(candidate.provider_slug) or ""
                    except Exception:
                        key = ""
                    if key:
                        return {
                            "provider_slug": candidate.provider_slug,
                            "model_slug": candidate.model_slug,
                            "api_key": key,
                            "base_url": candidate.base_url or "",
                        }

            # Last resort: return first row even without key (will fail with
            # a clear error message from _validate_config)
            row = rows[0] if rows else None

        if not row:
            return {
                "provider_slug": "default",
                "model_slug": "default",
                "api_key": "",
                "base_url": "",
            }

        # Récupérer la clé API depuis Vault (VaultService est synchrone)
        api_key = ""
        if self._vault:
            try:
                api_key = self._vault.get_api_key(row.provider_slug) or ""
            except Exception as e:
                logger.warning(f"Failed to get API key from Vault: {e}")

        return {
            "provider_slug": row.provider_slug,
            "model_slug": row.model_slug,
            "api_key": api_key,
            "base_url": row.base_url or "",
        }
