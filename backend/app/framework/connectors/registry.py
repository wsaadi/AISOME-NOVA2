"""
Connector Registry — Registre centralisé avec auto-discovery des connecteurs.

Même principe que le Tool Registry : ajouter un connecteur = créer un fichier Python.
Le registre le découvre automatiquement au démarrage.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

from app.framework.base.connector import BaseConnector
from app.framework.schemas import ConnectorMetadata, ConnectorResult

logger = logging.getLogger(__name__)

CONNECTORS_ROOT = Path(__file__).parent


class ConnectorRegistry:
    """
    Registre centralisé des connecteurs avec auto-discovery.

    Usage:
        registry = ConnectorRegistry()
        registry.discover()
        connectors = registry.list_connectors()
        result = await registry.execute_connector("salesforce", "get_contacts", {})
    """

    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {}
        self._connected: set[str] = set()

    def discover(self, connectors_dir: Optional[Path] = None) -> int:
        """
        Auto-découvre les connecteurs dans le dossier spécifié.

        Args:
            connectors_dir: Dossier à scanner (défaut: framework/connectors/)

        Returns:
            Nombre de connecteurs découverts
        """
        scan_dir = connectors_dir or CONNECTORS_ROOT
        count = 0

        for py_file in scan_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "registry.py"):
                continue

            try:
                connectors = self._load_connectors_from_file(py_file)
                for connector in connectors:
                    self.register(connector)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load connectors from {py_file.name}: {e}")

        logger.info(f"Connector registry: {count} connectors discovered")
        return count

    def register(self, connector: BaseConnector) -> None:
        """
        Enregistre un connecteur.

        Args:
            connector: Instance de BaseConnector
        """
        slug = connector.metadata.slug
        if slug in self._connectors:
            logger.warning(f"Connector '{slug}' already registered, replacing")
        self._connectors[slug] = connector
        logger.info(f"Connector registered: {slug} v{connector.metadata.version}")

    def unregister(self, slug: str) -> bool:
        """
        Désenregistre un connecteur.

        Args:
            slug: Slug du connecteur

        Returns:
            True si supprimé
        """
        if slug in self._connectors:
            del self._connectors[slug]
            self._connected.discard(slug)
            logger.info(f"Connector unregistered: {slug}")
            return True
        return False

    def get_connector(self, slug: str) -> Optional[BaseConnector]:
        """
        Récupère un connecteur par son slug.

        Args:
            slug: Slug du connecteur

        Returns:
            Instance de BaseConnector ou None
        """
        return self._connectors.get(slug)

    def list_connectors(self) -> list[ConnectorMetadata]:
        """
        Liste tous les connecteurs avec leurs métadonnées.

        Returns:
            Liste de ConnectorMetadata
        """
        return [c.metadata for c in self._connectors.values()]

    def connector_exists(self, slug: str) -> bool:
        """
        Vérifie si un connecteur existe.

        Args:
            slug: Slug du connecteur

        Returns:
            True si enregistré
        """
        return slug in self._connectors

    async def connect(self, slug: str, config: dict[str, Any]) -> bool:
        """
        Initialise la connexion d'un connecteur.

        Args:
            slug: Slug du connecteur
            config: Configuration de connexion

        Returns:
            True si connexion réussie
        """
        connector = self.get_connector(slug)
        if not connector:
            logger.error(f"Connector '{slug}' not found")
            return False

        try:
            await connector.connect(config)
            self._connected.add(slug)
            logger.info(f"Connector connected: {slug}")
            return True
        except Exception as e:
            logger.error(f"Connector connection failed ({slug}): {e}")
            return False

    async def disconnect(self, slug: str) -> None:
        """
        Ferme la connexion d'un connecteur.

        Args:
            slug: Slug du connecteur
        """
        connector = self.get_connector(slug)
        if connector and slug in self._connected:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.warning(f"Connector disconnect error ({slug}): {e}")
            finally:
                self._connected.discard(slug)

    async def disconnect_all(self) -> None:
        """Ferme toutes les connexions actives."""
        for slug in list(self._connected):
            await self.disconnect(slug)

    async def execute_connector(
        self,
        slug: str,
        action: str,
        params: dict[str, Any],
    ) -> ConnectorResult:
        """
        Exécute une action sur un connecteur.

        1. Vérifie que le connecteur existe
        2. Vérifie que l'action est valide
        3. Exécute l'action
        4. Retourne le résultat

        Args:
            slug: Slug du connecteur
            action: Nom de l'action
            params: Paramètres de l'action

        Returns:
            ConnectorResult avec success, data, error
        """
        connector = self.get_connector(slug)
        if not connector:
            return ConnectorResult(
                success=False,
                error=f"Connecteur '{slug}' non trouvé dans le registre",
            )

        if not connector.validate_action(action):
            available = connector.get_available_actions()
            return ConnectorResult(
                success=False,
                error=f"Action '{action}' inconnue. Actions disponibles: {available}",
            )

        try:
            result = await connector.execute(action, params)
            logger.info(f"Connector executed: {slug}.{action} success={result.success}")
            return result
        except Exception as e:
            logger.error(
                f"Connector execution error ({slug}.{action}): {e}", exc_info=True
            )
            return ConnectorResult(
                success=False, error=f"Erreur d'exécution: {str(e)}"
            )

    async def health_check_all(self) -> dict[str, bool]:
        """
        Vérifie la santé de tous les connecteurs connectés.

        Returns:
            Dict slug → is_healthy
        """
        results = {}
        for slug in self._connected:
            connector = self.get_connector(slug)
            if connector:
                try:
                    results[slug] = await connector.health_check()
                except Exception:
                    results[slug] = False
        return results

    def _load_connectors_from_file(self, py_file: Path) -> list[BaseConnector]:
        """Charge les connecteurs depuis un fichier Python."""
        module_name = f"app.framework.connectors.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        connectors = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseConnector)
                and attr is not BaseConnector
            ):
                connectors.append(attr())

        return connectors

    def get_catalog(self) -> list[dict[str, Any]]:
        """
        Retourne le catalogue complet pour l'API et la doc.

        Returns:
            Liste de dicts avec toutes les infos de chaque connecteur
        """
        catalog = []
        for connector in self._connectors.values():
            entry = connector.metadata.model_dump()
            entry["is_connected"] = connector.metadata.slug in self._connected
            catalog.append(entry)
        return catalog
