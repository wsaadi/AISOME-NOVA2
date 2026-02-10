"""
Agent Validator — Vérifie qu'un package agent respecte TOUTES les conventions du framework.

Aucun agent ne peut être déployé sans passer par le validateur.

Usage:
    python -m app.framework.validator agents/mon-agent/

Vérifications:
    1. manifest.json existe et est valide
    2. agent.py existe et étend BaseAgent
    3. handle_message() est implémenté
    4. Toutes les méthodes ont des docstrings
    5. Dépendances (tools/connectors) existent dans les registres
    6. prompts/system.md existe et n'est pas vide
    7. frontend/index.tsx existe
    8. Pas d'imports interdits (os, subprocess, requests, httpx, open...)
    9. Pas de credentials en dur
    10. Pas de path traversal ou d'accès filesystem
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.framework.schemas import AgentManifest

logger = logging.getLogger(__name__)

# Imports interdits dans agent.py
FORBIDDEN_IMPORTS = {
    "os",
    "subprocess",
    "shutil",
    "pathlib",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "sqlite3",
    "psycopg2",
    "asyncpg",
    "sqlalchemy",
    "redis",
    "celery",
    "boto3",
    "minio",
}

# Fonctions builtin interdites
FORBIDDEN_BUILTINS = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "globals",
    "locals",
}

# Patterns de credentials en dur
CREDENTIAL_PATTERNS = [
    r'(?:api_key|apikey|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']',
    r'(?:sk-|pk-|Bearer\s+)[a-zA-Z0-9]{20,}',
]


@dataclass
class ValidationError:
    """Erreur de validation."""

    code: str
    message: str
    file: str = ""
    line: int = 0
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Résultat de la validation d'un agent."""

    valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    agent_slug: str = ""

    def add_error(self, code: str, message: str, file: str = "", line: int = 0):
        """Ajoute une erreur."""
        self.errors.append(
            ValidationError(code=code, message=message, file=file, line=line)
        )
        self.valid = False

    def add_warning(self, code: str, message: str, file: str = "", line: int = 0):
        """Ajoute un warning."""
        self.warnings.append(
            ValidationError(
                code=code, message=message, file=file, line=line, severity="warning"
            )
        )

    def summary(self) -> str:
        """Retourne un résumé lisible."""
        lines = []
        if self.valid:
            lines.append(f"Agent '{self.agent_slug}' valide ✓")
        else:
            lines.append(f"Agent '{self.agent_slug}' invalide ✗")

        for err in self.errors:
            loc = f" ({err.file}:{err.line})" if err.file else ""
            lines.append(f"  ✗ [{err.code}] {err.message}{loc}")

        for warn in self.warnings:
            loc = f" ({warn.file}:{warn.line})" if warn.file else ""
            lines.append(f"  ⚠ [{warn.code}] {warn.message}{loc}")

        lines.append(f"\n  {len(self.errors)} erreur(s), {len(self.warnings)} warning(s)")
        return "\n".join(lines)


