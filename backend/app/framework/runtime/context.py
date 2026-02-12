"""
AgentContext — Point d'accès UNIQUE aux services de la plateforme pour les agents.

C'est le seul objet que l'agent reçoit. Il ne doit JAMAIS importer
ou accéder à quoi que ce soit d'autre.

Services disponibles via le context:
    context.llm         — Appeler les modèles LLM
    context.tools       — Exécuter des tools de la plateforme
    context.connectors  — Exécuter des actions sur les connecteurs
    context.agents      — Exécuter d'autres agents (orchestration)
    context.storage     — Stockage MinIO (cloisonné user × agent)
    context.memory      — Historique de conversation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from app.framework.schemas import (
    AgentResponse,
    ConnectorResult,
    SessionMessage,
    ToolMetadata,
    ToolResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Service Interfaces (ce que l'agent voit)
# =============================================================================


class LLMService:
    """
    Service d'appel aux modèles LLM.

    L'agent ne choisit pas le provider/modèle — c'est configuré au niveau plateforme.
    Supports both OpenAI-compatible and Anthropic native protocols.
    """

    # Providers that use the Anthropic Messages API (not OpenAI-compatible)
    _ANTHROPIC_PROVIDERS = {"anthropic"}

    def __init__(self, provider_slug: str, model_slug: str, api_key: str, base_url: str):
        self._provider_slug = provider_slug
        self._model_slug = model_slug
        self._api_key = api_key
        self._base_url = base_url
        self._last_usage: dict[str, int] = {"tokens_in": 0, "tokens_out": 0}

    @property
    def provider_slug(self) -> str:
        return self._provider_slug

    @property
    def model_slug(self) -> str:
        return self._model_slug

    @property
    def last_usage(self) -> dict[str, int]:
        """Token usage from the last chat/stream call."""
        return dict(self._last_usage)

    @property
    def _is_anthropic(self) -> bool:
        return self._provider_slug in self._ANTHROPIC_PROVIDERS

    def _validate_config(self) -> None:
        if not self._base_url:
            raise ValueError(
                "LLM base_url is not configured. "
                "Please configure an LLM provider in Settings > LLM Providers."
            )
        if not self._api_key:
            raise ValueError(
                f"No API key found for provider '{self._provider_slug}'. "
                "Please set the API key in Settings > LLM Providers."
            )

    # ------------------------------------------------------------------
    # Anthropic Messages API
    # ------------------------------------------------------------------

    async def _chat_anthropic(
        self, prompt: str, system_prompt: Optional[str],
        temperature: float, max_tokens: int,
    ) -> str:
        import httpx

        url = f"{self._base_url}/v1/messages"
        logger.info(
            f"LLM call [anthropic] → POST {url} "
            f"(model={self._model_slug}, max_tokens={max_tokens})"
        )

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model_slug,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        llm_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=llm_timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.ReadTimeout:
                raise ValueError(
                    f"Anthropic request timed out after 300s "
                    f"(model={self._model_slug}, max_tokens={max_tokens})."
                )
            except httpx.ConnectError as e:
                raise ValueError(
                    f"Cannot connect to Anthropic API at {url}: {e}"
                )
            except httpx.HTTPError as e:
                raise ValueError(
                    f"HTTP error calling Anthropic API at {url}: "
                    f"{type(e).__name__}: {e}"
                )

            if response.status_code != 200:
                body = response.text[:500]
                logger.error(
                    f"Anthropic API returned {response.status_code}: {body}"
                )
                raise ValueError(
                    f"Anthropic API error {response.status_code}: {body}"
                )

            data = response.json()

        usage = data.get("usage", {})
        self._last_usage = {
            "tokens_in": usage.get("input_tokens", 0),
            "tokens_out": usage.get("output_tokens", 0),
        }
        content_blocks = data.get("content", [])
        return "\n".join(
            b["text"] for b in content_blocks if b.get("type") == "text"
        )

    async def _stream_anthropic(
        self, prompt: str, system_prompt: Optional[str],
        temperature: float, max_tokens: int,
    ) -> AsyncIterator[str]:
        import httpx
        import json as _json

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model_slug,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        llm_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=llm_timeout) as client:
            async with client.stream(
                "POST", f"{self._base_url}/v1/messages",
                headers=headers, json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    event = _json.loads(raw)
                    event_type = event.get("type", "")
                    if event_type == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif event_type == "message_delta":
                        usage = event.get("usage", {})
                        if usage:
                            self._last_usage = {
                                "tokens_in": usage.get("input_tokens", 0),
                                "tokens_out": usage.get("output_tokens", 0),
                            }

    # ------------------------------------------------------------------
    # OpenAI-compatible API (default)
    # ------------------------------------------------------------------

    async def _chat_openai(
        self, prompt: str, system_prompt: Optional[str],
        temperature: float, max_tokens: int,
    ) -> str:
        import httpx

        url = f"{self._base_url}/chat/completions"
        logger.info(
            f"LLM call [openai-compat] → POST {url} "
            f"(model={self._model_slug}, max_tokens={max_tokens})"
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_slug,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        llm_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=llm_timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.ReadTimeout:
                raise ValueError(
                    f"LLM request timed out after 300s "
                    f"(model={self._model_slug}, max_tokens={max_tokens})."
                )
            except httpx.ConnectError as e:
                raise ValueError(
                    f"Cannot connect to LLM API at {url}: {e}"
                )
            except httpx.HTTPError as e:
                raise ValueError(
                    f"HTTP error calling LLM API at {url}: "
                    f"{type(e).__name__}: {e}"
                )

            if response.status_code != 200:
                body = response.text[:500]
                logger.error(f"LLM API returned {response.status_code}: {body}")
                raise ValueError(
                    f"LLM API error {response.status_code}: {body}"
                )

            data = response.json()

        usage = data.get("usage", {})
        self._last_usage = {
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
        }
        return data["choices"][0]["message"]["content"]

    async def _stream_openai(
        self, prompt: str, system_prompt: Optional[str],
        temperature: float, max_tokens: int,
    ) -> AsyncIterator[str]:
        import httpx
        import json as _json

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_slug,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        llm_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=llm_timeout) as client:
            async with client.stream(
                "POST", f"{self._base_url}/chat/completions",
                headers=headers, json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = _json.loads(line[6:])
                        usage = chunk.get("usage")
                        if usage:
                            self._last_usage = {
                                "tokens_in": usage.get("prompt_tokens", 0),
                                "tokens_out": usage.get("completion_tokens", 0),
                            }
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    # ------------------------------------------------------------------
    # Public interface (dispatches to the right protocol)
    # ------------------------------------------------------------------

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Appel LLM non-streamé.

        Dispatches to Anthropic Messages API or OpenAI-compatible endpoint
        depending on the configured provider.
        """
        self._validate_config()
        if self._is_anthropic:
            return await self._chat_anthropic(prompt, system_prompt, temperature, max_tokens)
        return await self._chat_openai(prompt, system_prompt, temperature, max_tokens)

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """
        Appel LLM streamé — retourne les tokens un par un.

        Dispatches to Anthropic Messages API or OpenAI-compatible endpoint
        depending on the configured provider.
        """
        self._validate_config()
        if self._is_anthropic:
            async for token in self._stream_anthropic(prompt, system_prompt, temperature, max_tokens):
                yield token
        else:
            async for token in self._stream_openai(prompt, system_prompt, temperature, max_tokens):
                yield token


