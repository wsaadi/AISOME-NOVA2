"""
ToolTestCase — Classe de base pour les tests unitaires de tools.

Fournit des utilitaires pour instancier le tool, créer des contextes mockés,
et vérifier les résultats.

Usage:
    import pytest
    from app.framework.testing import ToolTestCase
    from app.framework.schemas import ToolResult, ConnectorResult

    class TestTextSummarizer(ToolTestCase):
        tool_class = TextSummarizer

        @pytest.mark.asyncio
        async def test_basic_summary(self):
            ctx = self.create_context(
                llm_responses=["Point 1. Point 2. Point 3."],
            )
            result = await self.tool.execute(
                {"text": "Long texte...", "max_points": 3}, ctx
            )
            assert result.success
            assert "points" in result.data

        @pytest.mark.asyncio
        async def test_missing_required_param(self):
            errors = await self.tool.validate_params({})
            assert any("text" in e for e in errors)

        @pytest.mark.asyncio
        async def test_uses_connector(self):
            ctx = self.create_context(
                connector_results={
                    "google-translate.translate": ConnectorResult(
                        success=True, data={"translated": "Hello"}
                    )
                },
            )
            result = await self.tool.execute(
                {"text": "Bonjour", "target_lang": "en"}, ctx
            )
            self.assert_connector_called(ctx, "google-translate", "translate")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional, Type

from app.framework.base.tool import BaseTool
from app.framework.schemas import (
    ConnectorResult,
    HealthCheckResult,
    ToolMetadata,
    ToolResult,
)


# =============================================================================
# Mock Services pour ToolContext
# =============================================================================


class MockToolLLMService:
    """
    Mock du service LLM pour les tools.

    Retourne des réponses prédéfinies dans l'ordre.
    """

    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or ["Mock LLM response"])
        self._call_index = 0
        self.calls: list[dict[str, Any]] = []

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Retourne la prochaine réponse prédéfinie."""
        self.calls.append(
            {
                "method": "chat",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        response = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        return response

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Retourne la prochaine réponse token par token."""
        self.calls.append({"method": "stream", "prompt": prompt})
        response = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        for word in response.split(" "):
            yield word + " "


class MockToolConnectorService:
    """
    Mock du service Connectors pour les tools.

    Retourne des résultats prédéfinis par "slug.action".
    """

    def __init__(self, results: dict[str, ConnectorResult] | None = None):
        self._results = results or {}
        self.calls: list[dict[str, Any]] = []

    async def list(self) -> list[dict[str, Any]]:
        """Liste les connecteurs mockés."""
        return []

    async def execute(
        self, connector_slug: str, action: str, params: dict[str, Any]
    ) -> ConnectorResult:
        """Retourne le résultat prédéfini."""
        key = f"{connector_slug}.{action}"
        self.calls.append({"connector": connector_slug, "action": action, "params": params})
        if key in self._results:
            return self._results[key]
        return ConnectorResult(success=False, error=f"Mock: '{key}' non configuré")


class MockToolStorageService:
    """
    Mock du service Storage pour les tools.

    Stocke en mémoire au lieu de MinIO.
    """

    def __init__(self):
        self._data: dict[str, bytes] = {}
        self.calls: list[dict[str, Any]] = []

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Stocke en mémoire."""
        self._data[key] = data
        self.calls.append({"method": "put", "key": key, "size": len(data)})
        return key

    async def get(self, key: str) -> Optional[bytes]:
        """Récupère depuis la mémoire."""
        self.calls.append({"method": "get", "key": key})
        return self._data.get(key)

    async def delete(self, key: str) -> bool:
        """Supprime de la mémoire."""
        self.calls.append({"method": "delete", "key": key})
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def list(self, prefix: str = "") -> list[str]:
        """Liste les clés en mémoire."""
        return [k for k in self._data if k.startswith(prefix)]

    async def exists(self, key: str) -> bool:
        """Vérifie l'existence en mémoire."""
        return key in self._data


# =============================================================================
# MockToolContext
# =============================================================================


@dataclass
class MockToolContext:
    """
    Mock complet du ToolContext pour les tests de tools.

    Usage:
        ctx = MockToolContext(
            llm_responses=["Résumé du texte"],
            connector_results={
                "google-translate.translate": ConnectorResult(success=True, data={...})
            },
        )
        result = await tool.execute({"text": "..."}, ctx)

        # Vérifier les appels
        assert len(ctx.llm.calls) == 1
        assert ctx.connectors.calls[0]["connector"] == "google-translate"
    """

    user_id: int = 1
    storage: MockToolStorageService = field(default_factory=MockToolStorageService)
    connectors: MockToolConnectorService = field(default_factory=MockToolConnectorService)
    llm: MockToolLLMService = field(default_factory=MockToolLLMService)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("test.tool"))
    _progress_history: list[dict[str, Any]] = field(default_factory=list)

    def progress(self, percent: int, message: str = "") -> None:
        """Enregistre les appels de progression pour vérification."""
        self._progress_history.append({"percent": percent, "message": message})


def create_mock_tool_context(
    llm_responses: list[str] | None = None,
    connector_results: dict[str, ConnectorResult] | None = None,
    storage_data: dict[str, bytes] | None = None,
) -> MockToolContext:
    """
    Factory pour créer un MockToolContext pré-configuré.

    Args:
        llm_responses: Réponses LLM dans l'ordre
        connector_results: Résultats par "slug.action"
        storage_data: Fichiers pré-existants dans le storage

    Returns:
        MockToolContext configuré
    """
    ctx = MockToolContext(
        llm=MockToolLLMService(llm_responses),
        connectors=MockToolConnectorService(connector_results),
    )
    if storage_data:
        ctx.storage._data = dict(storage_data)
    return ctx


# =============================================================================
# ToolTestCase
# =============================================================================


class ToolTestCase:
    """
    Classe de base pour les tests de tools.

    Sous-classes doivent définir:
        tool_class: Type[BaseTool] — la classe de tool à tester

    Fournit:
        self.tool: Instance du tool
        self.create_context(): Factory pour MockToolContext
        Méthodes d'assertion helper
    """

    tool_class: Type[BaseTool]

    def setup_method(self):
        """Initialise le tool avant chaque test."""
        if not hasattr(self, "tool_class"):
            raise TypeError(
                f"{self.__class__.__name__} doit définir 'tool_class'"
            )
        self.tool = self.tool_class()

    def create_context(
        self,
        llm_responses: list[str] | None = None,
        connector_results: dict[str, ConnectorResult] | None = None,
        storage_data: dict[str, bytes] | None = None,
    ) -> MockToolContext:
        """
        Crée un MockToolContext pré-configuré pour un test.

        Args:
            llm_responses: Réponses LLM dans l'ordre d'appel
            connector_results: Résultats par "slug.action"
            storage_data: Fichiers pré-existants dans le storage

        Returns:
            MockToolContext prêt à l'emploi
        """
        return create_mock_tool_context(
            llm_responses=llm_responses,
            connector_results=connector_results,
            storage_data=storage_data,
        )

    # --- Assertions ---

    def assert_success(self, result: ToolResult) -> None:
        """Vérifie que le résultat est un succès."""
        assert result.success, f"Expected success but got error: {result.error}"

    def assert_error(self, result: ToolResult, error_code: str | None = None) -> None:
        """Vérifie que le résultat est une erreur."""
        assert not result.success, "Expected error but got success"
        if error_code and result.error_code:
            assert result.error_code.value == error_code, (
                f"Expected error_code '{error_code}' but got '{result.error_code.value}'"
            )

    def assert_data_has(self, result: ToolResult, *keys: str) -> None:
        """Vérifie que le résultat contient les clés spécifiées."""
        for key in keys:
            assert key in result.data, f"Clé '{key}' absente du résultat: {list(result.data.keys())}"

    def assert_llm_called(self, ctx: MockToolContext, times: int = 1) -> None:
        """Vérifie que le LLM a été appelé N fois."""
        assert len(ctx.llm.calls) == times, (
            f"LLM appelé {len(ctx.llm.calls)} fois, attendu {times}"
        )

    def assert_connector_called(
        self, ctx: MockToolContext, connector_slug: str, action: str, times: int = 1
    ) -> None:
        """Vérifie qu'un connecteur.action a été appelé N fois."""
        calls = [
            c for c in ctx.connectors.calls
            if c["connector"] == connector_slug and c["action"] == action
        ]
        assert len(calls) == times, (
            f"Connector '{connector_slug}.{action}' appelé {len(calls)} fois, attendu {times}"
        )

    def assert_storage_put(self, ctx: MockToolContext, key: str) -> None:
        """Vérifie qu'un fichier a été stocké."""
        puts = [c for c in ctx.storage.calls if c["method"] == "put" and c["key"] == key]
        assert len(puts) > 0, f"Aucun storage.put pour la clé '{key}'"

    def assert_storage_get(self, ctx: MockToolContext, key: str) -> None:
        """Vérifie qu'un fichier a été lu."""
        gets = [c for c in ctx.storage.calls if c["method"] == "get" and c["key"] == key]
        assert len(gets) > 0, f"Aucun storage.get pour la clé '{key}'"

    def assert_progress_reached(self, ctx: MockToolContext, min_percent: int) -> None:
        """Vérifie que la progression a atteint un minimum."""
        if not ctx._progress_history:
            raise AssertionError("Aucun appel à context.progress()")
        max_reached = max(p["percent"] for p in ctx._progress_history)
        assert max_reached >= min_percent, (
            f"Progression max atteinte: {max_reached}%, attendu >= {min_percent}%"
        )

    async def assert_health_ok(self) -> None:
        """Vérifie que le health_check retourne healthy."""
        result = await self.tool.health_check()
        assert result.healthy, f"Health check failed: {result.message}"

    async def assert_validates_params(self, params: dict, expected_errors: int = 0) -> list[str]:
        """
        Vérifie la validation des paramètres.

        Args:
            params: Paramètres à valider
            expected_errors: Nombre d'erreurs attendues (0 = valide)

        Returns:
            Liste des erreurs
        """
        errors = await self.tool.validate_params(params)
        assert len(errors) == expected_errors, (
            f"Attendu {expected_errors} erreurs, obtenu {len(errors)}: {errors}"
        )
        return errors
