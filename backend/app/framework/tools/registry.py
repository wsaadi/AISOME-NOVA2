"""
Tool Registry — Registre centralisé avec auto-discovery des tools.

Au démarrage, le registre scanne le dossier framework/tools/ et enregistre
automatiquement toute classe qui étend BaseTool.

Ajouter un tool = créer un fichier Python avec une classe BaseTool. C'est tout.
Supprimer = supprimer le fichier. Le registre se met à jour au prochain redémarrage.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

from app.framework.base.tool import BaseTool
from app.framework.runtime.context import ToolContext
from app.framework.schemas import ToolMetadata, ToolResult

logger = logging.getLogger(__name__)

# Dossier contenant les tools
TOOLS_ROOT = Path(__file__).parent


class ToolRegistry:
    """
    Registre centralisé des tools avec auto-discovery.

    Usage:
        registry = ToolRegistry()
        registry.discover()                    # Auto-discover au démarrage
        tools = registry.list_tools()           # Catalogue complet
        result = await registry.execute_tool("text-summarizer", {"text": "..."})
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def discover(self, tools_dir: Optional[Path] = None) -> int:
        """
        Auto-découvre les tools dans le dossier spécifié.

        Scanne chaque fichier .py (sauf __init__.py et registry.py),
        cherche les classes qui étendent BaseTool, et les enregistre.

        Args:
            tools_dir: Dossier à scanner (défaut: framework/tools/)

        Returns:
            Nombre de tools découverts
        """
        scan_dir = tools_dir or TOOLS_ROOT
        count = 0

        for py_file in scan_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "registry.py"):
                continue

            try:
                tools = self._load_tools_from_file(py_file)
                for tool in tools:
                    self.register(tool)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load tools from {py_file.name}: {e}")

        logger.info(f"Tool registry: {count} tools discovered")
        return count

    def register(self, tool: BaseTool) -> None:
        """
        Enregistre un tool manuellement.

        Args:
            tool: Instance de BaseTool à enregistrer

        Raises:
            ValueError: Si un tool avec le même slug existe déjà
        """
        slug = tool.metadata.slug
        if slug in self._tools:
            logger.warning(f"Tool '{slug}' already registered, replacing")
        self._tools[slug] = tool
        logger.info(f"Tool registered: {slug} v{tool.metadata.version}")

    def unregister(self, slug: str) -> bool:
        """
        Désenregistre un tool.

        Args:
            slug: Slug du tool

        Returns:
            True si le tool existait et a été supprimé
        """
        if slug in self._tools:
            del self._tools[slug]
            logger.info(f"Tool unregistered: {slug}")
            return True
        return False

    def get_tool(self, slug: str) -> Optional[BaseTool]:
        """
        Récupère un tool par son slug.

        Args:
            slug: Slug du tool

        Returns:
            Instance de BaseTool ou None
        """
        return self._tools.get(slug)

    def list_tools(self) -> list[ToolMetadata]:
        """
        Liste tous les tools enregistrés avec leurs métadonnées.

        C'est cette méthode qui alimente:
        - GET /api/tools (catalogue API)
        - La doc auto-générée
        - Le validateur d'agents

        Returns:
            Liste de ToolMetadata
        """
        return [tool.metadata for tool in self._tools.values()]

    def tool_exists(self, slug: str) -> bool:
        """
        Vérifie si un tool existe dans le registre.

        Args:
            slug: Slug du tool

        Returns:
            True si le tool est enregistré
        """
        return slug in self._tools

    async def execute_tool(
        self,
        slug: str,
        params: dict[str, Any],
        context: Optional[ToolContext] = None,
    ) -> ToolResult:
        """
        Exécute un tool par son slug.

        1. Vérifie que le tool existe
        2. Valide les paramètres contre le schema
        3. Exécute le tool
        4. Retourne le résultat

        Args:
            slug: Slug du tool
            params: Paramètres d'entrée
            context: Contexte d'exécution (optionnel)

        Returns:
            ToolResult avec success, data, error
        """
        tool = self.get_tool(slug)
        if not tool:
            return ToolResult(
                success=False, error=f"Tool '{slug}' non trouvé dans le registre"
            )

        # Validation des paramètres
        errors = await tool.validate_params(params)
        if errors:
            return ToolResult(
                success=False,
                error=f"Paramètres invalides: {'; '.join(errors)}",
            )

        # Exécution
        try:
            result = await tool.execute(params, context or ToolContext(user_id=0))
            logger.info(f"Tool executed: {slug} success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Tool execution error ({slug}): {e}", exc_info=True)
            return ToolResult(success=False, error=f"Erreur d'exécution: {str(e)}")

    def _load_tools_from_file(self, py_file: Path) -> list[BaseTool]:
        """
        Charge les tools depuis un fichier Python.

        Args:
            py_file: Chemin du fichier .py

        Returns:
            Liste d'instances de BaseTool trouvées
        """
        module_name = f"app.framework.tools.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tools = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseTool)
                and attr is not BaseTool
            ):
                tools.append(attr())

        return tools

    def get_catalog(self) -> list[dict[str, Any]]:
        """
        Retourne le catalogue complet pour l'API et la doc.

        Returns:
            Liste de dicts avec toutes les infos de chaque tool
        """
        return [tool.metadata.model_dump() for tool in self._tools.values()]
