"""
CSV CRUD — Créer, lire, modifier et supprimer des fichiers CSV.

Catégorie: data
Mode: sync

Actions:
    create  → Génère un CSV depuis des données structurées (headers + rows)
    read    → Parse un CSV et retourne les données structurées
    update  → Modifie un CSV (ajouter/modifier/supprimer des lignes)
    delete  → Supprime un fichier CSV du stockage
"""

from __future__ import annotations

import csv
import io
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


class CsvCrud(BaseTool):
    """CRUD complet pour les fichiers CSV via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="csv-crud",
            name="CSV CRUD",
            description="Créer, lire, modifier et supprimer des fichiers CSV",
            version="1.0.0",
            category="data",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=30,
            input_schema=[
                ToolParameter(name="action", type="string", required=True,
                              description="Action: create, read, update, delete"),
                ToolParameter(name="storage_key", type="string",
                              description="Chemin MinIO du fichier (requis pour read/update/delete)"),
                ToolParameter(name="data", type="object",
                              description="Données: {headers: [...], rows: [[...], ...]}"),
                ToolParameter(name="options", type="object",
                              description="Options: {delimiter, encoding, quoting}"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string",
                              description="Chemin MinIO du fichier créé/modifié"),
                ToolParameter(name="headers", type="array"),
                ToolParameter(name="rows", type="array"),
                ToolParameter(name="row_count", type="integer"),
                ToolParameter(name="column_count", type="integer"),
            ],
            examples=[
                ToolExample(
                    description="Créer un CSV",
                    input={
                        "action": "create",
                        "storage_key": "data/contacts.csv",
                        "data": {
                            "headers": ["nom", "email", "ville"],
                            "rows": [
                                ["Alice", "alice@mail.com", "Paris"],
                                ["Bob", "bob@mail.com", "Lyon"],
                            ],
                        },
                    },
                    output={"storage_key": "data/contacts.csv", "row_count": 2},
                ),
                ToolExample(
                    description="Lire un CSV",
                    input={"action": "read", "storage_key": "data/contacts.csv"},
                    output={
                        "headers": ["nom", "email", "ville"],
                        "rows": [["Alice", "alice@mail.com", "Paris"]],
                        "row_count": 1,
                        "column_count": 3,
                    },
                ),
            ],
            tags=["data", "csv", "crud", "tabular"],
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

        headers = data.get("headers", [])
        rows = data.get("rows", [])

        delimiter = options.get("delimiter", ",")
        encoding = options.get("encoding", "utf-8")

        output = io.StringIO()
        writer = csv.writer(output, delimiter=delimiter)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)

        content = output.getvalue().encode(encoding)
        await context.storage.put(storage_key, content, "text/csv")

        return self.success({
            "storage_key": storage_key,
            "row_count": len(rows),
            "column_count": len(headers) if headers else (len(rows[0]) if rows else 0),
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        encoding = options.get("encoding", "utf-8")
        delimiter = options.get("delimiter", ",")

        text = file_data.decode(encoding)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        all_rows = list(reader)

        if not all_rows:
            return self.success({"headers": [], "rows": [], "row_count": 0, "column_count": 0})

        headers = all_rows[0]
        rows = all_rows[1:]

        return self.success({
            "storage_key": storage_key,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers),
        })

    async def _update(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        data = params.get("data", {})
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour update", ToolErrorCode.INVALID_PARAMS)

        # Lire le fichier existant
        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        encoding = options.get("encoding", "utf-8")
        delimiter = options.get("delimiter", ",")

        text = file_data.decode(encoding)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        all_rows = list(reader)

        headers = all_rows[0] if all_rows else []
        rows = all_rows[1:] if len(all_rows) > 1 else []

        # Appliquer les modifications
        add_rows = data.get("add_rows", [])
        if add_rows:
            rows.extend(add_rows)

        update_rows = data.get("update_rows", {})
        for idx_str, new_row in update_rows.items():
            idx = int(idx_str)
            if 0 <= idx < len(rows):
                rows[idx] = new_row

        delete_indices = sorted(data.get("delete_rows", []), reverse=True)
        for idx in delete_indices:
            if 0 <= idx < len(rows):
                rows.pop(idx)

        new_headers = data.get("headers")
        if new_headers:
            headers = new_headers

        # Réécrire
        output = io.StringIO()
        writer = csv.writer(output, delimiter=delimiter)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)

        content = output.getvalue().encode(encoding)
        await context.storage.put(storage_key, content, "text/csv")

        return self.success({
            "storage_key": storage_key,
            "row_count": len(rows),
            "column_count": len(headers),
        })

    async def _delete(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour delete", ToolErrorCode.INVALID_PARAMS)

        deleted = await context.storage.delete(storage_key)
        if not deleted:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        return self.success({"storage_key": storage_key, "deleted": True})
