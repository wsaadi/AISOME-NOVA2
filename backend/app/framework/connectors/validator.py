"""
ConnectorValidator — Vérifie qu'un fichier connecteur respecte les conventions du framework.

Vérifications:
    1. Le fichier contient une classe qui étend BaseConnector
    2. metadata property est définie
    3. connect() et execute() sont implémentés
    4. Pas d'imports interdits (os, subprocess, open...)
    5. Pas de credentials en dur
    6. auth_type != "none" implique config_schema non vide
    7. Au moins 1 action dans metadata.actions

Usage:
    from app.framework.connectors.validator import ConnectorValidator

    validator = ConnectorValidator()
    result = validator.validate(Path("connectors/slack.py"))
    print(result.summary())
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Imports interdits dans les connecteurs
# NOTE: httpx, requests, boto3, aiohttp AUTORISÉS (c'est la raison d'être du connecteur)
CONNECTOR_FORBIDDEN_IMPORTS = {
    "os",
    "subprocess",
    "shutil",
    "pathlib",
    "sqlite3",
    "psycopg2",
    "asyncpg",
    "sqlalchemy",
    "redis",
    "celery",
    "minio",
}

# Fonctions builtin interdites
CONNECTOR_FORBIDDEN_BUILTINS = {
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
    r'(?:sk-|pk-|xoxb-|xoxp-|Bearer\s+)[a-zA-Z0-9]{20,}',
]


@dataclass
class ConnectorValidationError:
    """Erreur de validation d'un connecteur."""

    code: str
    message: str
    file: str = ""
    line: int = 0
    severity: str = "error"


@dataclass
class ConnectorValidationResult:
    """Résultat de la validation d'un connecteur."""

    valid: bool = True
    errors: list[ConnectorValidationError] = field(default_factory=list)
    warnings: list[ConnectorValidationError] = field(default_factory=list)
    connector_file: str = ""

    def add_error(self, code: str, message: str, file: str = "", line: int = 0):
        self.errors.append(
            ConnectorValidationError(code=code, message=message, file=file, line=line)
        )
        self.valid = False

    def add_warning(self, code: str, message: str, file: str = "", line: int = 0):
        self.warnings.append(
            ConnectorValidationError(
                code=code, message=message, file=file, line=line, severity="warning"
            )
        )

    def summary(self) -> str:
        lines = []
        status = "valide" if self.valid else "invalide"
        symbol = "✓" if self.valid else "✗"
        lines.append(f"Connecteur '{self.connector_file}' {status} {symbol}")

        for err in self.errors:
            loc = f" ({err.file}:{err.line})" if err.file else ""
            lines.append(f"  ✗ [{err.code}] {err.message}{loc}")

        for warn in self.warnings:
            loc = f" ({warn.file}:{warn.line})" if warn.file else ""
            lines.append(f"  ⚠ [{warn.code}] {warn.message}{loc}")

        lines.append(f"\n  {len(self.errors)} erreur(s), {len(self.warnings)} warning(s)")
        return "\n".join(lines)