class ToolService:
    """
    Service d'exécution des tools de la plateforme.

    Les tools sont des fonctions centralisées, auto-découvertes par le registre.
    """

    def __init__(self, registry: Any):
        self._registry = registry

    async def list(self) -> list[ToolMetadata]:
        """
        Liste tous les tools disponibles avec leurs schemas.

        Returns:
            Liste de ToolMetadata
        """
        return self._registry.list_tools()

    async def execute(self, tool_slug: str, params: dict[str, Any]) -> ToolResult:
        """
        Exécute un tool par son slug.

        Args:
            tool_slug: Identifiant unique du tool
            params: Paramètres d'entrée (validés contre le schema du tool)

        Returns:
            ToolResult avec success, data, error

        Raises:
            ValueError: Si le tool n'existe pas dans le registre
        """
        return await self._registry.execute_tool(tool_slug, params)


class ConnectorService:
    """
    Service d'exécution des connecteurs de la plateforme.

    Les connecteurs sont des intégrations avec des services externes.
    """

    def __init__(self, registry: Any):
        self._registry = registry

    async def list(self) -> list[dict[str, Any]]:
        """
        Liste tous les connecteurs disponibles.

        Returns:
            Liste des métadonnées de connecteurs
        """
        return self._registry.list_connectors()

    async def execute(
        self, connector_slug: str, action: str, params: dict[str, Any]
    ) -> ConnectorResult:
        """
        Exécute une action sur un connecteur.

        Args:
            connector_slug: Identifiant unique du connecteur
            action: Nom de l'action à exécuter
            params: Paramètres de l'action

        Returns:
            ConnectorResult avec success, data, error

        Raises:
            ValueError: Si le connecteur ou l'action n'existe pas
        """
        return await self._registry.execute_connector(connector_slug, action, params)


