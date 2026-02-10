"""
MockContext — Simule l'AgentContext pour les tests unitaires.

Permet de tester la logique d'un agent sans:
- Appels LLM réels
- Appels tools/connectors réels
- Accès MinIO réel
- Base de données
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from app.framework.schemas import (
    AgentResponse,
    ConnectorResult,
    SessionMessage,
    ToolMetadata,
    ToolResult,
)


class MockLLMService:
    """
    Mock du service LLM.

    Retourne des réponses prédéfinies dans l'ordre.
    """

    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or ["Mock LLM response"])
        self._call_index = 0
        self.calls: list[dict[str, Any]] = []

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Retourne la prochaine réponse prédéfinie."""
        self.calls.append(
            {
                "method": "chat",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        response = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        return response

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Retourne la prochaine réponse prédéfinie token par token."""
        self.calls.append({"method": "stream", "prompt": prompt})
        response = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        for word in response.split(" "):
            yield word + " "


class MockToolService:
    """
    Mock du service Tools.

    Retourne des résultats prédéfinis par slug de tool.
    """

    def __init__(self, results: dict[str, ToolResult] | None = None):
        self._results = results or {}
        self.calls: list[dict[str, Any]] = []

    async def list(self) -> list[ToolMetadata]:
        """Liste les tools mockés."""
        return []

    async def execute(self, tool_slug: str, params: dict[str, Any]) -> ToolResult:
        """Retourne le résultat prédéfini pour ce tool."""
        self.calls.append({"tool": tool_slug, "params": params})
        if tool_slug in self._results:
            return self._results[tool_slug]
        return ToolResult(success=False, error=f"Mock: tool '{tool_slug}' non configuré")


class MockConnectorService:
    """
    Mock du service Connectors.

    Retourne des résultats prédéfinis par slug.action.
    """

    def __init__(self, results: dict[str, ConnectorResult] | None = None):
        self._results = results or {}
        self.calls: list[dict[str, Any]] = []

    async def list(self) -> list[dict[str, Any]]:
        """Liste les connecteurs mockés."""
        return []

    async def execute(
        self, connector_slug: str, action: str, params: dict[str, Any]
    ) -> ConnectorResult:
        """Retourne le résultat prédéfini."""
        key = f"{connector_slug}.{action}"
        self.calls.append({"connector": connector_slug, "action": action, "params": params})
        if key in self._results:
            return self._results[key]
        return ConnectorResult(success=False, error=f"Mock: '{key}' non configuré")


class MockAgentService:
    """Mock du service inter-agents."""

    def __init__(self, results: dict[str, AgentResponse] | None = None):
        self._results = results or {}
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self, agent_slug: str, message: str, metadata: Optional[dict] = None
    ) -> AgentResponse:
        """Retourne le résultat prédéfini."""
        self.calls.append({"agent": agent_slug, "message": message})
        if agent_slug in self._results:
            return self._results[agent_slug]
        return AgentResponse(content=f"Mock response from {agent_slug}")


class MockStorageService:
    """
    Mock du service Storage.

    Stocke en mémoire au lieu de MinIO.
    """

    def __init__(self):
        self._data: dict[str, bytes] = {}
        self.calls: list[dict[str, Any]] = []

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Stocke en mémoire."""
        self._data[key] = data
        self.calls.append({"method": "put", "key": key, "size": len(data)})
        return key

    async def get(self, key: str) -> Optional[bytes]:
        """Récupère depuis la mémoire."""
        self.calls.append({"method": "get", "key": key})
        return self._data.get(key)

    async def delete(self, key: str) -> bool:
        """Supprime de la mémoire."""
        self.calls.append({"method": "delete", "key": key})
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def list(self, prefix: str = "") -> list[str]:
        """Liste les clés en mémoire."""
        return [k for k in self._data if k.startswith(prefix)]

    async def exists(self, key: str) -> bool:
        """Vérifie l'existence en mémoire."""
        return key in self._data


class MockMemoryService:
    """Mock du service Memory (historique conversation)."""

    def __init__(self, history: list[SessionMessage] | None = None):
        self._history = list(history or [])

    async def get_history(self, limit: Optional[int] = None) -> list[SessionMessage]:
        """Retourne l'historique mocké."""
        if limit:
            return self._history[-limit:]
        return self._history

    async def clear(self) -> None:
        """Efface l'historique."""
        self._history.clear()


@dataclass
class MockContext:
    """
    Mock complet de l'AgentContext pour les tests.

    Usage:
        ctx = MockContext(
            llm_responses=["Réponse 1", "Réponse 2"],
            tool_results={"my-tool": ToolResult(success=True, data={"key": "value"})},
        )
        response = await agent.handle_message(message, ctx)

        # Vérifier les appels
        assert len(ctx.llm.calls) == 1
        assert ctx.tools.calls[0]["tool"] == "my-tool"
    """

    session_id: str = "test-session"
    user_id: int = 1
    agent_slug: str = "test-agent"
    llm: MockLLMService = field(default_factory=MockLLMService)
    tools: MockToolService = field(default_factory=MockToolService)
    connectors: MockConnectorService = field(default_factory=MockConnectorService)
    agents: MockAgentService = field(default_factory=MockAgentService)
    storage: MockStorageService = field(default_factory=MockStorageService)
    memory: MockMemoryService = field(default_factory=MockMemoryService)
    _metadata: dict[str, Any] = field(default_factory=dict)

    def set_progress(self, percent: int, message: str = "") -> None:
        """Mock set_progress."""
        self._metadata["progress"] = percent
        self._metadata["progress_message"] = message


def create_mock_context(
    llm_responses: list[str] | None = None,
    tool_results: dict[str, ToolResult] | None = None,
    connector_results: dict[str, ConnectorResult] | None = None,
    agent_results: dict[str, AgentResponse] | None = None,
    history: list[SessionMessage] | None = None,
) -> MockContext:
    """
    Factory pour créer un MockContext pré-configuré.

    Args:
        llm_responses: Réponses LLM dans l'ordre
        tool_results: Résultats par slug de tool
        connector_results: Résultats par "slug.action"
        agent_results: Résultats par slug d'agent
        history: Historique de conversation

    Returns:
        MockContext configuré
    """
    return MockContext(
        llm=MockLLMService(llm_responses),
        tools=MockToolService(tool_results),
        connectors=MockConnectorService(connector_results),
        agents=MockAgentService(agent_results),
        memory=MockMemoryService(history),
    )
