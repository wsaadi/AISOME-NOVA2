"""
AgentTestCase — Classe de base pour les tests unitaires d'agents.

Fournit des utilitaires pour instancier l'agent, créer des contextes mockés,
et vérifier les résultats.

Usage:
    import pytest
    from app.framework.testing import AgentTestCase
    from app.framework.schemas import UserMessage

    class TestMonAgent(AgentTestCase):
        agent_class = MonAgent

        @pytest.mark.asyncio
        async def test_basic_response(self):
            ctx = self.create_context(llm_responses=["Bonjour!"])
            response = await self.agent.handle_message(
                UserMessage(content="Salut"), ctx
            )
            assert "Bonjour" in response.content

        @pytest.mark.asyncio
        async def test_uses_tool(self):
            ctx = self.create_context(
                tool_results={"my-tool": ToolResult(success=True, data={"result": 42})}
            )
            response = await self.agent.handle_message(
                UserMessage(content="Calcule"), ctx
            )
            assert ctx.tools.calls[0]["tool"] == "my-tool"
"""

from __future__ import annotations

from typing import Any, Optional, Type

from app.framework.base.agent import BaseAgent
from app.framework.schemas import (
    AgentResponse,
    ConnectorResult,
    SessionMessage,
    ToolResult,
    UserMessage,
)
from app.framework.testing.mock_context import MockContext, create_mock_context


class AgentTestCase:
    """
    Classe de base pour les tests d'agents.

    Sous-classes doivent définir:
        agent_class: Type[BaseAgent] — la classe d'agent à tester

    Fournit:
        self.agent: Instance de l'agent
        self.create_context(): Factory pour MockContext
        self.create_message(): Factory pour UserMessage
    """

    agent_class: Type[BaseAgent]

    def setup_method(self):
        """Initialise l'agent avant chaque test."""
        if not hasattr(self, "agent_class"):
            raise TypeError(
                f"{self.__class__.__name__} doit définir 'agent_class'"
            )
        self.agent = self.agent_class()

    def create_context(
        self,
        llm_responses: list[str] | None = None,
        tool_results: dict[str, ToolResult] | None = None,
        connector_results: dict[str, ConnectorResult] | None = None,
        agent_results: dict[str, AgentResponse] | None = None,
        history: list[SessionMessage] | None = None,
    ) -> MockContext:
        """
        Crée un MockContext pré-configuré pour un test.

        Args:
            llm_responses: Réponses LLM dans l'ordre d'appel
            tool_results: Résultats attendus par slug de tool
            connector_results: Résultats par "slug.action"
            agent_results: Résultats par slug d'agent (orchestration)
            history: Historique de conversation pré-rempli

        Returns:
            MockContext prêt à l'emploi
        """
        ctx = create_mock_context(
            llm_responses=llm_responses,
            tool_results=tool_results,
            connector_results=connector_results,
            agent_results=agent_results,
            history=history,
        )
        ctx.agent_slug = self.agent.manifest.slug
        return ctx

    def create_message(
        self,
        content: str = "Test message",
        metadata: dict[str, Any] | None = None,
    ) -> UserMessage:
        """
        Crée un UserMessage pour un test.

        Args:
            content: Contenu du message
            metadata: Métadonnées optionnelles

        Returns:
            UserMessage
        """
        return UserMessage(content=content, metadata=metadata or {})

    def assert_llm_called(self, ctx: MockContext, times: int = 1) -> None:
        """Vérifie que le LLM a été appelé N fois."""
        assert len(ctx.llm.calls) == times, (
            f"LLM appelé {len(ctx.llm.calls)} fois, attendu {times}"
        )

    def assert_tool_called(
        self, ctx: MockContext, tool_slug: str, times: int = 1
    ) -> None:
        """Vérifie qu'un tool a été appelé N fois."""
        calls = [c for c in ctx.tools.calls if c["tool"] == tool_slug]
        assert len(calls) == times, (
            f"Tool '{tool_slug}' appelé {len(calls)} fois, attendu {times}"
        )

    def assert_connector_called(
        self, ctx: MockContext, connector_slug: str, action: str, times: int = 1
    ) -> None:
        """Vérifie qu'un connecteur.action a été appelé N fois."""
        calls = [
            c
            for c in ctx.connectors.calls
            if c["connector"] == connector_slug and c["action"] == action
        ]
        assert len(calls) == times, (
            f"Connector '{connector_slug}.{action}' appelé {len(calls)} fois, attendu {times}"
        )

    def assert_storage_put(self, ctx: MockContext, key: str) -> None:
        """Vérifie qu'un fichier a été stocké."""
        puts = [c for c in ctx.storage.calls if c["method"] == "put" and c["key"] == key]
        assert len(puts) > 0, f"Aucun storage.put pour la clé '{key}'"
