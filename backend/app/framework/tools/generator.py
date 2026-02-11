"""
Tool Generator — Génère le boilerplate complet d'un nouveau tool.

Usage CLI:
    python -m app.framework.tools.generator <slug> <name> [description] [category] [mode]

Exemples:
    python -m app.framework.tools.generator text-summarizer "Text Summarizer"
    python -m app.framework.tools.generator pdf-to-text "PDF to Text" "Extracts text from PDF" file
    python -m app.framework.tools.generator video-transcriber "Video Transcriber" "Transcribes video" media async

Fichiers générés:
    backend/app/framework/tools/<slug>.py     — Code du tool
    backend/tests/tools/test_<slug>.py        — Tests unitaires
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
TESTS_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "tools"


def generate_tool_file(slug: str, name: str, description: str, category: str, mode: str) -> str:
    """Génère le contenu du fichier tool."""
    slug_underscore = slug.replace("-", "_")
    class_name = "".join(word.capitalize() for word in slug.split("-"))

    return f'''"""
{name} — {description}

Catégorie: {category}
Mode: {mode}
"""

from __future__ import annotations

from typing import Any

from app.framework.base import BaseTool
from app.framework.schemas import (
    HealthCheckResult,
    ToolErrorCode,
    ToolExample,
    ToolExecutionMode,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

if __name__ == "__main__":
    raise RuntimeError("Ce fichier ne doit pas être exécuté directement")


class {class_name}(BaseTool):
    """
    {description}

    Inputs:
        - input_text (string, required): Texte d'entrée

    Outputs:
        - result (string): Résultat du traitement
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="{slug}",
            name="{name}",
            description="{description}",
            version="1.0.0",
            category="{category}",
            execution_mode=ToolExecutionMode.{"ASYNC" if mode == "async" else "SYNC"},
            timeout_seconds={300 if mode == "async" else 30},
            input_schema=[
                ToolParameter(
                    name="input_text",
                    type="string",
                    description="Texte d'entrée",
                    required=True,
                ),
            ],
            output_schema=[
                ToolParameter(
                    name="result",
                    type="string",
                    description="Résultat du traitement",
                ),
            ],
            examples=[
                ToolExample(
                    description="Exemple basique",
                    input={{"input_text": "Exemple de texte"}},
                    output={{"result": "Résultat de l'exemple"}},
                ),
            ],
            required_connectors=[],
            tags=["{category}"],
        )

    async def execute(self, params: dict[str, Any], context) -> ToolResult:
        """
        Exécute le tool.

        Args:
            params: {{"input_text": "..."}}
            context: ToolContext avec accès à llm, storage, connectors
        """
        input_text = params["input_text"]

        # TODO: Implémenter la logique métier ici
        # Exemples d'accès aux services:
        #   result = await context.llm.chat("prompt")          # Appel LLM
        #   data = await context.storage.get("file.txt")       # Lire fichier MinIO
        #   await context.storage.put("out.txt", data, "text/plain")  # Écrire fichier
        #   conn = await context.connectors.execute("slug", "action", {{}})  # Connecteur
        #   context.progress(50, "Traitement en cours...")     # Progression (async)

        return self.success({{"result": f"Processed: {{input_text}}"}})

    async def health_check(self) -> HealthCheckResult:
        """Vérifie que le tool est opérationnel."""
        # TODO: Vérifier les dépendances (connecteurs requis, etc.)
        return HealthCheckResult(healthy=True, message="OK")
'''


def generate_test_file(slug: str, name: str, category: str) -> str:
    """Génère le contenu du fichier de tests."""
    slug_underscore = slug.replace("-", "_")
    class_name = "".join(word.capitalize() for word in slug.split("-"))

    return f'''"""
Tests — {name}
"""

import pytest

from app.framework.schemas import ConnectorResult, ToolResult
from app.framework.testing import MockToolContext, ToolTestCase
from app.framework.tools.{slug_underscore} import {class_name}


