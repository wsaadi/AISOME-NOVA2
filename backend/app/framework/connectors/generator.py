"""
Connector Generator — Génère un squelette de connecteur et ses tests.

Usage:
    python -m app.framework.connectors.generator <slug> <name> [description] [category] [auth_type]

Exemples:
    python -m app.framework.connectors.generator slack "Slack" "Messaging Slack" messaging api_key
    python -m app.framework.connectors.generator salesforce "Salesforce CRM" "CRM" saas oauth2
    python -m app.framework.connectors.generator smtp-email "SMTP Email" "Envoi d'emails" messaging basic
"""

from __future__ import annotations

import sys
from pathlib import Path

CONNECTORS_DIR = Path(__file__).parent
TESTS_DIR = CONNECTORS_DIR.parent.parent.parent / "tests" / "connectors"

CONNECTOR_TEMPLATE = '''"""
{name} — {description}

Catégorie: {category}
Auth: {auth_type}

Actions:
    example_action  → Description de l'action
"""

from __future__ import annotations

from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)


class {class_name}(BaseConnector):
    """{description}"""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="{slug}",
            name="{name}",
            description="{description}",
            version="1.0.0",
            category="{category}",
            auth_type="{auth_type}",
            config_schema=[
{config_schema_lines}
            ],
            actions=[
                ConnectorAction(
                    name="example_action",
                    description="Action exemple — à remplacer",
                    input_schema=[
                        ToolParameter(name="query", type="string", required=True,
                                      description="Paramètre exemple"),
                    ],
                    output_schema=[
                        ToolParameter(name="result", type="string"),
                    ],
                ),
            ],
            tags={tags},
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise la connexion au service externe."""
        import httpx

        self._config = config
{connect_body}

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        """Exécute une action."""
        if action == "example_action":
            return await self._example_action(params)
        return self.error(f"Action inconnue: {{action}}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme proprement la connexion."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Vérifie que le service est accessible."""
        # TODO: Implémenter le health check
        return True

    async def _example_action(self, params: dict[str, Any]) -> ConnectorResult:
        """Action exemple — à remplacer par la vraie logique."""
        try:
            # TODO: Implémenter l'action
            return self.success({{"result": "OK"}})
        except Exception as e:
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)
'''

TEST_TEMPLATE = '''"""Tests pour le connecteur {name}."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.framework.connectors.{module_name} import {class_name}


class Test{class_name}:
    """{name} connector tests."""

    @pytest.fixture
    def connector(self):
        """Crée une instance du connecteur."""
        return {class_name}()

    def test_metadata(self, connector):
        """Vérifie les métadonnées."""
        meta = connector.metadata
        assert meta.slug == "{slug}"
        assert meta.name == "{name}"
        assert meta.auth_type == "{auth_type}"
        assert meta.category == "{category}"
        assert len(meta.actions) >= 1
        assert "example_action" in connector.get_available_actions()

    def test_validate_action(self, connector):
        """Vérifie la validation des actions."""
        assert connector.validate_action("example_action")
        assert not connector.validate_action("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_invalid_action(self, connector):
        """Test action invalide."""
        result = await connector.execute("nonexistent_action", {{}})
        assert not result.success
        assert "inconnue" in result.error

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test déconnexion sans client initialisé."""
        await connector.disconnect()  # Ne doit pas lever d'exception

    @pytest.mark.asyncio
    async def test_health_check(self, connector):
        """Test health check par défaut."""
        assert await connector.health_check()

    # TODO: Ajouter des tests pour chaque action avec mock HTTP
'''


# Config schema templates par auth_type
AUTH_CONFIG_SCHEMAS = {
    "api_key": [
        '                ToolParameter(name="api_key", type="string", required=True,',
        '                              description="Clé d\'API du service"),',
        '                ToolParameter(name="base_url", type="string",',
        '                              description="URL de base"),',
    ],
    "oauth2": [
        '                ToolParameter(name="client_id", type="string", required=True),',
        '                ToolParameter(name="client_secret", type="string", required=True),',
        '                ToolParameter(name="refresh_token", type="string", required=True),',
        '                ToolParameter(name="token_url", type="string", required=True,',
        '                              description="URL de rafraîchissement du token"),',
    ],
    "basic": [
        '                ToolParameter(name="username", type="string", required=True),',
        '                ToolParameter(name="password", type="string", required=True),',
        '                ToolParameter(name="base_url", type="string", required=True,',
        '                              description="URL de base du service"),',
    ],
    "none": [],
    "custom": [
        '                # TODO: Définir les paramètres de config custom',
    ],
}