class AgentService:
    """
    Service d'appel inter-agents (orchestration).

    Permet à un agent d'appeler un autre agent.
    """

    def __init__(self, engine: Any):
        self._engine = engine

    async def execute(
        self, agent_slug: str, message: str, metadata: Optional[dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Exécute un autre agent avec un message.

        Args:
            agent_slug: Slug de l'agent à appeler
            message: Message à envoyer à l'agent
            metadata: Métadonnées supplémentaires

        Returns:
            AgentResponse de l'agent appelé
        """
        return await self._engine.execute_sub_agent(agent_slug, message, metadata)


class StorageService:
    """
    Service de stockage MinIO — cloisonné automatiquement par user × agent.

    L'agent ne connaît pas le chemin réel. Le framework scope tout automatiquement
    vers: users/{user_id}/agents/{agent_slug}/
    """

    def __init__(self, agent_storage: Any):
        self._storage = agent_storage

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Stocke un fichier.

        Args:
            key: Chemin relatif (ex: "outputs/report.pdf")
            data: Contenu du fichier en bytes
            content_type: Type MIME du fichier

        Returns:
            Chemin complet dans MinIO (pour référence)
        """
        return await self._storage.put(key, data, content_type)

    async def get(self, key: str) -> Optional[bytes]:
        """
        Récupère un fichier.

        Args:
            key: Chemin relatif (ex: "outputs/report.pdf")

        Returns:
            Contenu du fichier en bytes, ou None si introuvable
        """
        return await self._storage.get(key)

    async def delete(self, key: str) -> bool:
        """
        Supprime un fichier.

        Args:
            key: Chemin relatif

        Returns:
            True si supprimé, False si introuvable
        """
        return await self._storage.delete(key)

    async def list(self, prefix: str = "") -> list[str]:
        """
        Liste les fichiers avec un préfixe.

        Args:
            prefix: Préfixe de recherche (ex: "outputs/")

        Returns:
            Liste des chemins relatifs
        """
        return await self._storage.list(prefix)

    async def exists(self, key: str) -> bool:
        """
        Vérifie si un fichier existe.

        Args:
            key: Chemin relatif

        Returns:
            True si le fichier existe
        """
        return await self._storage.exists(key)


class MemoryService:
    """
    Service d'historique de conversation.

    Fournit l'accès à l'historique des messages de la session courante.
    """

    def __init__(self, session_id: str, session_manager: Any):
        self._session_id = session_id
        self._session_manager = session_manager

    async def get_history(self, limit: Optional[int] = None) -> list[SessionMessage]:
        """
        Récupère l'historique de la session courante.

        Args:
            limit: Nombre max de messages (None = tous)

        Returns:
            Liste de SessionMessage ordonnés chronologiquement
        """
        return await self._session_manager.get_messages(self._session_id, limit)

    async def clear(self) -> None:
        """Efface l'historique de la session courante."""
        await self._session_manager.clear_messages(self._session_id)


# =============================================================================
# Contexts
# =============================================================================


@dataclass
class AgentContext:
    """
    Contexte d'exécution fourni à chaque agent.

    C'est le SEUL objet que l'agent reçoit. Tous les accès aux services
    de la plateforme passent par ce context.

    Attributes:
        session_id: Identifiant de la session de conversation
        user_id: Identifiant de l'utilisateur
        agent_slug: Slug de l'agent en cours d'exécution
        llm: Service d'appel aux modèles LLM
        tools: Service d'exécution des tools
        connectors: Service d'exécution des connecteurs
        agents: Service d'appel inter-agents
        storage: Service de stockage MinIO (cloisonné user × agent)
        memory: Service d'historique de conversation
    """

    session_id: str
    user_id: int
    agent_slug: str
    llm: LLMService
    tools: ToolService
    connectors: ConnectorService
    agents: AgentService
    storage: Optional[StorageService] = None
    memory: Optional[MemoryService] = None
    lang: str = "en"
    _metadata: dict[str, Any] = field(default_factory=dict)

    def set_progress(self, percent: int, message: str = "") -> None:
        """
        Met à jour la progression du job (visible côté frontend).

        Args:
            percent: Pourcentage de progression (0-100)
            message: Message de statut optionnel
        """
        self._metadata["progress"] = max(0, min(100, percent))
        self._metadata["progress_message"] = message


@dataclass
class ToolContext:
    """
    Contexte d'exécution fourni aux tools.

    Plus restreint que AgentContext — un tool n'a pas accès aux autres agents
    ni à la mémoire de conversation.

    Services disponibles:
        context.user_id      → ID de l'utilisateur qui exécute
        context.storage      → Accès MinIO (read/write, scopé user)
        context.connectors   → Accès aux connecteurs (execute)
        context.llm          → Accès LLM plateforme (chat/stream)
        context.progress()   → Callback progression (async tools)
        context.logger       → Logger structuré du tool

    Un tool ne reçoit RIEN d'autre. Pas d'accès filesystem, pas d'accès
    réseau direct, pas d'accès DB, pas d'accès aux autres agents.
    """

    user_id: int
    storage: Optional[StorageService] = None
    connectors: Optional[ConnectorService] = None
    llm: Optional[LLMService] = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("tool"))
    _progress_callback: Optional[Any] = field(default=None, repr=False)

    def progress(self, percent: int, message: str = "") -> None:
        """
        Publie la progression d'un tool async.

        Utilisé uniquement par les tools en mode async.
        Le framework route vers Redis pub/sub → WebSocket → frontend.

        Args:
            percent: Pourcentage de progression (0-100)
            message: Message de statut optionnel
        """
        clamped = max(0, min(100, percent))
        self.logger.info(f"Progress: {clamped}% - {message}")
        if self._progress_callback:
            self._progress_callback(clamped, message)
