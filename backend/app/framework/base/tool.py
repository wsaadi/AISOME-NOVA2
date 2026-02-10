"""
BaseTool — Classe abstraite que TOUT tool de la plateforme doit étendre.

Chaque tool est auto-descriptif : il porte ses propres métadonnées (nom, description,
schemas input/output, exemples). Le registre les découvre automatiquement.

Usage:
    from framework.base import BaseTool
    from framework.schemas import ToolMetadata, ToolResult, ToolParameter, ToolExample

    class TextSummarizer(BaseTool):
        @property
        def metadata(self) -> ToolMetadata:
            return ToolMetadata(
                slug="text-summarizer",
                name="Résumeur de texte",
                description="Résume un texte long en points clés",
                input_schema=[
                    ToolParameter(name="text", type="string", required=True),
                    ToolParameter(name="max_points", type="integer", default=5),
                ],
                output_schema=[
                    ToolParameter(name="summary", type="string"),
                    ToolParameter(name="points", type="array"),
                ],
            )

        async def execute(self, params, context):
            text = params["text"]
            # ... logique du tool ...
            return ToolResult(success=True, data={"summary": "...", "points": [...]})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.framework.schemas import ToolMetadata, ToolResult

if TYPE_CHECKING:
    from app.framework.runtime.context import ToolContext


class BaseTool(ABC):
    """
    Classe abstraite de base pour tous les tools.

    Un tool est une fonction réutilisable exposée via API.
    Il est auto-descriptif et auto-découvert par le registre.

    Méthodes obligatoires:
        metadata : Retourne les métadonnées auto-descriptives du tool
        execute  : Exécute le tool avec les paramètres fournis
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """
        Retourne les métadonnées auto-descriptives du tool.

        Utilisées par:
        - Le registre pour l'auto-discovery
        - L'API GET /api/tools pour le catalogue
        - La doc auto-générée AGENT_FRAMEWORK.md
        - Le validateur pour vérifier les dépendances des agents

        Returns:
            ToolMetadata avec slug, name, description, schemas, exemples
        """
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: ToolContext) -> ToolResult:
        """
        Exécute le tool.

        Args:
            params: Paramètres d'entrée (validés contre input_schema par le framework)
            context: Contexte d'exécution du tool (accès aux services plateforme)

        Returns:
            ToolResult avec success, data, et éventuellement error
        """
        ...

    async def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Valide les paramètres d'entrée contre le schema.

        Appelé automatiquement par le framework avant execute().
        Peut être surchargé pour des validations custom.

        Args:
            params: Paramètres à valider

        Returns:
            Liste d'erreurs de validation (vide si OK)
        """
        errors = []
        for param_def in self.metadata.input_schema:
            if param_def.required and param_def.name not in params:
                errors.append(f"Paramètre requis manquant: {param_def.name}")
        return errors
