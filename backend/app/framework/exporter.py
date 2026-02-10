"""
Agent Exporter/Importer — Export ZIP et import de packages agents.

Format du ZIP:
    mon-agent.zip
    ├── manifest.json
    ├── backend/
    │   ├── agent.py
    │   └── prompts/
    │       └── system.md
    └── frontend/
        ├── index.tsx
        ├── components/
        │   └── *.tsx
        └── styles.ts
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.framework.schemas import AgentManifest, AgentPackageInfo
from app.framework.validator import AgentValidator, ValidationResult

logger = logging.getLogger(__name__)

BACKEND_AGENTS_ROOT = Path(__file__).parent.parent / "agents"
FRONTEND_AGENTS_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "src" / "agents"


class AgentExporter:
    """Exporte un agent sous forme de ZIP."""

    def export(self, agent_slug: str) -> bytes:
        """
        Exporte un agent en ZIP.

        Args:
            agent_slug: Slug de l'agent à exporter

        Returns:
            Contenu du ZIP en bytes

        Raises:
            FileNotFoundError: Si l'agent n'existe pas
            ValueError: Si l'agent est invalide
        """
        backend_dir = BACKEND_AGENTS_ROOT / agent_slug
        frontend_dir = FRONTEND_AGENTS_ROOT / agent_slug

        if not backend_dir.exists():
            raise FileNotFoundError(f"Agent backend not found: {backend_dir}")

        # Valider avant d'exporter
        validator = AgentValidator()
        result = validator.validate(backend_dir)
        if not result.valid:
            raise ValueError(f"Agent invalide, export refusé:\n{result.summary()}")

        # Créer le ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Backend files
            self._add_directory(zf, backend_dir, "backend")

            # Frontend files
            if frontend_dir.exists():
                self._add_directory(zf, frontend_dir, "frontend")

            # Copier manifest.json à la racine du ZIP aussi
            manifest_path = backend_dir / "manifest.json"
            if manifest_path.exists():
                zf.write(manifest_path, "manifest.json")

            # Ajouter les métadonnées d'export
            export_info = AgentPackageInfo(
                manifest=AgentManifest(**json.loads(manifest_path.read_text())),
                exported_at=datetime.utcnow(),
            )
            zf.writestr(
                "_export_info.json",
                export_info.model_dump_json(indent=2),
            )

        buffer.seek(0)
        logger.info(f"Agent exported: {agent_slug} ({buffer.getbuffer().nbytes} bytes)")
        return buffer.getvalue()

    def _add_directory(
        self, zf: zipfile.ZipFile, source_dir: Path, zip_prefix: str
    ) -> None:
        """Ajoute récursivement un dossier au ZIP."""
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                # Ignorer __pycache__, .pyc, node_modules
                if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                    continue
                if "node_modules" in str(file_path):
                    continue

                arcname = f"{zip_prefix}/{file_path.relative_to(source_dir)}"
                zf.write(file_path, arcname)


class AgentImporter:
    """Importe un agent depuis un ZIP."""

    def __init__(
        self,
        tool_slugs: Optional[set[str]] = None,
        connector_slugs: Optional[set[str]] = None,
    ):
        self._tool_slugs = tool_slugs or set()
        self._connector_slugs = connector_slugs or set()

    def import_agent(
        self, zip_data: bytes, overwrite: bool = False
    ) -> tuple[str, ValidationResult]:
        """
        Importe un agent depuis un ZIP.

        1. Extrait le ZIP en mémoire
        2. Lit le manifest pour déterminer le slug
        3. Valide le contenu
        4. Déploie les fichiers sur le filesystem

        Args:
            zip_data: Contenu du ZIP en bytes
            overwrite: Écraser si l'agent existe déjà

        Returns:
            Tuple (slug, ValidationResult)

        Raises:
            ValueError: Si le ZIP est invalide ou si l'agent existe et overwrite=False
        """
        buffer = io.BytesIO(zip_data)

        with zipfile.ZipFile(buffer, "r") as zf:
            # Lire le manifest
            manifest_data = self._read_manifest(zf)
            if not manifest_data:
                raise ValueError("manifest.json manquant dans le ZIP")

            try:
                manifest = AgentManifest(**manifest_data)
            except Exception as e:
                raise ValueError(f"manifest.json invalide: {e}")

            slug = manifest.slug
            backend_dir = BACKEND_AGENTS_ROOT / slug
            frontend_dir = FRONTEND_AGENTS_ROOT / slug

            # Vérifier si l'agent existe
            if backend_dir.exists() and not overwrite:
                raise ValueError(
                    f"L'agent '{slug}' existe déjà. Utilisez overwrite=True pour écraser."
                )

            # Extraire les fichiers
            self._extract_files(zf, backend_dir, frontend_dir)

        # Valider l'agent importé
        validator = AgentValidator(
            tool_slugs=self._tool_slugs,
            connector_slugs=self._connector_slugs,
        )
        result = validator.validate(backend_dir)

        if result.valid:
            logger.info(f"Agent imported successfully: {slug}")
        else:
            logger.warning(f"Agent imported with issues: {slug}\n{result.summary()}")

        return slug, result

    def _read_manifest(self, zf: zipfile.ZipFile) -> Optional[dict]:
        """Lit le manifest.json depuis le ZIP."""
        # Essayer à la racine
        if "manifest.json" in zf.namelist():
            return json.loads(zf.read("manifest.json"))

        # Essayer dans backend/
        if "backend/manifest.json" in zf.namelist():
            return json.loads(zf.read("backend/manifest.json"))

        return None

    def _extract_files(
        self,
        zf: zipfile.ZipFile,
        backend_dir: Path,
        frontend_dir: Path,
    ) -> None:
        """Extrait les fichiers du ZIP vers les bons dossiers."""
        for name in zf.namelist():
            # Sécurité: bloquer path traversal
            if ".." in name or name.startswith("/"):
                logger.warning(f"Skipping suspicious path: {name}")
                continue

            # Ignorer les métadonnées d'export
            if name == "_export_info.json":
                continue

            if name.startswith("backend/"):
                rel_path = name[len("backend/"):]
                if rel_path:
                    target = backend_dir / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not name.endswith("/"):
                        target.write_bytes(zf.read(name))

            elif name.startswith("frontend/"):
                rel_path = name[len("frontend/"):]
                if rel_path:
                    target = frontend_dir / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not name.endswith("/"):
                        target.write_bytes(zf.read(name))

            elif name == "manifest.json":
                # Copier le manifest dans le backend
                target = backend_dir / "manifest.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
