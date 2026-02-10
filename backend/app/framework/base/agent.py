"""
BaseAgent — Classe abstraite que TOUT agent doit étendre.

Un agent n'a qu'une seule responsabilité : implémenter handle_message().
Tout le reste (auth, modération, quotas, logging) est géré par le pipeline framework.

Usage:
    from framework.base import BaseAgent
    from framework.schemas import AgentManifest, UserMessage, AgentResponse, AgentResponseChunk

    class MonAgent(BaseAgent):
        @property
        def manifest(self) -> AgentManifest:
            return AgentManifest(name="Mon Agent", slug="mon-agent", ...)

        async def handle_message(self, message, context):
            response = await context.llm.chat(message.content)
            return AgentResponse(content=response)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator

from app.framework.schemas import AgentManifest, AgentResponse, AgentResponseChunk, UserMessage

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext


class BaseAgent(ABC):
    """
    Classe abstraite de base pour tous les agents.

    Méthodes obligatoires:
        manifest    : Retourne les métadonnées de l'agent (AgentManifest)
        handle_message : Traite un message utilisateur et retourne une réponse

    Hooks optionnels:
        on_session_start : Appelé au démarrage d'une nouvelle session
        on_session_end   : Appelé à la fin d'une session

    Méthode optionnelle:
        handle_message_stream : Version streaming de handle_message (token par token)

    INTERDIT:
        - Importer des libs externes (requests, httpx, os, subprocess...)
        - Accéder au filesystem directement
        - Faire des appels HTTP directs
        - Tout accès se fait via le context fourni par le framework
    """

    @property
    @abstractmethod
    def manifest(self) -> AgentManifest:
        """
        Retourne le manifeste de l'agent.

        Returns:
            AgentManifest avec name, slug, version, description, dependencies, etc.
        """
        ...

    @abstractmethod
    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """
        Traite un message utilisateur — POINT D'ENTRÉE UNIQUE de la logique métier.

        C'est ici que le dev met toute sa logique :
        - Appels LLM via context.llm
        - Appels tools via context.tools
        - Appels connecteurs via context.connectors
        - Lecture/écriture stockage via context.storage
        - Lecture historique via context.memory

        Args:
            message: Message de l'utilisateur (texte + pièces jointes)
            context: Contexte d'exécution (seul point d'accès aux services)

        Returns:
            AgentResponse avec le contenu de la réponse + éventuelles pièces jointes
        """
        ...

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Version streaming de handle_message — optionnel.

        Si implémenté, le framework utilisera cette méthode pour streamer
        les tokens au frontend via WebSocket en temps réel.

        Par défaut, fait un appel non-streamé et retourne le résultat en un bloc.

        Args:
            message: Message de l'utilisateur
            context: Contexte d'exécution

        Yields:
            AgentResponseChunk avec les tokens au fur et à mesure
        """
        response = await self.handle_message(message, context)
        yield AgentResponseChunk(content=response.content, is_final=True, metadata=response.metadata)

    async def on_session_start(self, context: AgentContext) -> None:
        """
        Hook appelé au démarrage d'une nouvelle session de conversation.

        Utile pour initialiser des données, charger un contexte, etc.
        Par défaut ne fait rien.

        Args:
            context: Contexte d'exécution
        """
        pass

    async def on_session_end(self, context: AgentContext) -> None:
        """
        Hook appelé à la fin d'une session de conversation.

        Utile pour sauvegarder des données, nettoyer des ressources, etc.
        Par défaut ne fait rien.

        Args:
            context: Contexte d'exécution
        """
        pass

    def __init_subclass__(cls, **kwargs):
        """Vérifie à la déclaration que la sous-classe respecte le contrat."""
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):
            if not hasattr(cls, "manifest"):
                raise TypeError(f"{cls.__name__} doit définir la propriété 'manifest'")
            if not hasattr(cls, "handle_message"):
                raise TypeError(f"{cls.__name__} doit implémenter 'handle_message'")
