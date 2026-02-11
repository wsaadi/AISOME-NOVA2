"""
BaseConnector — Classe abstraite que TOUT connecteur de la plateforme doit étendre.

Un connecteur est une intégration avec un service externe (API, BDD, SaaS...).
Il expose des actions (get_contacts, send_email, query...) consommables par les agents.

Chaque connecteur est auto-descriptif et auto-découvert par le registre.

Usage:
    from framework.base import BaseConnector
    from framework.schemas import ConnectorMetadata, ConnectorAction, ConnectorResult

    class SalesforceConnector(BaseConnector):
        @property
        def metadata(self) -> ConnectorMetadata:
            return ConnectorMetadata(
                slug="salesforce",
                name="Salesforce",
                description="Connecteur CRM Salesforce",
                auth_type="oauth2",
                actions=[
                    ConnectorAction(name="get_contacts", description="..."),
                    ConnectorAction(name="create_lead", description="..."),
                ],
            )

        async def connect(self, config):
            self._client = SalesforceClient(config["instance_url"], ...)

        async def execute(self, action, params):
            if action == "get_contacts":
                data = await self._client.get_contacts(**params)
                return ConnectorResult(success=True, data={"contacts": data})

        async def disconnect(self):
            await self._client.close()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.framework.schemas import ConnectorErrorCode, ConnectorMetadata, ConnectorResult


class BaseConnector(ABC):
    """
    Classe abstraite de base pour tous les connecteurs.

    Un connecteur est une intégration avec un service externe, exposée via API.
    Il est auto-descriptif et auto-découvert par le registre.

    Méthodes obligatoires:
        metadata   : Retourne les métadonnées auto-descriptives
        connect    : Initialise la connexion avec la config fournie
        execute    : Exécute une action sur le service externe

    Méthode optionnelle:
        disconnect : Ferme proprement la connexion
    """

    @property
    @abstractmethod
    def metadata(self) -> ConnectorMetadata:
        """
        Retourne les métadonnées auto-descriptives du connecteur.

        Returns:
            ConnectorMetadata avec slug, name, description, auth_type, actions
        """
        ...

    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> None:
        """
        Initialise la connexion au service externe.

        Appelé par le framework au premier usage du connecteur dans une session.
        Les credentials sont récupérées depuis Vault par le framework.

        Args:
            config: Configuration de connexion (URL, tokens, paramètres...)
        """
        ...

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        """
        Exécute une action sur le service externe.

        Args:
            action: Nom de l'action à exécuter (doit être dans metadata.actions)
            params: Paramètres de l'action

        Returns:
            ConnectorResult avec success, data, et éventuellement error

        Raises:
            ValueError: Si l'action n'existe pas dans les actions déclarées
        """
        ...

    async def disconnect(self) -> None:
        """
        Ferme proprement la connexion au service externe.

        Appelé par le framework en fin de session ou en cas d'erreur.
        Par défaut ne fait rien.
        """
        pass

    async def health_check(self) -> bool:
        """
        Vérifie que la connexion au service externe est fonctionnelle.

        Returns:
            True si le service est accessible, False sinon
        """
        return True

    def get_available_actions(self) -> list[str]:
        """
        Retourne la liste des noms d'actions disponibles.

        Returns:
            Liste des noms d'actions
        """
        return [action.name for action in self.metadata.actions]

    def validate_action(self, action: str) -> bool:
        """
        Vérifie qu'une action existe dans les actions déclarées.

        Args:
            action: Nom de l'action à vérifier

        Returns:
            True si l'action existe
        """
        return action in self.get_available_actions()

    def success(self, data: dict[str, Any] | None = None) -> ConnectorResult:
        """
        Helper : retourne un résultat de succès.

        Args:
            data: Données de sortie

        Returns:
            ConnectorResult avec success=True
        """
        return ConnectorResult(success=True, data=data or {})

    def error(
        self,
        message: str,
        code: ConnectorErrorCode | None = None,
    ) -> ConnectorResult:
        """
        Helper : retourne un résultat d'erreur.

        Args:
            message: Message d'erreur
            code: Code d'erreur standardisé

        Returns:
            ConnectorResult avec success=False
        """
        return ConnectorResult(success=False, error=message, error_code=code)
