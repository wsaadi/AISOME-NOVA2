"""
Framework Testing — Kit de test pour les agents.

Fournit MockContext et AgentTestCase pour tester les agents
sans appels réels aux LLM, tools, connecteurs ou stockage.

Usage:
    from app.framework.testing import MockContext, AgentTestCase

    class TestMonAgent(AgentTestCase):
        agent_class = MonAgent

        async def test_handle_message(self):
            ctx = self.create_context(
                llm_responses=["Voici le résumé..."],
                tool_results={"text-summarizer": ToolResult(success=True, data={...})},
            )
            response = await self.agent.handle_message(
                UserMessage(content="Résume ce doc"), ctx
            )
            assert response.content == "Voici le résumé..."
"""

from app.framework.testing.mock_context import MockContext
from app.framework.testing.test_case import AgentTestCase

__all__ = ["MockContext", "AgentTestCase"]
