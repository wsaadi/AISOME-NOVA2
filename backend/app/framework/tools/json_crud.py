"""
JSON CRUD — Créer, lire, modifier et supprimer des fichiers JSON.

Catégorie: data
Mode: sync

Actions:
    create  → Génère un fichier JSON depuis des données
    read    → Parse un JSON et retourne les données
    update  → Modifie un JSON (merge patch RFC 7396)
    delete  → Supprime un fichier JSON du stockage
"""

from __future__ import annotations

import json
from typing import Any

from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolErrorCode,
    ToolExample,
    ToolExecutionMode,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)


class JsonCrud(BaseTool):
    """CRUD complet pour les fichiers JSON via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="json-crud",
            name="JSON CRUD",
            description="Créer, lire, modifier et supprimer des fichiers JSON",
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
                              description="Données JSON à écrire ou fusionner"),
                ToolParameter(name="options", type="object",
                              description="Options: {indent, sort_keys, json_path}"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string"),
                ToolParameter(name="data", type="object", description="Données JSON lues/modifiées"),
                ToolParameter(name="keys", type="array", description="Clés de premier niveau"),
                ToolParameter(name="size_bytes", type="integer"),
            ],
            examples=[
                ToolExample(
                    description="Créer un JSON",
                    input={
                        "action": "create",
                        "storage_key": "config/app.json",
                        "data": {"name": "MyApp", "version": "1.0.0", "features": ["auth", "api"]},
                    },
                    output={"storage_key": "config/app.json", "keys": ["name", "version", "features"]},
                ),
                ToolExample(
                    description="Lire un JSON",
                    input={"action": "read", "storage_key": "config/app.json"},
                    output={"data": {"name": "MyApp"}, "keys": ["name", "version", "features"]},
                ),
                ToolExample(
                    description="Update par merge patch",
                    input={
                        "action": "update",
                        "storage_key": "config/app.json",
                        "data": {"version": "2.0.0", "debug": True},
                    },
                    output={"storage_key": "config/app.json"},
                ),
            ],
            tags=["data", "json", "crud", "config"],
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

        indent = options.get("indent", 2)
        sort_keys = options.get("sort_keys", False)

        content = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        content_bytes = content.encode("utf-8")
        await context.storage.put(storage_key, content_bytes, "application/json")

        keys = list(data.keys()) if isinstance(data, dict) else []

        return self.success({
            "storage_key": storage_key,
            "keys": keys,
            "size_bytes": len(content_bytes),
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            data = json.loads(file_data.decode("utf-8"))
        except json.JSONDecodeError as e:
            return self.error(f"JSON invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        # Extraction par json_path optionnelle
        json_path = options.get("json_path")
        extracted = data
        if json_path and isinstance(data, dict):
            for key in json_path.split("."):
                if isinstance(extracted, dict) and key in extracted:
                    extracted = extracted[key]
                else:
                    return self.error(
                        f"Chemin '{json_path}' introuvable dans le JSON",
                        ToolErrorCode.INVALID_PARAMS,
                    )

        keys = list(data.keys()) if isinstance(data, dict) else []

        return self.success({
            "storage_key": storage_key,
            "data": extracted,
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
            data = json.loads(file_data.decode("utf-8"))
        except json.JSONDecodeError as e:
            return self.error(f"JSON invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        # JSON Merge Patch (RFC 7396)
        merged = self._merge_patch(data, patch)

        indent = options.get("indent", 2)
        sort_keys = options.get("sort_keys", False)
        content = json.dumps(merged, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        content_bytes = content.encode("utf-8")
        await context.storage.put(storage_key, content_bytes, "application/json")

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
    def _merge_patch(target: Any, patch: Any) -> Any:
        """JSON Merge Patch (RFC 7396)."""
        if not isinstance(patch, dict):
            return patch
        if not isinstance(target, dict):
            target = {}
        result = dict(target)
        for key, value in patch.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict):
                result[key] = JsonCrud._merge_patch(result.get(key, {}), value)
            else:
                result[key] = value
        return result