CONNECT_BODIES = {
    "api_key": """        self._client = httpx.AsyncClient(
            base_url=config.get("base_url", "https://api.example.com"),
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=30.0,
        )""",
    "oauth2": """        self._client = httpx.AsyncClient(timeout=30.0)
        await self._refresh_access_token()

    async def _refresh_access_token(self):
        \"\"\"Rafraîchit le access token via OAuth2.\"\"\"
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(self._config["token_url"], data={
                "grant_type": "refresh_token",
                "client_id": self._config["client_id"],
                "client_secret": self._config["client_secret"],
                "refresh_token": self._config["refresh_token"],
            })
            data = resp.json()
            self._access_token = data["access_token"]
            self._client.headers["Authorization"] = f"Bearer {self._access_token}" """,
    "basic": """        self._client = httpx.AsyncClient(
            base_url=config["base_url"],
            auth=(config["username"], config["password"]),
            timeout=30.0,
        )""",
    "none": """        self._client = httpx.AsyncClient(timeout=30.0)""",
    "custom": """        # TODO: Implémenter la connexion custom
        self._client = httpx.AsyncClient(timeout=30.0)""",
}


def slug_to_class_name(slug: str) -> str:
    """Convertit un slug en nom de classe (kebab-case → PascalCase + Connector)."""
    parts = slug.split("-")
    class_name = "".join(p.capitalize() for p in parts)
    return f"{class_name}Connector"


def slug_to_module_name(slug: str) -> str:
    """Convertit un slug en nom de module (kebab-case → snake_case)."""
    return slug.replace("-", "_")


def generate_connector(
    slug: str,
    name: str,
    description: str = "",
    category: str = "general",
    auth_type: str = "api_key",
) -> tuple[Path, Path]:
    """
    Génère un squelette de connecteur et ses tests.

    Args:
        slug: Identifiant unique (kebab-case)
        name: Nom d'affichage
        description: Description courte
        category: Catégorie du connecteur
        auth_type: Type d'authentification

    Returns:
        Tuple (chemin connecteur, chemin tests)
    """
    if not description:
        description = f"Connecteur {name}"

    class_name = slug_to_class_name(slug)
    module_name = slug_to_module_name(slug)

    config_schema_lines = "\n".join(AUTH_CONFIG_SCHEMAS.get(auth_type, AUTH_CONFIG_SCHEMAS["api_key"]))
    connect_body = CONNECT_BODIES.get(auth_type, CONNECT_BODIES["api_key"])
    tags = repr([category, slug.split("-")[0]])

    connector_content = CONNECTOR_TEMPLATE.format(
        slug=slug,
        name=name,
        description=description,
        category=category,
        auth_type=auth_type,
        class_name=class_name,
        config_schema_lines=config_schema_lines,
        connect_body=connect_body,
        tags=tags,
    )

    test_content = TEST_TEMPLATE.format(
        slug=slug,
        name=name,
        auth_type=auth_type,
        category=category,
        class_name=class_name,
        module_name=module_name,
    )

    # Écrire les fichiers
    connector_path = CONNECTORS_DIR / f"{module_name}.py"
    connector_path.write_text(connector_content)

    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    init_file = TESTS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    test_path = TESTS_DIR / f"test_{module_name}.py"
    test_path.write_text(test_content)

    return connector_path, test_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m app.framework.connectors.generator <slug> <name> [description] [category] [auth_type]")
        print()
        print("Arguments:")
        print("  slug         Identifiant unique (kebab-case, ex: slack, google-drive)")
        print("  name         Nom d'affichage (ex: 'Slack', 'Google Drive')")
        print("  description  Description courte (défaut: 'Connecteur {name}')")
        print("  category     saas|messaging|storage|database|ai|devops|analytics|finance|general")
        print("  auth_type    none|api_key|oauth2|basic|custom (défaut: api_key)")
        print()
        print("Exemples:")
        print('  python -m app.framework.connectors.generator slack "Slack" "Messaging" messaging api_key')
        print('  python -m app.framework.connectors.generator google-drive "Google Drive" "Cloud" storage oauth2')
        sys.exit(1)

    slug = sys.argv[1]
    name = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else ""
    category = sys.argv[4] if len(sys.argv) > 4 else "general"
    auth_type = sys.argv[5] if len(sys.argv) > 5 else "api_key"

    connector_path, test_path = generate_connector(slug, name, description, category, auth_type)

    print(f"Connecteur généré:")
    print(f"  {connector_path}")
    print(f"  {test_path}")
    print()
    print("Prochaines étapes:")
    print(f"  1. Éditer {connector_path} — implémenter les actions")
    print(f"  2. Éditer {test_path} — compléter les tests")
    print(f"  3. Le connecteur sera auto-découvert au prochain démarrage")