class Test{class_name}(ToolTestCase):
    tool_class = {class_name}

    def test_metadata(self):
        """Vérifie les métadonnées du tool."""
        meta = self.tool.metadata
        assert meta.slug == "{slug}"
        assert meta.category == "{category}"
        assert len(meta.input_schema) > 0
        assert len(meta.output_schema) > 0
        assert len(meta.examples) > 0

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test d'exécution basique avec des paramètres valides."""
        ctx = self.create_context()
        result = await self.tool.execute(
            {{"input_text": "Test input"}}, ctx
        )
        self.assert_success(result)
        self.assert_data_has(result, "result")

    @pytest.mark.asyncio
    async def test_missing_required_param(self):
        """Test qu'un paramètre requis manquant retourne une erreur."""
        await self.assert_validates_params({{}}, expected_errors=1)

    @pytest.mark.asyncio
    async def test_wrong_type(self):
        """Test qu'un type incorrect retourne une erreur."""
        await self.assert_validates_params(
            {{"input_text": 123}}, expected_errors=1
        )

    @pytest.mark.asyncio
    async def test_valid_params(self):
        """Test que des paramètres valides passent la validation."""
        await self.assert_validates_params(
            {{"input_text": "valide"}}, expected_errors=0
        )

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test que le health check passe."""
        await self.assert_health_ok()
'''


def main():
    """Point d'entrée CLI."""
    if len(sys.argv) < 3:
        print("Usage: python -m app.framework.tools.generator <slug> <name> [description] [category] [mode]")
        print()
        print("Arguments:")
        print("  slug         Identifiant unique (kebab-case, ex: text-summarizer)")
        print("  name         Nom d'affichage (ex: \"Text Summarizer\")")
        print("  description  Description courte (optionnel)")
        print("  category     Catégorie: text, file, data, ai, media, general (défaut: general)")
        print("  mode         Mode: sync, async (défaut: sync)")
        print()
        print("Exemples:")
        print('  python -m app.framework.tools.generator text-summarizer "Text Summarizer"')
        print('  python -m app.framework.tools.generator pdf-to-text "PDF to Text" "Extract text" file')
        print('  python -m app.framework.tools.generator video-transcriber "Video Transcriber" "" media async')
        sys.exit(1)

    slug = sys.argv[1]
    name = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else f"Tool {name}"
    category = sys.argv[4] if len(sys.argv) > 4 else "general"
    mode = sys.argv[5] if len(sys.argv) > 5 else "sync"

    # Validation
    if not all(c.isalnum() or c == "-" for c in slug):
        print(f"Erreur: slug '{slug}' invalide (kebab-case uniquement)")
        sys.exit(1)

    if mode not in ("sync", "async"):
        print(f"Erreur: mode '{mode}' invalide (sync ou async)")
        sys.exit(1)

    slug_underscore = slug.replace("-", "_")

    # Générer le fichier tool
    tool_path = TOOLS_DIR / f"{slug_underscore}.py"
    if tool_path.exists():
        print(f"Erreur: {tool_path} existe déjà")
        sys.exit(1)

    tool_content = generate_tool_file(slug, name, description, category, mode)
    tool_path.write_text(tool_content)
    print(f"Tool créé: {tool_path}")

    # Générer le fichier de tests
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    init_file = TESTS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    test_path = TESTS_DIR / f"test_{slug_underscore}.py"
    test_content = generate_test_file(slug, name, category)
    test_path.write_text(test_content)
    print(f"Tests créés: {test_path}")

    print()
    print(f"Tool '{slug}' généré avec succès!")
    print()
    print("Prochaines étapes:")
    print(f"  1. Éditer {tool_path} → implémenter execute()")
    print(f"  2. Éditer {test_path} → ajouter des tests spécifiques")
    print("  3. Redémarrer le backend → auto-discovery")
    print(f"  4. GET /api/tools/{slug} → vérifier le catalogue")


if __name__ == "__main__":
    main()