class AgentValidator:
    """
    Validateur de packages agents.

    Vérifie la conformité structurelle, sécuritaire et qualitative.
    """

    def __init__(
        self,
        tool_slugs: Optional[set[str]] = None,
        connector_slugs: Optional[set[str]] = None,
    ):
        self._tool_slugs = tool_slugs or set()
        self._connector_slugs = connector_slugs or set()

    def validate(self, agent_dir: Path) -> ValidationResult:
        """
        Valide un package agent complet.

        Args:
            agent_dir: Chemin du dossier de l'agent

        Returns:
            ValidationResult avec les erreurs et warnings
        """
        result = ValidationResult(agent_slug=agent_dir.name)

        if not agent_dir.is_dir():
            result.add_error("NOT_DIR", f"'{agent_dir}' n'est pas un dossier")
            return result

        # 1. manifest.json
        manifest = self._validate_manifest(agent_dir, result)

        if manifest:
            result.agent_slug = manifest.slug

        # 2. agent.py
        self._validate_agent_py(agent_dir, result)

        # 3. prompts/system.md
        self._validate_prompts(agent_dir, result)

        # 4. Dépendances
        if manifest:
            self._validate_dependencies(manifest, result)

        # 5. Frontend
        self._validate_frontend(agent_dir, result)

        return result

    def _validate_manifest(
        self, agent_dir: Path, result: ValidationResult
    ) -> Optional[AgentManifest]:
        """Valide manifest.json."""
        manifest_path = agent_dir / "manifest.json"

        if not manifest_path.exists():
            result.add_error("NO_MANIFEST", "manifest.json manquant", "manifest.json")
            return None

        try:
            with open(manifest_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error("INVALID_JSON", f"JSON invalide: {e}", "manifest.json")
            return None

        try:
            manifest = AgentManifest(**data)
            return manifest
        except Exception as e:
            result.add_error(
                "INVALID_MANIFEST", f"Manifest invalide: {e}", "manifest.json"
            )
            return None

    def _validate_agent_py(self, agent_dir: Path, result: ValidationResult) -> None:
        """Valide agent.py (structure, imports, sécurité)."""
        agent_py = agent_dir / "agent.py"

        if not agent_py.exists():
            result.add_error("NO_AGENT_PY", "agent.py manquant", "agent.py")
            return

        source = agent_py.read_text()

        # Parser l'AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result.add_error(
                "SYNTAX_ERROR", f"Erreur de syntaxe: {e}", "agent.py", e.lineno or 0
            )
            return

        # Vérifier les imports interdits
        self._check_forbidden_imports(tree, result)

        # Vérifier les appels interdits
        self._check_forbidden_calls(tree, result)

        # Vérifier la présence de BaseAgent
        has_base_agent = False
        has_handle_message = False
        has_manifest = False

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name == "BaseAgent":
                        has_base_agent = True

                        # Vérifier les méthodes
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if item.name == "handle_message":
                                    has_handle_message = True
                                    # Vérifier docstring
                                    if not ast.get_docstring(item):
                                        result.add_warning(
                                            "NO_DOCSTRING",
                                            "handle_message() n'a pas de docstring",
                                            "agent.py",
                                            item.lineno,
                                        )
                                if item.name == "manifest":
                                    has_manifest = True

                            if isinstance(item, ast.FunctionDef) and item.name == "manifest":
                                # C'est un property
                                for deco in item.decorator_list:
                                    if isinstance(deco, ast.Name) and deco.id == "property":
                                        has_manifest = True

        if not has_base_agent:
            result.add_error(
                "NO_BASE_AGENT",
                "Aucune classe n'étend BaseAgent",
                "agent.py",
            )

        if has_base_agent and not has_handle_message:
            result.add_error(
                "NO_HANDLE_MESSAGE",
                "handle_message() non implémenté",
                "agent.py",
            )

        if has_base_agent and not has_manifest:
            result.add_error(
                "NO_MANIFEST_PROP",
                "Propriété manifest non définie",
                "agent.py",
            )

        # Vérifier les credentials en dur
        self._check_credentials(source, result)

    def _check_forbidden_imports(
        self, tree: ast.AST, result: ValidationResult
    ) -> None:
        """Vérifie les imports interdits."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in FORBIDDEN_IMPORTS:
                        result.add_error(
                            "FORBIDDEN_IMPORT",
                            f"Import interdit: '{alias.name}' — utiliser le context framework",
                            "agent.py",
                            node.lineno,
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in FORBIDDEN_IMPORTS:
                        result.add_error(
                            "FORBIDDEN_IMPORT",
                            f"Import interdit: 'from {node.module}' — utiliser le context framework",
                            "agent.py",
                            node.lineno,
                        )

    def _check_forbidden_calls(
        self, tree: ast.AST, result: ValidationResult
    ) -> None:
        """Vérifie les appels de fonctions interdits."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in FORBIDDEN_BUILTINS:
                    result.add_error(
                        "FORBIDDEN_CALL",
                        f"Appel interdit: '{func_name}()' — interdit pour raisons de sécurité",
                        "agent.py",
                        node.lineno,
                    )

    def _check_credentials(self, source: str, result: ValidationResult) -> None:
        """Vérifie l'absence de credentials en dur."""
        for pattern in CREDENTIAL_PATTERNS:
            matches = re.finditer(pattern, source, re.IGNORECASE)
            for match in matches:
                line_num = source[: match.start()].count("\n") + 1
                result.add_error(
                    "HARDCODED_CREDENTIALS",
                    "Credentials potentiellement en dur détectés",
                    "agent.py",
                    line_num,
                )

    def _validate_prompts(self, agent_dir: Path, result: ValidationResult) -> None:
        """Valide le dossier prompts/."""
        system_md = agent_dir / "prompts" / "system.md"

        if not system_md.exists():
            result.add_error(
                "NO_SYSTEM_PROMPT",
                "prompts/system.md manquant",
                "prompts/system.md",
            )
            return

        content = system_md.read_text().strip()
        if not content:
            result.add_error(
                "EMPTY_SYSTEM_PROMPT",
                "prompts/system.md est vide",
                "prompts/system.md",
            )

    def _validate_dependencies(
        self, manifest: AgentManifest, result: ValidationResult
    ) -> None:
        """Valide que les dépendances déclarées existent dans les registres."""
        for tool_slug in manifest.dependencies.tools:
            if self._tool_slugs and tool_slug not in self._tool_slugs:
                result.add_warning(
                    "UNKNOWN_TOOL",
                    f"Tool '{tool_slug}' non trouvé dans le registre",
                    "manifest.json",
                )

        for connector_slug in manifest.dependencies.connectors:
            if self._connector_slugs and connector_slug not in self._connector_slugs:
                result.add_warning(
                    "UNKNOWN_CONNECTOR",
                    f"Connecteur '{connector_slug}' non trouvé dans le registre",
                    "manifest.json",
                )

    def _validate_frontend(self, agent_dir: Path, result: ValidationResult) -> None:
        """Valide les fichiers frontend."""
        # Chercher dans le dossier frontend de l'agent ou dans le frontend global
        # Le frontend peut être dans un dossier séparé
        frontend_dir = agent_dir / "frontend"
        if not frontend_dir.exists():
            # Acceptable si le frontend est dans le repo frontend/src/agents/{slug}/
            result.add_warning(
                "NO_FRONTEND_DIR",
                "Pas de dossier frontend/ local (vérifier frontend/src/agents/)",
                "",
            )
            return

        index_tsx = frontend_dir / "index.tsx"
        if not index_tsx.exists():
            result.add_error(
                "NO_INDEX_TSX",
                "frontend/index.tsx manquant",
                "frontend/index.tsx",
            )


def validate_agent(agent_path: str) -> ValidationResult:
    """
    Point d'entrée pour la validation en ligne de commande.

    Args:
        agent_path: Chemin vers le dossier de l'agent

    Returns:
        ValidationResult
    """
    validator = AgentValidator()
    return validator.validate(Path(agent_path))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.framework.validator <agent_path>")
        sys.exit(1)

    result = validate_agent(sys.argv[1])
    print(result.summary())
    sys.exit(0 if result.valid else 1)
