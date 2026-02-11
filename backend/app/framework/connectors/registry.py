"""
Connector Registry — Registre centralisé avec auto-discovery des connecteurs.

Même principe que le Tool Registry : ajouter un connecteur = créer un fichier Python.
Le registre le découvre automatiquement au démarrage.

Enrichi avec:
- Validation AST au chargement (ConnectorValidator)
- Lazy connection avec Vault
- Catalogue enrichi (is_connected, is_configured)
- Liste par catégorie
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

from app.framework.base.connector import BaseConnector
from app.framework.schemas import ConnectorErrorCode, ConnectorMetadata, ConnectorResult

logger = logging.getLogger(__name__)

CONNECTORS_ROOT = Path(__file__).parent
SKIP_FILES = {"__init__.py", "registry.py", "generator.py", "validator.py"}


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

        Chaque fichier est validé par ConnectorValidator avant chargement.

        Args:
            connectors_dir: Dossier à scanner (défaut: framework/connectors/)

        Returns:
            Nombre de connecteurs découverts
        """
        from app.framework.connectors.validator import ConnectorValidator

        scan_dir = connectors_dir or CONNECTORS_ROOT
        validator = ConnectorValidator()
        count = 0

        for py_file in scan_dir.glob("*.py"):
            if py_file.name in SKIP_FILES:
                continue

            # Valider avant de charger
            validation = validator.validate(py_file)
            if not validation.valid:
                logger.error(
                    f"Connector file {py_file.name} failed validation:\n{validation.summary()}"
                )
                continue

            for warning in validation.warnings:
                logger.warning(f"Connector {py_file.name}: [{warning.code}] {warning.message}")

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

    def list_by_category(self, category: str) -> list[ConnectorMetadata]:
        """
        Liste les connecteurs d'une catégorie.

        Args:
            category: Catégorie (saas, messaging, storage, database, etc.)

        Returns:
            Liste de ConnectorMetadata filtrée
        """
        return [
            c.metadata for c in self._connectors.values()
            if c.metadata.category == category
        ]

    def get_categories(self) -> list[str]:
        """Retourne les catégories disponibles (celles ayant au moins 1 connecteur)."""
        categories = set()
        for connector in self._connectors.values():
            categories.add(connector.metadata.category)
        return sorted(categories)

    def connector_exists(self, slug: str) -> bool:
        """
        Vérifie si un connecteur existe.

        Args:
            slug: Slug du connecteur

        Returns:
            True si enregistré
        """
        return slug in self._connectors

    def is_connected(self, slug: str) -> bool:
        """
        Vérifie si un connecteur est actuellement connecté.

        Args:
            slug: Slug du connecteur

        Returns:
            True si connecté
        """
        return slug in self._connected

    async def connect(self, slug: str, config: dict[str, Any]) -> bool:
        """
        Initialise la connexion d'un connecteur.

        Args:
            slug: Slug du connecteur
            config: Configuration de connexion (provenant de Vault)

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

    async def connect_from_vault(self, slug: str) -> bool:
        """
        Connecte un connecteur en récupérant sa config depuis Vault.

        C'est le mode de connexion normal : le framework gère les credentials.

        Args:
            slug: Slug du connecteur

        Returns:
            True si connexion réussie
        """
        if slug in self._connected:
            return True  # Déjà connecté

        try:
            from app.services.vault import get_vault_service
            vault = get_vault_service()
            config = vault.get_connector_config(slug)
            if config is None:
                logger.warning(f"No Vault config for connector '{slug}'")
                return False
            return await self.connect(slug, config)
        except Exception as e:
            logger.error(f"Vault connection failed for connector '{slug}': {e}")
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

        Si le connecteur n'est pas encore connecté, tente une lazy connection via Vault.

        Args:
            slug: Slug du connecteur
            action: Nom de l'action
            params: Paramètres de l'action

        Returns:
            ConnectorResult avec success, data, error, error_code
        """
        connector = self.get_connector(slug)
        if not connector:
            return ConnectorResult(
                success=False,
                error=f"Connecteur '{slug}' non trouvé dans le registre",
                error_code=ConnectorErrorCode.INVALID_CONFIG,
            )

        if not connector.validate_action(action):
            available = connector.get_available_actions()
            return ConnectorResult(
                success=False,
                error=f"Action '{action}' inconnue. Actions disponibles: {available}",
                error_code=ConnectorErrorCode.INVALID_ACTION,
            )

        # Lazy connection via Vault si pas encore connecté
        if slug not in self._connected:
            connected = await self.connect_from_vault(slug)
            if not connected:
                return ConnectorResult(
                    success=False,
                    error=f"Impossible de connecter '{slug}' — vérifier la config Vault",
                    error_code=ConnectorErrorCode.NOT_CONNECTED,
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
                success=False,
                error=f"Erreur d'exécution: {str(e)}",
                error_code=ConnectorErrorCode.PROCESSING_ERROR,
            )

    async def health_check(self, slug: str) -> dict[str, Any]:
        """
        Vérifie la santé d'un connecteur spécifique.

        Args:
            slug: Slug du connecteur

        Returns:
            Dict avec healthy, message, details
        """
        connector = self.get_connector(slug)
        if not connector:
            return {"healthy": False, "message": f"Connecteur '{slug}' non trouvé"}

        if slug not in self._connected:
            return {"healthy": False, "message": "Non connecté"}

        try:
            is_healthy = await connector.health_check()
            return {
                "healthy": is_healthy,
                "message": "OK" if is_healthy else "Health check failed",
            }
        except Exception as e:
            return {"healthy": False, "message": f"Health check error: {str(e)}"}

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
        import sys as _sys

        module_name = f"app.framework.connectors.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            return []

        module = importlib.util.module_from_spec(spec)
        _sys.modules[module_name] = module
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
            slug = connector.metadata.slug
            entry["is_connected"] = slug in self._connected
            # Vérifier si configuré dans Vault (best-effort)
            entry["is_configured"] = self._check_vault_config(slug)
            catalog.append(entry)
        return catalog

    @staticmethod
    def _check_vault_config(slug: str) -> bool:
        """Vérifie si un connecteur a une config Vault (best-effort, pas d'erreur si Vault down)."""
        try:
            from app.services.vault import get_vault_service
            vault = get_vault_service()
            return vault.has_connector_config(slug)
        except Exception:
            return False
