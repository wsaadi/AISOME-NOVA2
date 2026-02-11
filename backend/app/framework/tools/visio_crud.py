"""
Visio CRUD — Créer, lire, modifier et supprimer des fichiers VSDX.

Catégorie: file
Mode: sync

Le format VSDX est un ZIP contenant des fichiers XML (Open Packaging Convention).
Ce tool manipule la structure XML interne pour les opérations CRUD.

Actions:
    create  → Génère un VSDX basique depuis des données structurées (pages, shapes)
    read    → Extrait le contenu d'un VSDX (pages, shapes, texte, connexions)
    update  → Modifie un VSDX (ajouter des shapes, modifier du texte)
    delete  → Supprime un fichier VSDX du stockage
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
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

VISIO_NS = {
    "v": "http://schemas.microsoft.com/office/visio/2012/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

for prefix, uri in VISIO_NS.items():
    ET.register_namespace(prefix, uri)


class VisioCrud(BaseTool):
    """CRUD pour les fichiers Visio VSDX via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="visio-crud",
            name="Visio CRUD",
            description="Créer, lire, modifier et supprimer des fichiers Visio (VSDX)",
            version="1.0.0",
            category="file",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=30,
            input_schema=[
                ToolParameter(name="action", type="string", required=True,
                              description="Action: create, read, update, delete"),
                ToolParameter(name="storage_key", type="string",
                              description="Chemin MinIO du fichier"),
                ToolParameter(name="data", type="object",
                              description="Contenu: {pages: [{name, shapes: [{text, x, y, width, height, type}]}]}"),
                ToolParameter(name="options", type="object",
                              description="Options additionnelles"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string"),
                ToolParameter(name="pages", type="array",
                              description="Liste des pages avec shapes"),
                ToolParameter(name="page_count", type="integer"),
                ToolParameter(name="shape_count", type="integer"),
                ToolParameter(name="texts", type="array",
                              description="Tous les textes extraits"),
            ],
            examples=[
                ToolExample(
                    description="Créer un diagramme Visio simple",
                    input={
                        "action": "create",
                        "storage_key": "diagrams/process.vsdx",
                        "data": {
                            "pages": [
                                {
                                    "name": "Page-1",
                                    "shapes": [
                                        {"text": "Début", "x": 2, "y": 8, "width": 2, "height": 1, "type": "rectangle"},
                                        {"text": "Process", "x": 2, "y": 5, "width": 2, "height": 1, "type": "rectangle"},
                                        {"text": "Fin", "x": 2, "y": 2, "width": 2, "height": 1, "type": "rectangle"},
                                    ],
                                },
                            ],
                        },
                    },
                    output={"storage_key": "diagrams/process.vsdx", "page_count": 1, "shape_count": 3},
                ),
            ],
            tags=["file", "visio", "vsdx", "crud", "diagram", "office"],
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

        pages_data = data.get("pages", [{"name": "Page-1", "shapes": []}])
        total_shapes = 0

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Content Types
            zf.writestr("[Content_Types].xml", self._content_types_xml(len(pages_data)))

            # Rels
            zf.writestr("_rels/.rels", self._root_rels_xml())

            # Document
            zf.writestr("visio/document.xml", self._document_xml())
            zf.writestr("visio/_rels/document.xml.rels", self._document_rels_xml(len(pages_data)))

            # Pages index
            zf.writestr("visio/pages/pages.xml", self._pages_index_xml(pages_data))
            zf.writestr("visio/pages/_rels/pages.xml.rels", self._pages_rels_xml(len(pages_data)))

            # Chaque page
            for idx, page_data in enumerate(pages_data):
                shapes = page_data.get("shapes", [])
                total_shapes += len(shapes)
                page_xml = self._page_xml(shapes)
                zf.writestr(f"visio/pages/page{idx + 1}.xml", page_xml)

        buffer.seek(0)
        await context.storage.put(
            storage_key, buffer.getvalue(),
            "application/vnd.ms-visio.drawing",
        )

        return self.success({
            "storage_key": storage_key,
            "page_count": len(pages_data),
            "shape_count": total_shapes,
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            zf = zipfile.ZipFile(io.BytesIO(file_data), "r")
        except zipfile.BadZipFile:
            return self.error("Fichier VSDX invalide (pas un ZIP)", ToolErrorCode.PROCESSING_ERROR)

        pages = []
        texts = []
        total_shapes = 0

        # Lister les fichiers de pages
        page_files = sorted([
            name for name in zf.namelist()
            if name.startswith("visio/pages/page") and name.endswith(".xml")
        ])

        for page_file in page_files:
            try:
                page_xml = zf.read(page_file).decode("utf-8")
                root = ET.fromstring(page_xml)
            except (ET.ParseError, KeyError):
                continue

            shapes = []
            for shape_elem in root.iter():
                tag = shape_elem.tag.split("}")[-1] if "}" in shape_elem.tag else shape_elem.tag
                if tag == "Shape":
                    shape_info = {"id": shape_elem.get("ID", ""), "attrs": dict(shape_elem.attrib)}

                    # Extraire le texte
                    for text_elem in shape_elem.iter():
                        text_tag = text_elem.tag.split("}")[-1] if "}" in text_elem.tag else text_elem.tag
                        if text_tag == "Text" and text_elem.text:
                            shape_info["text"] = text_elem.text.strip()
                            texts.append(text_elem.text.strip())

                    shapes.append(shape_info)
                    total_shapes += 1

            pages.append({
                "file": page_file,
                "shapes": shapes,
                "shape_count": len(shapes),
            })

        zf.close()

        return self.success({
            "storage_key": storage_key,
            "pages": pages,
            "page_count": len(pages),
            "shape_count": total_shapes,
            "texts": texts,
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
            input_zf = zipfile.ZipFile(io.BytesIO(file_data), "r")
        except zipfile.BadZipFile:
            return self.error("Fichier VSDX invalide", ToolErrorCode.PROCESSING_ERROR)

        # Lire tous les fichiers existants
        existing_files = {}
        for name in input_zf.namelist():
            existing_files[name] = input_zf.read(name)

        input_zf.close()

        # Appliquer les remplacements de texte
        replacements = data.get("replace", {})
        if replacements:
            for name, content in existing_files.items():
                if name.startswith("visio/pages/page") and name.endswith(".xml"):
                    text = content.decode("utf-8")
                    for old_text, new_text in replacements.items():
                        text = text.replace(old_text, new_text)
                    existing_files[name] = text.encode("utf-8")

        # Réécrire le ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in existing_files.items():
                zf.writestr(name, content)

        buffer.seek(0)
        await context.storage.put(
            storage_key, buffer.getvalue(),
            "application/vnd.ms-visio.drawing",
        )

        return self.success({
            "storage_key": storage_key,
        })

    async def _delete(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour delete", ToolErrorCode.INVALID_PARAMS)

        deleted = await context.storage.delete(storage_key)
        if not deleted:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        return self.success({"storage_key": storage_key, "deleted": True})

    # --- Helpers XML pour la création VSDX ---

    @staticmethod
    def _content_types_xml(page_count: int) -> str:
        parts = []
        for i in range(1, page_count + 1):
            parts.append(f'  <Override PartName="/visio/pages/page{i}.xml" '
                         f'ContentType="application/vnd.ms-visio.page+xml"/>')
        pages_parts = "\n".join(parts)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>
  <Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
{pages_parts}
</Types>"""

    @staticmethod
    def _root_rels_xml() -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>
</Relationships>"""

    @staticmethod
    def _document_xml() -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2012/main"
               xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
</VisioDocument>"""

    @staticmethod
    def _document_rels_xml(page_count: int) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>
</Relationships>"""

    @staticmethod
    def _pages_index_xml(pages_data: list) -> str:
        ns = VISIO_NS["v"]
        pages_entries = []
        for idx, page in enumerate(pages_data):
            name = page.get("name", f"Page-{idx + 1}")
            pages_entries.append(
                f'  <Page ID="{idx}" Name="{name}" '
                f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'\n    <Rel r:id="rId{idx + 1}"/>'
                f"\n  </Page>"
            )
        entries = "\n".join(pages_entries)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Pages xmlns="{ns}">
{entries}
</Pages>"""

    @staticmethod
    def _pages_rels_xml(page_count: int) -> str:
        rels = []
        for i in range(1, page_count + 1):
            rels.append(
                f'  <Relationship Id="rId{i}" '
                f'Type="http://schemas.microsoft.com/visio/2010/relationships/page" '
                f'Target="page{i}.xml"/>'
            )
        entries = "\n".join(rels)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{entries}
</Relationships>"""

    @staticmethod
    def _page_xml(shapes: list) -> str:
        ns = VISIO_NS["v"]
        shape_entries = []
        for idx, shape in enumerate(shapes):
            text = shape.get("text", "")
            x = shape.get("x", 4)
            y = shape.get("y", 4)
            w = shape.get("width", 2)
            h = shape.get("height", 1)

            shape_entries.append(f"""    <Shape ID="{idx + 1}" NameU="Shape.{idx + 1}" Type="Shape">
      <Cell N="PinX" V="{x}"/>
      <Cell N="PinY" V="{y}"/>
      <Cell N="Width" V="{w}"/>
      <Cell N="Height" V="{h}"/>
      <Text>{text}</Text>
    </Shape>""")

        shapes_xml = "\n".join(shape_entries)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<PageContents xmlns="{ns}">
  <Shapes>
{shapes_xml}
  </Shapes>
</PageContents>"""
