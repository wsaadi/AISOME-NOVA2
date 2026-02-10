"""
Agent: Template Agent
Description: Agent template — point de départ pour tout nouvel agent.

Ce fichier sert de modèle. Copiez ce dossier et adaptez-le à votre besoin.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from app.framework.base import BaseAgent
from app.framework.schemas import (
    AgentManifest,
    AgentResponse,
    AgentResponseChunk,
    UserMessage,
)

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext


class TemplateAgent(BaseAgent):
    """
    Agent template — point de départ pour tout nouvel agent.

    Workflow:
        1. Reçoit le message de l'utilisateur
        2. Charge le system prompt depuis prompts/system.md
        3. Envoie au LLM via context.llm
        4. Retourne la réponse

    Pour créer un nouvel agent:
        1. Copiez ce dossier
        2. Renommez la classe et le slug
        3. Modifiez manifest.json
        4. Adaptez handle_message() à votre logique métier
        5. Modifiez prompts/system.md
        6. Validez: python -m app.framework.validator backend/app/agents/{slug}/
    """

    @property
    def manifest(self) -> AgentManifest:
        """Retourne le manifeste de l'agent depuis manifest.json."""
        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        return AgentManifest(**data)

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """
        Traite un message utilisateur.

        Args:
            message: Message de l'utilisateur (texte + pièces jointes)
            context: Contexte d'exécution framework (llm, tools, connectors, storage, memory)

        Returns:
            AgentResponse avec le contenu de la réponse
        """
        # Charger le system prompt
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text()

        # Récupérer l'historique pour le contexte
        history = await context.memory.get_history(limit=10)

        # Construire le prompt avec l'historique
        conversation = ""
        for msg in history:
            conversation += f"{msg.role}: {msg.content}\n"
        conversation += f"user: {message.content}"

        # Appeler le LLM
        response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
        )

        return AgentResponse(content=response)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Version streaming — envoie les tokens au fur et à mesure.

        Args:
            message: Message de l'utilisateur
            context: Contexte d'exécution framework

        Yields:
            AgentResponseChunk avec les tokens progressifs
        """
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text()

        async for token in context.llm.stream(
            prompt=message.content,
            system_prompt=system_prompt,
        ):
            yield AgentResponseChunk(content=token)

        yield AgentResponseChunk(content="", is_final=True)

    async def on_session_start(self, context: AgentContext) -> None:
        """Hook de début de session — initialisation optionnelle."""
        pass

    async def on_session_end(self, context: AgentContext) -> None:
        """Hook de fin de session — nettoyage optionnel."""
        pass
