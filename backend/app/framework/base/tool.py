"""
BaseTool — Classe abstraite que TOUT tool de la plateforme doit étendre.

Chaque tool est auto-descriptif : il porte ses propres métadonnées (nom, description,
schemas input/output, exemples, catégorie, mode d'exécution, connecteurs requis).
Le registre les découvre automatiquement.

Un tool est de la LOGIQUE PURE :
- Jamais d'appel réseau direct → utiliser context.connectors
- Jamais d'accès filesystem → utiliser context.storage
- Jamais de secret en dur → les secrets vivent dans les connecteurs

Usage:
    from app.framework.base import BaseTool
    from app.framework.schemas import (
        ToolMetadata, ToolResult, ToolParameter, ToolExample,
        ToolExecutionMode, ToolErrorCode, HealthCheckResult,
    )

    class TextSummarizer(BaseTool):
        @property
        def metadata(self) -> ToolMetadata:
            return ToolMetadata(
                slug="text-summarizer",
                name="Résumeur de texte",
                description="Résume un texte long en points clés",
                category="text",
                execution_mode=ToolExecutionMode.SYNC,
                timeout_seconds=30,
                input_schema=[
                    ToolParameter(name="text", type="string", required=True),
                    ToolParameter(name="max_points", type="integer", default=5),
                ],
                output_schema=[
                    ToolParameter(name="summary", type="string"),
                    ToolParameter(name="points", type="array"),
                ],
                examples=[
                    ToolExample(
                        description="Résumé basique",
                        input={"text": "Long texte...", "max_points": 3},
                        output={"summary": "...", "points": ["...", "...", "..."]},
                    ),
                ],
            )

        async def execute(self, params, context):
            text = params["text"]
            summary = await context.llm.chat(f"Résume en points clés: {text}")
            return ToolResult(success=True, data={"summary": summary, "points": []})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.framework.schemas import HealthCheckResult, ToolErrorCode, ToolMetadata, ToolResult

if TYPE_CHECKING:
    from app.framework.runtime.context import ToolContext


class BaseTool(ABC):
    """
    Classe abstraite de base pour tous les tools.

    Un tool est une fonction réutilisable exposée via API.
    Il est auto-descriptif et auto-découvert par le registre.

    Règles absolues :
        - Jamais d'import os, subprocess, requests, httpx, socket
        - Jamais de open(), exec(), eval()
        - Jamais de secret en dur
        - Jamais d'appel réseau direct → context.connectors
        - Jamais d'accès filesystem → context.storage

    Méthodes obligatoires:
        metadata : Retourne les métadonnées auto-descriptives du tool
        execute  : Exécute le tool avec les paramètres fournis

    Méthodes optionnelles (overridable):
        validate_params : Validation custom des paramètres
        health_check    : Vérifie que le tool est opérationnel
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """
        Retourne les métadonnées auto-descriptives du tool.

        Utilisées par:
        - Le registre pour l'auto-discovery
        - L'API GET /api/tools pour le catalogue
        - La doc auto-générée TOOL_FRAMEWORK.md
        - Le validateur pour vérifier les dépendances des agents

        Returns:
            ToolMetadata avec slug, name, description, category, mode, schemas, exemples
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
            ToolResult avec success, data, et éventuellement error + error_code

        Important:
            - Pour les erreurs métier, retourner ToolResult(success=False, error_code=...)
            - Ne JAMAIS lever d'exception pour des erreurs attendues
            - Les exceptions non-catchées sont interceptées par le framework
        """
        ...

    async def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Valide les paramètres d'entrée contre le schema.

        Appelé automatiquement par le framework avant execute().
        Peut être surchargé pour des validations custom.

        La validation de base vérifie :
        - Présence des paramètres requis
        - Types basiques (string, integer, number, boolean)

        Args:
            params: Paramètres à valider

        Returns:
            Liste d'erreurs de validation (vide si OK)
        """
        errors = []
        for param_def in self.metadata.input_schema:
            value = params.get(param_def.name)

            # Vérifier les paramètres requis
            if param_def.required and value is None:
                errors.append(f"Paramètre requis manquant: {param_def.name}")
                continue

            # Vérifier les types si la valeur est présente
            if value is not None:
                type_error = self._check_type(param_def.name, value, param_def.type)
                if type_error:
                    errors.append(type_error)

        return errors

    async def health_check(self) -> HealthCheckResult:
        """
        Vérifie que le tool est opérationnel.

        Par défaut, retourne healthy=True.
        Surcharger pour vérifier les connecteurs requis, les dépendances internes, etc.

        Exposé via l'API GET /api/tools/health.

        Returns:
            HealthCheckResult avec healthy, message, details
        """
        return HealthCheckResult(healthy=True, message="OK")

    @staticmethod
    def _check_type(name: str, value: Any, expected_type: str) -> str | None:
        """Vérifie le type d'un paramètre."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected and not isinstance(value, expected):
            return f"Paramètre '{name}': type '{type(value).__name__}' reçu, '{expected_type}' attendu"
        return None

    @staticmethod
    def error(
        message: str,
        code: ToolErrorCode,
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        Helper pour créer un ToolResult d'erreur standardisé.

        Usage dans execute():
            if not text:
                return self.error("Le texte est vide", ToolErrorCode.INVALID_PARAMS)

        Args:
            message: Message d'erreur humain
            code: Code d'erreur standardisé
            data: Données supplémentaires optionnelles

        Returns:
            ToolResult avec success=False et error_code
        """
        return ToolResult(
            success=False,
            error=message,
            error_code=code,
            data=data or {},
        )

    @staticmethod
    def success(data: dict[str, Any] | None = None) -> ToolResult:
        """
        Helper pour créer un ToolResult de succès.

        Usage dans execute():
            return self.success({"summary": "...", "points": [...]})

        Args:
            data: Données de résultat

        Returns:
            ToolResult avec success=True
        """
        return ToolResult(success=True, data=data or {})