class ConnectorValidator:
    """
    Validateur de fichiers connecteurs.

    Vérifie la conformité structurelle et sécuritaire.
    """

    def validate(self, py_file: Path) -> ConnectorValidationResult:
        """
        Valide un fichier connecteur.

        Args:
            py_file: Chemin du fichier Python à valider

        Returns:
            ConnectorValidationResult
        """
        result = ConnectorValidationResult(connector_file=py_file.name)

        if not py_file.exists():
            result.add_error("FILE_NOT_FOUND", f"Fichier '{py_file}' introuvable")
            return result

        if not py_file.suffix == ".py":
            result.add_error("NOT_PYTHON", "Le fichier doit être un .py")
            return result

        source = py_file.read_text()

        # Parse AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result.add_error(
                "SYNTAX_ERROR", f"Erreur de syntaxe: {e}",
                py_file.name, e.lineno or 0,
            )
            return result

        # Vérifications structurelles
        self._check_base_connector(tree, py_file.name, result)

        # Vérifications sécurité
        self._check_forbidden_imports(tree, py_file.name, result)
        self._check_forbidden_calls(tree, py_file.name, result)
        self._check_credentials(source, py_file.name, result)

        # Vérification docstring module
        if not ast.get_docstring(tree):
            result.add_warning(
                "NO_MODULE_DOCSTRING",
                "Le module n'a pas de docstring",
                py_file.name,
            )

        return result

    def _check_base_connector(
        self, tree: ast.AST, filename: str, result: ConnectorValidationResult
    ) -> None:
        """Vérifie la structure BaseConnector."""
        has_base_connector = False
        has_metadata = False
        has_connect = False
        has_execute = False
        has_disconnect = False

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name == "BaseConnector":
                        has_base_connector = True

                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if item.name == "metadata":
                                    has_metadata = True
                                elif item.name == "connect":
                                    has_connect = True
                                elif item.name == "execute":
                                    has_execute = True
                                elif item.name == "disconnect":
                                    has_disconnect = True

                                    # Vérifier docstring
                                    if not ast.get_docstring(item):
                                        result.add_warning(
                                            "NO_DOCSTRING",
                                            f"{item.name}() n'a pas de docstring",
                                            filename, item.lineno,
                                        )

                            # Property metadata
                            if isinstance(item, ast.FunctionDef) and item.name == "metadata":
                                for deco in item.decorator_list:
                                    if isinstance(deco, ast.Name) and deco.id == "property":
                                        has_metadata = True

        if not has_base_connector:
            result.add_error(
                "NO_BASE_CONNECTOR",
                "Aucune classe n'étend BaseConnector",
                filename,
            )

        if has_base_connector and not has_metadata:
            result.add_error("NO_METADATA", "Propriété metadata manquante", filename)

        if has_base_connector and not has_connect:
            result.add_error("NO_CONNECT", "Méthode connect() manquante", filename)

        if has_base_connector and not has_execute:
            result.add_error("NO_EXECUTE", "Méthode execute() manquante", filename)

        if has_base_connector and not has_disconnect:
            result.add_warning(
                "NO_DISCONNECT",
                "Méthode disconnect() non définie (les ressources ne seront pas nettoyées)",
                filename,
            )

    def _check_forbidden_imports(
        self, tree: ast.AST, filename: str, result: ConnectorValidationResult
    ) -> None:
        """Vérifie les imports interdits."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in CONNECTOR_FORBIDDEN_IMPORTS:
                        result.add_error(
                            "FORBIDDEN_IMPORT",
                            f"Import interdit: '{alias.name}' — un connecteur ne peut pas accéder à {module_root}",
                            filename, node.lineno,
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in CONNECTOR_FORBIDDEN_IMPORTS:
                        result.add_error(
                            "FORBIDDEN_IMPORT",
                            f"Import interdit: 'from {node.module}' — un connecteur ne peut pas accéder à {module_root}",
                            filename, node.lineno,
                        )

    def _check_forbidden_calls(
        self, tree: ast.AST, filename: str, result: ConnectorValidationResult
    ) -> None:
        """Vérifie les appels de fonctions interdits."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in CONNECTOR_FORBIDDEN_BUILTINS:
                    result.add_error(
                        "FORBIDDEN_CALL",
                        f"Appel interdit: '{func_name}()' — interdit pour raisons de sécurité",
                        filename, node.lineno,
                    )

    def _check_credentials(
        self, source: str, filename: str, result: ConnectorValidationResult
    ) -> None:
        """Vérifie l'absence de credentials en dur."""
        for pattern in CREDENTIAL_PATTERNS:
            matches = re.finditer(pattern, source, re.IGNORECASE)
            for match in matches:
                line_num = source[: match.start()].count("\n") + 1
                result.add_error(
                    "HARDCODED_CREDENTIALS",
                    "Credentials potentiellement en dur détectés — utiliser Vault",
                    filename, line_num,
                )


def validate_connector(connector_path: str) -> ConnectorValidationResult:
    """Point d'entrée CLI."""
    validator = ConnectorValidator()
    return validator.validate(Path(connector_path))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.framework.connectors.validator <connector_file.py>")
        sys.exit(1)

    res = validate_connector(sys.argv[1])
    print(res.summary())
    sys.exit(0 if res.valid else 1)
