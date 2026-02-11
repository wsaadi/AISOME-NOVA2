"""
SVG CRUD — Créer, lire, modifier et supprimer des fichiers SVG.

Catégorie: media
Mode: sync

Actions:
    create  → Génère un SVG depuis des données structurées (éléments, attributs)
    read    → Parse un SVG et retourne les éléments structurés
    update  → Modifie un SVG (ajouter/modifier des éléments, attributs)
    delete  → Supprime un fichier SVG du stockage
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
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

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


class SvgCrud(BaseTool):
    """CRUD complet pour les fichiers SVG via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="svg-crud",
            name="SVG CRUD",
            description="Créer, lire, modifier et supprimer des fichiers SVG",
            version="1.0.0",
            category="media",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=15,
            input_schema=[
                ToolParameter(name="action", type="string", required=True,
                              description="Action: create, read, update, delete"),
                ToolParameter(name="storage_key", type="string",
                              description="Chemin MinIO du fichier"),
                ToolParameter(name="data", type="object",
                              description="Contenu: {width, height, viewBox, elements: [{tag, attrs, text}]}"),
                ToolParameter(name="options", type="object",
                              description="Options: {pretty_print}"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string"),
                ToolParameter(name="elements", type="array",
                              description="Liste des éléments SVG"),
                ToolParameter(name="element_count", type="integer"),
                ToolParameter(name="width", type="string"),
                ToolParameter(name="height", type="string"),
                ToolParameter(name="svg_content", type="string",
                              description="Contenu SVG brut"),
            ],
            examples=[
                ToolExample(
                    description="Créer un SVG avec des formes",
                    input={
                        "action": "create",
                        "storage_key": "images/diagram.svg",
                        "data": {
                            "width": "400",
                            "height": "300",
                            "elements": [
                                {"tag": "rect", "attrs": {"x": "10", "y": "10", "width": "100", "height": "80", "fill": "#4472C4", "rx": "5"}},
                                {"tag": "text", "attrs": {"x": "60", "y": "55", "text-anchor": "middle", "fill": "white"}, "text": "Hello"},
                                {"tag": "circle", "attrs": {"cx": "250", "cy": "150", "r": "60", "fill": "#ED7D31"}},
                                {"tag": "line", "attrs": {"x1": "110", "y1": "50", "x2": "190", "y2": "150", "stroke": "#333", "stroke-width": "2"}},
                            ],
                        },
                    },
                    output={"storage_key": "images/diagram.svg", "element_count": 4},
                ),
            ],
            tags=["media", "svg", "image", "vector", "crud"],
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

        if not storage_key:
            return self.error("storage_key requis pour create", ToolErrorCode.INVALID_PARAMS)

        width = data.get("width", "800")
        height = data.get("height", "600")
        view_box = data.get("viewBox", f"0 0 {width} {height}")

        root = ET.Element(f"{{{SVG_NS}}}svg")
        root.set("xmlns", SVG_NS)
        root.set("width", str(width))
        root.set("height", str(height))
        root.set("viewBox", view_box)

        elements = data.get("elements", [])
        for elem_data in elements:
            self._add_element(root, elem_data)

        svg_content = self._serialize_svg(root)
        await context.storage.put(storage_key, svg_content.encode("utf-8"), "image/svg+xml")

        return self.success({
            "storage_key": storage_key,
            "element_count": len(elements),
            "width": str(width),
            "height": str(height),
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            root = ET.fromstring(file_data.decode("utf-8"))
        except ET.ParseError as e:
            return self.error(f"SVG invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        elements = []
        for child in root:
            tag = child.tag.replace(f"{{{SVG_NS}}}", "")
            elem_info = {
                "tag": tag,
                "attrs": dict(child.attrib),
            }
            if child.text and child.text.strip():
                elem_info["text"] = child.text.strip()
            elements.append(elem_info)

        width = root.get("width", "")
        height = root.get("height", "")

        return self.success({
            "storage_key": storage_key,
            "elements": elements,
            "element_count": len(elements),
            "width": width,
            "height": height,
            "svg_content": file_data.decode("utf-8"),
        })

    async def _update(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        data = params.get("data", {})

        if not storage_key:
            return self.error("storage_key requis pour update", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            root = ET.fromstring(file_data.decode("utf-8"))
        except ET.ParseError as e:
            return self.error(f"SVG invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        # Modifier les attributs du SVG racine
        root_attrs = data.get("root_attrs", {})
        for key, value in root_attrs.items():
            root.set(key, str(value))

        # Ajouter des éléments
        add_elements = data.get("add_elements", [])
        for elem_data in add_elements:
            self._add_element(root, elem_data)

        # Modifier des éléments existants par index
        update_elements = data.get("update_elements", {})
        children = list(root)
        for idx_str, updates in update_elements.items():
            idx = int(idx_str)
            if 0 <= idx < len(children):
                for key, value in updates.get("attrs", {}).items():
                    children[idx].set(key, str(value))
                if "text" in updates:
                    children[idx].text = updates["text"]

        # Supprimer des éléments par index
        delete_indices = sorted(data.get("delete_elements", []), reverse=True)
        children = list(root)
        for idx in delete_indices:
            if 0 <= idx < len(children):
                root.remove(children[idx])

        svg_content = self._serialize_svg(root)
        await context.storage.put(storage_key, svg_content.encode("utf-8"), "image/svg+xml")

        return self.success({
            "storage_key": storage_key,
            "element_count": len(list(root)),
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
    def _add_element(parent: ET.Element, elem_data: dict) -> None:
        """Ajoute un élément SVG à un parent."""
        tag = elem_data.get("tag", "g")
        attrs = elem_data.get("attrs", {})

        element = ET.SubElement(parent, f"{{{SVG_NS}}}{tag}")
        for key, value in attrs.items():
            element.set(key, str(value))

        if "text" in elem_data:
            element.text = elem_data["text"]

        # Éléments enfants récursifs
        for child_data in elem_data.get("children", []):
            SvgCrud._add_element(element, child_data)

    @staticmethod
    def _serialize_svg(root: ET.Element) -> str:
        """Sérialise un arbre SVG en string XML."""
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            root, encoding="unicode"
        )
