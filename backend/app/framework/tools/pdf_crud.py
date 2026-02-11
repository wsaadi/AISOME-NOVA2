"""
PDF CRUD — Créer, lire, modifier et supprimer des fichiers PDF.

Catégorie: file
Mode: sync

Actions:
    create  → Génère un PDF depuis du texte structuré (titre, paragraphes, tableaux)
    read    → Extrait le texte et les métadonnées d'un PDF
    update  → Modifie un PDF (merge, extraire des pages, ajouter watermark)
    delete  → Supprime un fichier PDF du stockage
"""

from __future__ import annotations

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


class PdfCrud(BaseTool):
    """CRUD complet pour les fichiers PDF via MinIO."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="pdf-crud",
            name="PDF CRUD",
            description="Créer, lire, modifier et supprimer des fichiers PDF",
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
                              description="Contenu: {title, paragraphs, tables, author, subject}"),
                ToolParameter(name="options", type="object",
                              description="Options: {page_size, margin, font_size, extract_pages, merge_keys, watermark}"),
            ],
            output_schema=[
                ToolParameter(name="storage_key", type="string"),
                ToolParameter(name="text", type="string", description="Texte extrait"),
                ToolParameter(name="page_count", type="integer"),
                ToolParameter(name="metadata", type="object",
                              description="Métadonnées: {author, title, subject, creator}"),
            ],
            examples=[
                ToolExample(
                    description="Créer un PDF",
                    input={
                        "action": "create",
                        "storage_key": "docs/rapport.pdf",
                        "data": {
                            "title": "Rapport Mensuel",
                            "paragraphs": [
                                "Introduction du rapport.",
                                "Les résultats de janvier sont encourageants.",
                            ],
                            "author": "AISOME",
                        },
                    },
                    output={"storage_key": "docs/rapport.pdf", "page_count": 1},
                ),
                ToolExample(
                    description="Lire un PDF",
                    input={"action": "read", "storage_key": "docs/rapport.pdf"},
                    output={"text": "Rapport Mensuel\n...", "page_count": 1},
                ),
                ToolExample(
                    description="Merger deux PDFs",
                    input={
                        "action": "update",
                        "storage_key": "docs/merged.pdf",
                        "options": {"merge_keys": ["docs/part1.pdf", "docs/part2.pdf"]},
                    },
                    output={"storage_key": "docs/merged.pdf", "page_count": 10},
                ),
            ],
            tags=["file", "pdf", "crud", "document"],
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
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        storage_key = params.get("storage_key", "")
        data = params.get("data", {})
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour create", ToolErrorCode.INVALID_PARAMS)

        page_size = A4 if options.get("page_size", "A4") == "A4" else letter
        margin = options.get("margin", 2.5)
        font_size = options.get("font_size", 11)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=margin * cm,
            rightMargin=margin * cm,
            topMargin=margin * cm,
            bottomMargin=margin * cm,
        )

        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=font_size,
            leading=font_size * 1.4,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading1"],
            fontSize=font_size + 4,
            spaceAfter=12,
            spaceBefore=12,
        )

        elements = []

        # Titre
        title = data.get("title")
        if title:
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.5 * cm))

        # Paragraphes
        paragraphs = data.get("paragraphs", [])
        for para in paragraphs:
            if isinstance(para, str):
                elements.append(Paragraph(para, body_style))
            elif isinstance(para, dict):
                text = para.get("text", "")
                style = para.get("style", "normal")
                if style == "heading":
                    elements.append(Paragraph(text, heading_style))
                else:
                    elements.append(Paragraph(text, body_style))

        # Tableaux
        tables = data.get("tables", [])
        for table_data in tables:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            all_rows = []
            if headers:
                all_rows.append(headers)
            all_rows.extend(rows)
            if all_rows:
                elements.append(Spacer(1, 0.3 * cm))
                t = Table(all_rows)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), "#4472C4"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), "#FFFFFF"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, "#CCCCCC"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["#F2F2F2", "#FFFFFF"]),
                ]))
                elements.append(t)

        if not elements:
            elements.append(Paragraph("&nbsp;", body_style))

        # Métadonnées du PDF
        doc.title = data.get("title", "")
        doc.author = data.get("author", "AISOME NOVA2")
        doc.subject = data.get("subject", "")

        doc.build(elements)
        buffer.seek(0)

        await context.storage.put(storage_key, buffer.getvalue(), "application/pdf")

        return self.success({
            "storage_key": storage_key,
            "page_count": 1,  # SimpleDocTemplate ne donne pas le count facilement
        })

    async def _read(self, params: dict[str, Any], context) -> ToolResult:
        from PyPDF2 import PdfReader

        storage_key = params.get("storage_key", "")
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour read", ToolErrorCode.INVALID_PARAMS)

        file_data = await context.storage.get(storage_key)
        if file_data is None:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        try:
            reader = PdfReader(io.BytesIO(file_data))
        except Exception as e:
            return self.error(f"Fichier PDF invalide: {e}", ToolErrorCode.PROCESSING_ERROR)

        # Extraire des pages spécifiques ou toutes
        extract_pages = options.get("extract_pages")
        pages_text = []

        for i, page in enumerate(reader.pages):
            if extract_pages and i not in extract_pages:
                continue
            text = page.extract_text() or ""
            pages_text.append(text)

        # Métadonnées
        meta = reader.metadata
        pdf_metadata = {}
        if meta:
            pdf_metadata = {
                "author": meta.author or "",
                "title": meta.title or "",
                "subject": meta.subject or "",
                "creator": meta.creator or "",
            }

        return self.success({
            "storage_key": storage_key,
            "text": "\n\n".join(pages_text),
            "page_count": len(reader.pages),
            "metadata": pdf_metadata,
        })

    async def _update(self, params: dict[str, Any], context) -> ToolResult:
        from PyPDF2 import PdfMerger, PdfReader, PdfWriter

        storage_key = params.get("storage_key", "")
        options = params.get("options", {})

        if not storage_key:
            return self.error("storage_key requis pour update", ToolErrorCode.INVALID_PARAMS)

        # Mode merge : fusionner plusieurs PDFs
        merge_keys = options.get("merge_keys", [])
        if merge_keys:
            merger = PdfMerger()
            for key in merge_keys:
                pdf_data = await context.storage.get(key)
                if pdf_data is None:
                    return self.error(
                        f"Fichier introuvable pour merge: {key}",
                        ToolErrorCode.FILE_NOT_FOUND,
                    )
                merger.append(io.BytesIO(pdf_data))

            buffer = io.BytesIO()
            merger.write(buffer)
            merger.close()
            buffer.seek(0)

            await context.storage.put(storage_key, buffer.getvalue(), "application/pdf")

            reader = PdfReader(io.BytesIO(buffer.getvalue()))
            return self.success({
                "storage_key": storage_key,
                "page_count": len(reader.pages),
            })

        # Mode extract : extraire des pages spécifiques
        extract_pages = options.get("extract_pages")
        if extract_pages:
            file_data = await context.storage.get(storage_key)
            if file_data is None:
                return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

            reader = PdfReader(io.BytesIO(file_data))
            writer = PdfWriter()

            for page_idx in extract_pages:
                if 0 <= page_idx < len(reader.pages):
                    writer.add_page(reader.pages[page_idx])

            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            output_key = options.get("output_key", storage_key)
            await context.storage.put(output_key, buffer.getvalue(), "application/pdf")

            return self.success({
                "storage_key": output_key,
                "page_count": len(writer.pages),
            })

        return self.error(
            "update nécessite merge_keys ou extract_pages dans options",
            ToolErrorCode.INVALID_PARAMS,
        )

    async def _delete(self, params: dict[str, Any], context) -> ToolResult:
        storage_key = params.get("storage_key", "")
        if not storage_key:
            return self.error("storage_key requis pour delete", ToolErrorCode.INVALID_PARAMS)

        deleted = await context.storage.delete(storage_key)
        if not deleted:
            return self.error(f"Fichier introuvable: {storage_key}", ToolErrorCode.FILE_NOT_FOUND)

        return self.success({"storage_key": storage_key, "deleted": True})
