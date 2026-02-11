"""
YAML CRUD — Créer, lire, modifier et supprimer des fichiers YAML.

Catégorie: data
Mode: sync

Actions:
    create  → Génère un fichier YAML depuis des données
    read    → Parse un YAML et retourne les données
    update  → Modifie un YAML (merge patch)
    delete  → Supprime un fichier YAML du stockage
"""

from __future__ import annotations

from typing import Any

import yaml

from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolErrorCode,
    ToolExample,
    ToolExecutionMode,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)


class YamlCrud(BaseTool):
    """CRUD complet pour les fichiers YAML via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="yaml-crud",
            name="YAML CRUD",
            description="Créer, lire, modifier et supprimer des fichiers YAML",
            version="1.0.0",
            category="data",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=30,
            input_schema=[
                ToolParameter(name="action", type="string", required=True,
                              description="Action: create, read, update, delete"),
                ToolParameter(name="storage_key", type="string",
                              description="Chemin MinIO du fichier"),
                ToolParameter(name="data", type="object",
                              description="Données YAML à écrire ou fusionner"),
                ToolParameter(name="options", type="object",
                              description="Options: {default_flow_style, allow_unicode}"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string"),
                ToolParameter(name="data", type="object", description="Données YAML lues/modifiées"),
                ToolParameter(name="keys", type="array"),
                ToolParameter(name="size_bytes", type="integer"),
            ],
            examples=[
                ToolExample(
                    description="Créer un YAML",
                    input={
                        "action": "create",
                        "storage_key": "config/app.yaml",
                        "data": {
                            "app": {"name": "MyApp", "version": "1.0.0"},
                            "database": {"host": "localhost", "port": 5432},
                        },
                    },
                    output={"storage_key": "config/app.yaml", "keys": ["app", "database"]},
                ),
                ToolExample(
                    description="Lire un YAML",
                    input={"action": "read", "storage_key": "config/app.yaml"},
                    output={"data": {"app": {"name": "MyApp"}}, "keys": ["app", "database"]},
                ),
            ],
            tags=["data", "yaml", "crud", "config"],
        )

    async def execute(self, params: dict[str, Any], context) -> ToolResult:
        action = params.get("action", "")
        if action == "create":
            return await self._create(params, context)
        elif action == "read":
            return await self._read(params, context)
        elif action == "update":
            return await self._update(params, context)
        elif action == "delete":
            return await self._delete(params, context)
        else:
            return self.error(
                f"Action inconnue: '{action}'. Actions: create, read, update, delete",
                ToolErrorCode.INVALID_PARAMS,
            )

    async def _create(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        data = params.get("data", {})
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour create", ToolErrorCode.INVALID_PARAMS)

        default_flow_style = options.get("default_flow_style", False)
        allow_unicode = options.get("allow_unicode", True)

        content = yaml.dump(
            data,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            sort_keys=False,
        )
        content_bytes = content.encode("utf-8")
        await context.storage.put(storage_key, content_bytes, "application/x-yaml")

        keys = list(data.keys()) if isinstance(data, dict) else []

        return self.success({
            "storage_key": storage_key,
            "keys": keys,
            "size_bytes": len(content_bytes),
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            data = yaml.safe_load(file_data.decode("utf-8"))
        except yaml.YAMLError as e:
            return self.error(f"YAML invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        if data is None:
            data = {}

        keys = list(data.keys()) if isinstance(data, dict) else []

        return self.success({
            "storage_key": storage_key,
            "data": data,
            "keys": keys,
            "size_bytes": len(file_data),
        })

    async def _update(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        patch = params.get("data", {})
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour update", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            data = yaml.safe_load(file_data.decode("utf-8"))
        except yaml.YAMLError as e:
            return self.error(f"YAML invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        if data is None:
            data = {}

        merged = self._deep_merge(data, patch)

        default_flow_style = options.get("default_flow_style", False)
        allow_unicode = options.get("allow_unicode", True)

        content = yaml.dump(
            merged,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            sort_keys=False,
        )
        content_bytes = content.encode("utf-8")
        await context.storage.put(storage_key, content_bytes, "application/x-yaml")

        keys = list(merged.keys()) if isinstance(merged, dict) else []

        return self.success({
            "storage_key": storage_key,
            "data": merged,
            "keys": keys,
            "size_bytes": len(content_bytes),
        })

    async def _delete(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour delete", ToolErrorCode.INVALID_PARAMS)

        deleted = await context.storage.delete(storage_key)
        if not deleted:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        return self.success({"storage_key": storage_key, "deleted": True})

    @staticmethod
    def _deep_merge(target: Any, patch: Any) -> Any:
        """Merge profond (comme JSON Merge Patch)."""
        if not isinstance(patch, dict):
            return patch
        if not isinstance(target, dict):
            target = {}
        result = dict(target)
        for key, value in patch.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict):
                result[key] = YamlCrud._deep_merge(result.get(key, {}), value)
            else:
                result[key] = value
        return result
