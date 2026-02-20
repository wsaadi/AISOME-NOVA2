"""
Tender Assistant Agent - Assistant complet pour la réponse aux appels d'offres.

Fonctionnalités:
    - Gestion de documents (upload, catégorisation, tags)
    - Analyse de documents AO (ancien et nouveau)
    - Comparaison ancien AO vs nouveau AO
    - Analyse de la réponse précédente
    - Génération de structure de réponse
    - Rédaction assistée par chapitre
    - Vérification de conformité
    - Gestion des points d'amélioration
    - Export DOCX avec template corporate
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

from app.framework.base import BaseAgent
from app.framework.schemas import (
    AgentManifest,
    AgentResponse,
    AgentResponseChunk,
    UserMessage,
)

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext

# Storage key constants
STATE_KEY = "project/state.json"
DOCS_META_KEY = "project/documents.json"
CHAPTERS_KEY = "project/chapters.json"
IMPROVEMENTS_KEY = "project/improvements.json"
ANALYSIS_KEY = "project/analyses.json"
PSEUDONYMS_KEY = "project/pseudonyms.json"


class TenderAssistantAgent(BaseAgent):
    """Agent spécialisé dans l'aide à la réponse aux appels d'offres."""

    @property
    def manifest(self) -> AgentManifest:
        with open(Path(__file__).parent / "manifest.json") as f:
            return AgentManifest(**json.load(f))

    # =========================================================================
    # Main dispatcher
    # =========================================================================

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        system_prompt = self._load_system_prompt()
        action = (message.metadata or {}).get("action", "chat")

        handlers = {
            "upload_document": self._handle_upload,
            "delete_document": self._handle_delete_document,
            "update_document_meta": self._handle_update_document_meta,
            "analyze_document": self._handle_analyze_document,
            "analyze_all_documents": self._handle_analyze_all_documents,
            "compare_tenders": self._handle_compare_tenders,
            "generate_structure": self._handle_generate_structure,
            "update_structure": self._handle_update_structure,
            "write_chapter": self._handle_write_chapter,
            "write_all_chapters": self._handle_write_all_chapters,
            "improve_chapter": self._handle_improve_chapter,
            "improve_all_chapters": self._handle_improve_all_chapters,
            "check_compliance": self._handle_check_compliance,
            "add_improvement": self._handle_add_improvement,
            "delete_improvement": self._handle_delete_improvement,
            "export_docx": self._handle_export_docx,
            "upload_template": self._handle_upload_template,
            "get_project_state": self._handle_get_state,
            "update_pseudonyms": self._handle_update_pseudonyms,
            "apply_pseudonyms": self._handle_apply_pseudonyms,
            "detect_confidential": self._handle_detect_confidential,
            "cleanup_formatting": self._handle_cleanup_formatting,
            "export_workspace": self._handle_export_workspace,
            "import_workspace": self._handle_import_workspace,
            "chat": self._handle_chat,
        }

        handler = handlers.get(action, self._handle_chat)
        return await handler(message, context, system_prompt)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        system_prompt = self._load_system_prompt()
        action = (message.metadata or {}).get("action", "chat")

        # Stream only for chat and write actions
        if action in ("chat", "write_chapter", "improve_chapter"):
            async for chunk in self._stream_handler(message, context, system_prompt, action):
                yield chunk
            return

        # Non-streaming actions: execute and yield result
        response = await self.handle_message(message, context)
        yield AgentResponseChunk(content=response.content, metadata=response.metadata)
        yield AgentResponseChunk(content="", is_final=True)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _load_system_prompt(self) -> str:
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    async def _load_json(self, context: AgentContext, key: str, default: Any = None) -> Any:
        try:
            data = await context.storage.get(key)
            if data:
                return json.loads(data.decode("utf-8"))
        except Exception:
            pass
        return default if default is not None else {}

    async def _save_json(self, context: AgentContext, key: str, data: Any) -> None:
        await context.storage.put(
            key, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json"
        )

    async def _get_documents_meta(self, context: AgentContext) -> list[dict]:
        return await self._load_json(context, DOCS_META_KEY, [])

    async def _save_documents_meta(self, context: AgentContext, docs: list[dict]) -> None:
        await self._save_json(context, DOCS_META_KEY, docs)

    async def _get_chapters(self, context: AgentContext) -> list[dict]:
        return await self._load_json(context, CHAPTERS_KEY, [])

    async def _save_chapters(self, context: AgentContext, chapters: list[dict]) -> None:
        await self._save_json(context, CHAPTERS_KEY, chapters)

    async def _get_improvements(self, context: AgentContext) -> list[dict]:
        return await self._load_json(context, IMPROVEMENTS_KEY, [])

    async def _save_improvements(self, context: AgentContext, items: list[dict]) -> None:
        await self._save_json(context, IMPROVEMENTS_KEY, items)

    async def _get_analyses(self, context: AgentContext) -> dict:
        return await self._load_json(context, ANALYSIS_KEY, {})

    async def _save_analyses(self, context: AgentContext, analyses: dict) -> None:
        await self._save_json(context, ANALYSIS_KEY, analyses)

    async def _get_pseudonyms(self, context: AgentContext) -> list[dict]:
        return await self._load_json(context, PSEUDONYMS_KEY, [])

    async def _save_pseudonyms(self, context: AgentContext, items: list[dict]) -> None:
        await self._save_json(context, PSEUDONYMS_KEY, items)

    def _pseudonymize(self, text: str, pseudonyms: list[dict]) -> str:
        """Replace real values with placeholders before sending to LLM."""
        for entry in pseudonyms:
            real = entry.get("real", "")
            placeholder = entry.get("placeholder", "")
            if real and placeholder:
                text = text.replace(real, placeholder)
        return text

    def _depseudonymize(self, text: str, pseudonyms: list[dict]) -> str:
        """Replace placeholders with real values (for display)."""
        for entry in pseudonyms:
            real = entry.get("real", "")
            placeholder = entry.get("placeholder", "")
            if real and placeholder:
                text = text.replace(placeholder, real)
        return text

    def _clean_chapter_content(self, text: str) -> str:
        """Strip markdown code fences, normalize line breaks, and fix LLM artefacts."""
        stripped = text.strip()
        # Remove wrapping ```markdown ... ``` or ```\n ... ```
        m = re.match(r"^```(?:markdown|md)?\s*\n(.*?)```\s*$", stripped, re.DOTALL)
        if m:
            stripped = m.group(1).strip()
        # Remove LLM intro commentary (e.g. "Voici une version..." before actual content)
        intro_pattern = re.match(
            r"^(Voici\s+(?:une|le|la|les|un)\s+.*?[.!]\s*\n{1,2})(#{1,4}\s+|\*\*|\|)",
            stripped, re.DOTALL | re.IGNORECASE,
        )
        if intro_pattern:
            stripped = stripped[len(intro_pattern.group(1)):]
        # Remove JSON metadata blocks (LLM sometimes appends structured JSON)
        # Pattern: optional intro line + { "type": "chapter_content", ... }
        stripped = re.sub(
            r'\n*(?:Bloc JSON[^\n]*\n)?```(?:json)?\s*\n\s*\{[^{}]*"type"\s*:\s*"chapter_content"[^}]*(?:\{[^}]*\}[^}]*)*\}[^`]*```',
            '', stripped, flags=re.DOTALL
        )
        # Also catch unformatted JSON blocks (no code fences)
        stripped = re.sub(
            r'\n+(?:Bloc JSON[^\n]*\n+)\s*\{[^{}]*"type"\s*:\s*"chapter_content"[\s\S]*$',
            '', stripped
        )
        # Ensure blank lines before headings (required for proper markdown parsing)
        stripped = re.sub(r"([^\n])\n(#{1,4}\s)", r"\1\n\n\2", stripped)
        # Ensure blank lines before table blocks (only before first | row, not between table rows)
        stripped = re.sub(r"(^|\n)([^\n|][^\n]*)\n(\|)", r"\1\2\n\n\3", stripped)
        # Ensure blank lines before/after horizontal rules
        stripped = re.sub(r"([^\n])\n(---+)\n", r"\1\n\n\2\n\n", stripped)
        # Normalize Windows line endings
        stripped = stripped.replace("\r\n", "\n")
        return stripped.strip()

    async def _llm_chat(
        self, context: AgentContext, prompt: str,
        system_prompt: str, temperature: float = 0.3, max_tokens: int = 4096,
    ) -> str:
        """Wrapper around context.llm.chat that auto-pseudonymizes the prompt."""
        pseudonyms = await self._get_pseudonyms(context)
        if pseudonyms:
            prompt = self._pseudonymize(prompt, pseudonyms)
            system_prompt = self._pseudonymize(system_prompt, pseudonyms)
        return await context.llm.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _extract_images_from_docx(
        self, context: AgentContext, file_key: str, doc_id: str
    ) -> list[dict]:
        """Extract embedded images from a DOCX file and store them."""
        try:
            from docx import Document as DocxDocument
            raw = await context.storage.get(file_key)
            if not raw:
                return []
            doc = DocxDocument(io.BytesIO(raw))
            images = []
            for i, rel in enumerate(doc.part.rels.values()):
                if "image" in rel.reltype:
                    try:
                        img_data = rel.target_part.blob
                        ext = rel.target_ref.split(".")[-1] if "." in rel.target_ref else "png"
                        ct = f"image/{ext}" if ext in ("png", "jpeg", "jpg", "gif", "svg") else "image/png"
                        img_key = f"documents/images/{doc_id}/image_{i+1}.{ext}"
                        await context.storage.put(img_key, img_data, ct)
                        images.append({
                            "key": img_key,
                            "name": f"image_{i+1}.{ext}",
                            "contentType": ct,
                            "size": len(img_data),
                        })
                    except Exception as e:
                        logger.warning(f"Failed to extract image {i} from DOCX: {e}")
            return images
        except Exception as e:
            logger.warning(f"Failed to extract images from DOCX: {e}")
            return []

    async def _extract_document_text(
        self, context: AgentContext, file_key: str, file_name: str
    ) -> str:
        lower = file_name.lower()
        if lower.endswith(".pdf"):
            result = await context.tools.execute("pdf-crud", {"action": "read", "storage_key": file_key})
        elif lower.endswith((".docx", ".doc")):
            result = await context.tools.execute("word-crud", {"action": "read", "storage_key": file_key})
        elif lower.endswith((".xlsx", ".xls")):
            result = await context.tools.execute("excel-crud", {"action": "read", "storage_key": file_key})
        elif lower.endswith(".csv"):
            result = await context.tools.execute("csv-crud", {"action": "read", "storage_key": file_key})
        elif lower.endswith(".txt"):
            raw = await context.storage.get(file_key)
            return raw.decode("utf-8") if raw else ""
        else:
            return f"[Format non supporté: {file_name}]"

        if not result.success:
            return f"[Erreur de lecture: {result.error}]"
        return result.data.get("text", "") if result.data else ""

    # =========================================================================
    # Document management handlers
    # =========================================================================

    async def _handle_upload(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        file_key = meta.get("fileKey", "")
        file_name = meta.get("fileName", "document")
        category = meta.get("category", "other")
        tags = meta.get("tags", [])

        if not file_key:
            return AgentResponse(content="Aucun fichier fourni.", metadata={"error": True})

        context.set_progress(10, "Enregistrement du document...")

        docs = await self._get_documents_meta(context)

        doc_entry = {
            "id": f"doc-{len(docs) + 1}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "fileKey": file_key,
            "fileName": file_name,
            "category": category,
            "tags": tags,
            "uploadedAt": datetime.now().isoformat(),
            "analyzed": False,
            "textKey": None,
        }

        # Extract and store text
        context.set_progress(30, "Extraction du texte...")
        text = await self._extract_document_text(context, file_key, file_name)

        if text and not text.startswith("["):
            text_key = f"documents/parsed/{doc_entry['id']}.txt"
            await context.storage.put(text_key, text.encode("utf-8"), "text/plain")
            doc_entry["textKey"] = text_key
            doc_entry["textLength"] = len(text)

        # Extract images from DOCX files (especially useful for ancienne_reponse)
        if file_name.lower().endswith((".docx", ".doc")):
            context.set_progress(60, "Extraction des images...")
            images = await self._extract_images_from_docx(context, file_key, doc_entry["id"])
            if images:
                doc_entry["images"] = images
                logger.info(f"Extracted {len(images)} images from {file_name}")

        docs.append(doc_entry)
        await self._save_documents_meta(context, docs)

        context.set_progress(100, "Document enregistré")

        return AgentResponse(
            content=f"Document **{file_name}** enregistré dans la catégorie **{category}**.",
            metadata={"type": "document_uploaded", "document": doc_entry}
        )

    async def _handle_delete_document(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        doc_id = (message.metadata or {}).get("documentId", "")
        docs = await self._get_documents_meta(context)
        docs = [d for d in docs if d["id"] != doc_id]
        await self._save_documents_meta(context, docs)

        return AgentResponse(
            content="Document supprimé.",
            metadata={"type": "document_deleted", "documentId": doc_id}
        )

    async def _handle_update_document_meta(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        doc_id = meta.get("documentId", "")
        new_category = meta.get("category")
        new_tags = meta.get("tags")

        docs = await self._get_documents_meta(context)
        for doc in docs:
            if doc["id"] == doc_id:
                if new_category is not None:
                    doc["category"] = new_category
                if new_tags is not None:
                    doc["tags"] = new_tags
                break
        await self._save_documents_meta(context, docs)

        return AgentResponse(
            content="Métadonnées du document mises à jour.",
            metadata={"type": "document_updated", "documentId": doc_id}
        )

    # =========================================================================
    # Analysis handlers
    # =========================================================================

    async def _handle_analyze_document(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        doc_id = meta.get("documentId", "")

        docs = await self._get_documents_meta(context)
        doc = next((d for d in docs if d["id"] == doc_id), None)
        if not doc:
            return AgentResponse(content="Document non trouvé.", metadata={"error": True})

        context.set_progress(10, f"Analyse de {doc['fileName']}...")

        # Load document text
        text = ""
        if doc.get("textKey"):
            raw = await context.storage.get(doc["textKey"])
            if raw:
                text = raw.decode("utf-8")

        if not text:
            text = await self._extract_document_text(context, doc["fileKey"], doc["fileName"])

        context.set_progress(40, "Analyse IA en cours...")

        analysis_prompt = f"""Analyse en détail le document suivant provenant d'un appel d'offres.

Document : {doc['fileName']}
Catégorie : {doc['category']}

CONTENU DU DOCUMENT :
{text[:15000]}

{"[Document tronqué - " + str(len(text)) + " caractères au total]" if len(text) > 15000 else ""}

Fournis une analyse structurée complète en suivant ta méthodologie d'analyse.
IMPORTANT : Inclus un bloc JSON structuré avec les données parsées (type document_analysis) en plus de ton analyse textuelle."""

        analysis = await self._llm_chat(
            context, prompt=analysis_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        context.set_progress(80, "Sauvegarde de l'analyse...")

        # Save analysis
        analyses = await self._get_analyses(context)
        analyses[doc_id] = {
            "documentId": doc_id,
            "fileName": doc["fileName"],
            "category": doc["category"],
            "content": analysis,
            "analyzedAt": datetime.now().isoformat(),
        }
        await self._save_analyses(context, analyses)

        # Mark document as analyzed
        for d in docs:
            if d["id"] == doc_id:
                d["analyzed"] = True
                break
        await self._save_documents_meta(context, docs)

        context.set_progress(100, "Analyse terminée")

        return AgentResponse(
            content=analysis,
            metadata={"type": "document_analysis", "documentId": doc_id, "fileName": doc["fileName"]}
        )

    async def _handle_analyze_all_documents(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        docs = await self._get_documents_meta(context)
        unanalyzed = [d for d in docs if not d.get("analyzed")]

        if not unanalyzed:
            return AgentResponse(
                content="Tous les documents ont déjà été analysés.",
                metadata={"type": "all_documents_analyzed"}
            )

        total = len(unanalyzed)
        analyses = await self._get_analyses(context)
        results = []

        for i, doc in enumerate(unanalyzed):
            pct = int(10 + (80 * i / total))
            context.set_progress(pct, f"Analyse de {doc['fileName']} ({i+1}/{total})...")

            # Load document text
            text = ""
            if doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    text = raw.decode("utf-8")
            if not text:
                text = await self._extract_document_text(context, doc["fileKey"], doc["fileName"])

            analysis_prompt = f"""Analyse en détail le document suivant provenant d'un appel d'offres.

Document : {doc['fileName']}
Catégorie : {doc['category']}

CONTENU DU DOCUMENT :
{text[:15000]}

{"[Document tronqué - " + str(len(text)) + " caractères au total]" if len(text) > 15000 else ""}

Fournis une analyse structurée complète en suivant ta méthodologie d'analyse.
IMPORTANT : Inclus un bloc JSON structuré avec les données parsées (type document_analysis) en plus de ton analyse textuelle."""

            analysis = await self._llm_chat(
                context, prompt=analysis_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4096,
            )

            analyses[doc["id"]] = {
                "documentId": doc["id"],
                "fileName": doc["fileName"],
                "category": doc["category"],
                "content": analysis,
                "analyzedAt": datetime.now().isoformat(),
            }

            doc["analyzed"] = True
            results.append(doc["fileName"])

        await self._save_analyses(context, analyses)
        await self._save_documents_meta(context, docs)

        context.set_progress(100, f"{total} documents analysés")

        return AgentResponse(
            content=f"**{total} documents analysés** : {', '.join(results)}",
            metadata={"type": "all_documents_analyzed", "analyzedDocIds": [d["id"] for d in unanalyzed]}
        )

    async def _handle_compare_tenders(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        context.set_progress(10, "Chargement des documents...")

        docs = await self._get_documents_meta(context)
        old_docs = [d for d in docs if d["category"] == "ancien_ao"]
        new_docs = [d for d in docs if d["category"] == "nouvel_ao"]

        if not old_docs or not new_docs:
            return AgentResponse(
                content="Il faut au moins un document dans la catégorie **ancien_ao** et un dans **nouvel_ao** pour comparer.",
                metadata={"error": True}
            )

        # Load texts
        old_texts = []
        for doc in old_docs:
            if doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    old_texts.append(f"--- {doc['fileName']} ---\n{raw.decode('utf-8')[:8000]}")

        new_texts = []
        for doc in new_docs:
            if doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    new_texts.append(f"--- {doc['fileName']} ---\n{raw.decode('utf-8')[:8000]}")

        context.set_progress(40, "Comparaison en cours...")

        comparison_prompt = f"""Compare en détail l'ancien appel d'offres avec le nouveau.

=== ANCIEN APPEL D'OFFRES ===
{chr(10).join(old_texts) if old_texts else "[Aucun texte extrait]"}

=== NOUVEL APPEL D'OFFRES ===
{chr(10).join(new_texts) if new_texts else "[Aucun texte extrait]"}

Fournis une comparaison structurée et détaillée :
1. Synthèse des changements
2. Tableau des écarts par catégorie avec niveau d'impact
3. Nouvelles exigences ajoutées
4. Exigences supprimées ou modifiées
5. Impact sur la structure de réponse
6. Recommandations prioritaires

IMPORTANT : Inclus un bloc JSON structuré (type comparison) avec toutes les différences identifiées."""

        comparison = await self._llm_chat(
            context, prompt=comparison_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        # Save comparison result
        analyses = await self._get_analyses(context)
        analyses["_comparison"] = {
            "content": comparison,
            "comparedAt": datetime.now().isoformat(),
            "oldDocs": [d["fileName"] for d in old_docs],
            "newDocs": [d["fileName"] for d in new_docs],
        }
        await self._save_analyses(context, analyses)

        context.set_progress(100, "Comparaison terminée")

        return AgentResponse(
            content=comparison,
            metadata={"type": "comparison_result"}
        )

    # =========================================================================
    # Structure handlers
    # =========================================================================

    async def _handle_generate_structure(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        context.set_progress(10, "Chargement des analyses...")

        analyses = await self._get_analyses(context)
        improvements = await self._get_improvements(context)
        docs = await self._get_documents_meta(context)

        # Gather all analysis content
        analysis_context = []
        for key, analysis in analyses.items():
            if key != "_comparison":
                analysis_context.append(f"[Analyse: {analysis.get('fileName', key)}]\n{analysis.get('content', '')[:3000]}")

        comparison = analyses.get("_comparison", {}).get("content", "")

        # Gather new AO document texts for structure extraction
        new_ao_texts = []
        for doc in docs:
            if doc["category"] == "nouvel_ao" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    new_ao_texts.append(f"--- {doc['fileName']} ---\n{raw.decode('utf-8')[:6000]}")

        # Gather previous response texts for inspiration
        prev_response_texts = []
        for doc in docs:
            if doc["category"] == "ancienne_reponse" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    prev_response_texts.append(f"--- {doc['fileName']} ---\n{raw.decode('utf-8')[:4000]}")

        improvements_text = ""
        if improvements:
            improvements_text = "\n\nPOINTS D'AMÉLIORATION À INTÉGRER :\n"
            for imp in improvements:
                improvements_text += f"- [{imp.get('priority', 'normal')}] {imp.get('title', '')}: {imp.get('description', '')}\n"

        context.set_progress(40, "Génération de la structure...")

        structure_prompt = f"""Génère une structure de réponse complète et détaillée pour le nouvel appel d'offres.

=== DOCUMENTS DU NOUVEL AO ===
{chr(10).join(new_ao_texts) if new_ao_texts else "[Pas de documents nouvel AO chargés]"}

=== ANALYSES RÉALISÉES ===
{chr(10).join(analysis_context) if analysis_context else "[Aucune analyse disponible]"}

=== COMPARAISON ANCIEN/NOUVEAU AO ===
{comparison[:4000] if comparison else "[Pas de comparaison disponible]"}

=== STRUCTURE DE LA RÉPONSE PRÉCÉDENTE ===
{chr(10).join(prev_response_texts) if prev_response_texts else "[Pas de réponse précédente chargée]"}
{improvements_text}

Génère une structure de réponse qui :
1. Respecte strictement le cadre de réponse du nouvel AO si imposé
2. Couvre TOUTES les exigences identifiées
3. Intègre les points d'amélioration
4. S'inspire de la structure de la réponse précédente quand pertinent
5. Inclut des sous-chapitres détaillés avec description et points clés

IMPORTANT : Retourne un bloc JSON structuré (type response_structure) avec la structure complète des chapitres."""

        structure = await self._llm_chat(
            context, prompt=structure_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        # Try to parse chapters from JSON in response
        chapters = self._extract_chapters_from_response(structure)

        if chapters:
            await self._save_chapters(context, chapters)

        context.set_progress(100, "Structure générée")

        return AgentResponse(
            content=structure,
            metadata={"type": "structure_generated", "chapters": chapters}
        )

    def _extract_chapters_from_response(self, response: str) -> list[dict]:
        """Extract structured chapters from LLM response JSON block."""

        def _normalize_chapters(raw_chapters: list) -> list[dict]:
            result = []
            for ch in raw_chapters:
                if not isinstance(ch, dict):
                    continue
                chapter = {
                    "id": ch.get("id", f"ch-{len(result)+1}"),
                    "number": ch.get("number", str(len(result)+1)),
                    "title": ch.get("title", "Sans titre"),
                    "description": ch.get("description", ""),
                    "requirements_covered": ch.get("requirements_covered", []),
                    "key_points": ch.get("key_points", []),
                    "estimated_pages": ch.get("estimated_pages", 3),
                    "content": "",
                    "status": "draft",
                    "sub_chapters": [],
                }
                for sub in ch.get("sub_chapters", []):
                    if not isinstance(sub, dict):
                        continue
                    chapter["sub_chapters"].append({
                        "id": sub.get("id", f"{chapter['id']}-{len(chapter['sub_chapters'])+1}"),
                        "number": sub.get("number", ""),
                        "title": sub.get("title", "Sans titre"),
                        "description": sub.get("description", ""),
                        "requirements_covered": sub.get("requirements_covered", []),
                        "key_points": sub.get("key_points", []),
                        "content": "",
                        "status": "draft",
                    })
                result.append(chapter)
            return result

        def _try_parse(text: str) -> list[dict] | None:
            """Try to parse JSON text and extract chapters."""
            try:
                data = json.loads(text)
                chapters = data.get("chapters", []) if isinstance(data, dict) else data if isinstance(data, list) else []
                if chapters:
                    result = _normalize_chapters(chapters)
                    if result:
                        return result
            except (json.JSONDecodeError, ValueError):
                pass
            return None

        def _repair_truncated_json(text: str) -> str | None:
            """Attempt to repair truncated JSON by closing open brackets/braces."""
            # Count open brackets and braces
            open_braces = 0
            open_brackets = 0
            in_string = False
            escape = False
            for c in text:
                if escape:
                    escape = False
                    continue
                if c == '\\' and in_string:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    open_braces += 1
                elif c == '}':
                    open_braces -= 1
                elif c == '[':
                    open_brackets += 1
                elif c == ']':
                    open_brackets -= 1

            if open_braces <= 0 and open_brackets <= 0:
                return None  # Not truncated

            # Trim trailing incomplete entry (e.g. cut mid-value/key)
            # Find last complete structure by looking for last },  or }
            trimmed = text.rstrip()
            # Remove trailing comma if present
            if trimmed.endswith(','):
                trimmed = trimmed[:-1]

            # Close all open brackets/braces
            repair = trimmed + (']' * open_brackets) + ('}' * open_braces)
            return repair

        # Strategy 1: extract from ```json ... ``` fenced block
        json_blocks = re.findall(r'```json\s*([\s\S]*?)```', response)
        for block in json_blocks:
            result = _try_parse(block.strip())
            if result:
                logger.info(f"Extracted {len(result)} chapters from ```json block")
                return result

        # Strategy 2: extract from any ``` ... ``` fenced block
        code_blocks = re.findall(r'```\s*([\s\S]*?)```', response)
        for block in code_blocks:
            block = block.strip()
            if block.startswith(('{', '[')):
                result = _try_parse(block)
                if result:
                    logger.info(f"Extracted {len(result)} chapters from code block")
                    return result

        # Strategy 3: truncated ```json block (no closing ```)
        truncated_match = re.search(r'```json\s*([\s\S]+)$', response)
        if truncated_match:
            raw_json = truncated_match.group(1).strip()
            # Try direct parse first
            result = _try_parse(raw_json)
            if result:
                logger.info(f"Extracted {len(result)} chapters from truncated ```json block")
                return result
            # Try repair
            repaired = _repair_truncated_json(raw_json)
            if repaired:
                result = _try_parse(repaired)
                if result:
                    logger.info(f"Extracted {len(result)} chapters from repaired truncated JSON")
                    return result

        # Strategy 4: extract individual chapter objects from truncated JSON
        # Find the "chapters" array and extract each complete {...} at array level
        chapters_start = response.find('"chapters"')
        if chapters_start == -1:
            chapters_start = response.find("'chapters'")
        if chapters_start != -1:
            bracket_pos = response.find('[', chapters_start)
            if bracket_pos != -1:
                individual_chapters = []
                depth = 0
                obj_start = -1
                i = bracket_pos + 1
                while i < len(response):
                    c = response[i]
                    # Skip strings to avoid counting braces inside values
                    if c == '"':
                        i += 1
                        while i < len(response):
                            if response[i] == '\\':
                                i += 2
                                continue
                            if response[i] == '"':
                                break
                            i += 1
                    elif c == '{':
                        if depth == 0:
                            obj_start = i
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0 and obj_start != -1:
                            obj_text = response[obj_start:i + 1]
                            try:
                                obj = json.loads(obj_text)
                                if isinstance(obj, dict) and ('title' in obj or 'id' in obj):
                                    individual_chapters.append(obj)
                            except (json.JSONDecodeError, ValueError):
                                pass
                            obj_start = -1
                    elif c == ']' and depth == 0:
                        break  # End of chapters array
                    i += 1

                if individual_chapters:
                    result = _normalize_chapters(individual_chapters)
                    if result:
                        logger.info(
                            f"Extracted {len(result)} chapters individually "
                            f"from truncated JSON (chapter-by-chapter parsing)"
                        )
                        return result

        # Strategy 5: find the largest JSON object in the raw text
        brace_depth = 0
        start = -1
        candidates = []
        for i, c in enumerate(response):
            if c == '{':
                if brace_depth == 0:
                    start = i
                brace_depth += 1
            elif c == '}':
                brace_depth -= 1
                if brace_depth == 0 and start != -1:
                    candidates.append(response[start:i + 1])
                    start = -1

        # Sort by length descending — the biggest JSON is most likely the structure
        candidates.sort(key=len, reverse=True)
        for candidate in candidates:
            result = _try_parse(candidate)
            if result:
                logger.info(f"Extracted {len(result)} chapters from raw JSON object")
                return result

        logger.warning(
            f"Failed to extract chapters from LLM response "
            f"(response length={len(response)}, first 500 chars: {response[:500]})"
        )
        return []

    async def _handle_update_structure(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        chapters = meta.get("chapters", [])

        if chapters:
            await self._save_chapters(context, chapters)

        return AgentResponse(
            content="Structure mise à jour.",
            metadata={"type": "structure_updated", "chapters": chapters}
        )

    # =========================================================================
    # Writing handlers
    # =========================================================================

    async def _handle_write_chapter(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        chapter_id = meta.get("chapterId", "")
        user_instructions = message.content

        chapters = await self._get_chapters(context)
        chapter = self._find_chapter(chapters, chapter_id)
        if not chapter:
            return AgentResponse(content="Chapitre non trouvé.", metadata={"error": True})

        context.set_progress(10, f"Rédaction de : {chapter['title']}...")

        # Load relevant context
        docs = await self._get_documents_meta(context)
        analyses = await self._get_analyses(context)
        improvements = await self._get_improvements(context)

        # Get relevant document texts for this chapter's requirements
        relevant_texts = await self._gather_relevant_context(context, chapter, docs, analyses)

        improvements_text = ""
        related_improvements = [
            imp for imp in improvements
            if chapter_id in imp.get("linkedChapters", [])
        ]
        if related_improvements:
            improvements_text = "\nPOINTS D'AMÉLIORATION LIÉS À CE CHAPITRE :\n"
            for imp in related_improvements:
                improvements_text += f"- [{imp.get('priority', 'normal')}] {imp['title']}: {imp.get('description', '')}\n"

        context.set_progress(40, "Rédaction IA en cours...")

        write_prompt = f"""Rédige le chapitre suivant pour un MÉMOIRE TECHNIQUE officiel de réponse à appel d'offres.

CHAPITRE : {chapter['number']} - {chapter['title']}
DESCRIPTION : {chapter.get('description', '')}
POINTS CLÉS À COUVRIR : {json.dumps(chapter.get('key_points', []), ensure_ascii=False)}
EXIGENCES COUVERTES : {json.dumps(chapter.get('requirements_covered', []), ensure_ascii=False)}

INSTRUCTIONS DE L'UTILISATEUR :
{user_instructions if user_instructions else "Rédige ce chapitre de manière complète et professionnelle."}

CONTEXTE DOCUMENTAIRE :
{relevant_texts[:12000]}
{improvements_text}

CONTENU EXISTANT DU CHAPITRE :
{chapter.get('content', '[Aucun contenu existant]')}

═══ CONSIGNES IMPÉRATIVES DE RÉDACTION ═══

QUALITÉ ATTENDUE : Ce chapitre sera intégré tel quel dans un mémoire technique soumis à un acheteur public. Il doit être LIVRABLE CLÉ EN MAIN, pas une ébauche ni une prise de notes.

STYLE ET FORME :
1. RÉDIGE EN PARAGRAPHES DÉVELOPPÉS avec des phrases complètes et articulées.
   Chaque paragraphe doit contenir 3 à 6 phrases développant une idée.
   INTERDIT : les listes de puces sèches sans phrases, le style télégraphique, les notes brèves.
2. VOLUME MINIMUM : le chapitre doit faire au moins 400-800 mots. Développe, argumente, détaille.
3. STRUCTURE NARRATIVE : pour chaque sujet abordé, suis la logique :
   Contexte/enjeu → Notre approche → Mise en œuvre détaillée → Engagements concrets → Bénéfices client
4. LANGAGE PROFESSIONNEL SOUTENU : ton formel d'entreprise, vocabulaire précis du secteur,
   connecteurs logiques entre les idées (« En effet », « Par ailleurs », « À cet égard »...).
5. ENGAGEMENTS CHIFFRÉS : SLA, KPIs, délais, taux de disponibilité, pénalités.
   Pas de formulations vagues comme "nous assurons une bonne qualité".
6. ALTERNE prose développée et éléments visuels (tableaux de synthèse, listes structurées)
   pour rendre le contenu clair et lisible. Les tableaux complètent la prose, pas l'inverse.

CONTENU :
7. CAPITALISE sur le contenu de la réponse précédente s'il est fourni. Reprends les
   arguments et données factuelles pertinentes, puis enrichis-les.
8. VALORISE l'expérience du marché précédent : cite des résultats concrets obtenus,
   des chiffres de performance, des retours terrain.
9. RÉPONDS explicitement à chaque exigence listée dans les points clés à couvrir.
10. INTÈGRE les points d'amélioration identifiés ci-dessus.

FORMAT :
11. Ne commence PAS par un titre qui répète le nom du chapitre.
12. Utilise du markdown propre : ## pour les sous-sections, **gras** pour les termes clés,
    tableaux markdown pour les synthèses, listes numérotées pour les processus.
13. Ne génère JAMAIS de bloc JSON, de métadonnées ou de résumé structuré.
    Retourne UNIQUEMENT le contenu rédigé en markdown."""

        content = await self._llm_chat(
            context, prompt=write_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=8192,
        )

        # Update chapter content (auto-apply pseudonyms)
        pseudonyms = await self._get_pseudonyms(context)
        self._update_chapter_content(chapters, chapter_id, content, pseudonyms)
        await self._save_chapters(context, chapters)

        context.set_progress(100, "Rédaction terminée")

        return AgentResponse(
            content=content,
            metadata={
                "type": "chapter_written",
                "chapterId": chapter_id,
                "chapterTitle": chapter["title"],
            }
        )

    async def _handle_improve_chapter(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        chapter_id = meta.get("chapterId", "")
        user_instructions = message.content

        chapters = await self._get_chapters(context)
        chapter = self._find_chapter(chapters, chapter_id)
        if not chapter:
            return AgentResponse(content="Chapitre non trouvé.", metadata={"error": True})

        if not chapter.get("content"):
            return AgentResponse(content="Le chapitre n'a pas encore de contenu à améliorer.", metadata={"error": True})

        context.set_progress(30, "Amélioration en cours...")

        improve_prompt = f"""Améliore le contenu suivant du chapitre "{chapter['number']} - {chapter['title']}" pour un MÉMOIRE TECHNIQUE officiel.

CONTENU ACTUEL :
{chapter['content']}

DEMANDE DE L'UTILISATEUR :
{user_instructions}

═══ CONSIGNES D'AMÉLIORATION ═══

1. APPLIQUE la demande de l'utilisateur en priorité.
2. DÉVELOPPE les passages trop concis : transforme les listes sèches en paragraphes
   développés avec des phrases complètes et articulées (3-6 phrases par paragraphe minimum).
3. RENFORCE le niveau de langage : ton professionnel soutenu, connecteurs logiques,
   vocabulaire précis du secteur.
4. AJOUTE des engagements chiffrés concrets (SLA, KPIs, délais) là où c'est pertinent.
5. ASSURE que chaque section suit la structure : contexte → approche → mise en œuvre → engagements → bénéfices.
6. CONSERVE la structure globale sauf si elle peut être significativement améliorée.
7. Retourne le contenu COMPLET amélioré, pas juste les modifications.
8. CORRIGE tout problème de formatage markdown (mermaid mal encapsulé, tableaux cassés, etc.).
9. Ne génère JAMAIS de bloc JSON ou de métadonnées. Retourne UNIQUEMENT le contenu markdown."""

        improved = await self._llm_chat(
            context, prompt=improve_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=8192,
        )

        pseudonyms = await self._get_pseudonyms(context)
        self._update_chapter_content(chapters, chapter_id, improved, pseudonyms)
        await self._save_chapters(context, chapters)

        context.set_progress(100, "Chapitre amélioré")

        return AgentResponse(
            content=improved,
            metadata={
                "type": "chapter_improved",
                "chapterId": chapter_id,
                "chapterTitle": chapter["title"],
            }
        )

    # =========================================================================
    # Bulk writing / improving
    # =========================================================================

    async def _handle_write_all_chapters(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Write all chapters that don't have content yet."""
        chapters = await self._get_chapters(context)
        docs = await self._get_documents_meta(context)
        analyses = await self._get_analyses(context)
        improvements = await self._get_improvements(context)

        # Collect all unwritten chapters (top-level + sub-chapters)
        unwritten = []
        for ch in chapters:
            if not ch.get("content"):
                unwritten.append(ch)
            for sub in ch.get("sub_chapters", []):
                if not sub.get("content"):
                    unwritten.append(sub)

        if not unwritten:
            return AgentResponse(
                content="Tous les chapitres sont déjà rédigés.",
                metadata={"type": "write_all_complete"}
            )

        total = len(unwritten)
        pseudonyms = await self._get_pseudonyms(context)
        context.set_progress(5, f"Rédaction de {total} chapitre(s)...")

        for idx, chapter in enumerate(unwritten):
            pct = int(5 + (idx / total) * 90)
            context.set_progress(pct, f"Rédaction {idx+1}/{total} : {chapter['title']}...")

            relevant_texts = await self._gather_relevant_context(context, chapter, docs, analyses)

            improvements_text = ""
            related_improvements = [
                imp for imp in improvements
                if chapter["id"] in imp.get("linkedChapters", [])
            ]
            if related_improvements:
                improvements_text = "\nPOINTS D'AMÉLIORATION LIÉS À CE CHAPITRE :\n"
                for imp in related_improvements:
                    improvements_text += f"- [{imp.get('priority', 'normal')}] {imp['title']}: {imp.get('description', '')}\n"

            write_prompt = f"""Rédige le chapitre suivant pour un MÉMOIRE TECHNIQUE officiel de réponse à appel d'offres.

CHAPITRE : {chapter['number']} - {chapter['title']}
DESCRIPTION : {chapter.get('description', '')}
POINTS CLÉS À COUVRIR : {json.dumps(chapter.get('key_points', []), ensure_ascii=False)}
EXIGENCES COUVERTES : {json.dumps(chapter.get('requirements_covered', []), ensure_ascii=False)}

CONTEXTE DOCUMENTAIRE :
{relevant_texts[:12000]}
{improvements_text}

CONSIGNES IMPÉRATIVES :
1. RÉDIGE EN PARAGRAPHES DÉVELOPPÉS (3-6 phrases par paragraphe). INTERDIT : les listes sèches sans phrases, le style télégraphique.
2. VOLUME : minimum 400 mots. Développe, argumente, détaille chaque point.
3. LANGAGE PROFESSIONNEL SOUTENU : phrases complètes, connecteurs logiques, vocabulaire du secteur.
4. Pour chaque sujet : contexte → approche → mise en œuvre → engagements chiffrés → bénéfices client.
5. CAPITALISE sur le contexte documentaire et la réponse précédente.
6. INCLUS des engagements concrets : SLA, KPIs, délais, chiffres de performance.
7. Ne commence PAS par un titre répétant le nom du chapitre.
8. Ne génère JAMAIS de JSON ou métadonnées. UNIQUEMENT du markdown rédigé."""

            try:
                content = await self._llm_chat(
                    context, prompt=write_prompt,
                    system_prompt=system_prompt,
                    temperature=0.5, max_tokens=8192,
                )
                self._update_chapter_content(chapters, chapter["id"], content, pseudonyms)
            except Exception as e:
                logger.error(f"Failed to write chapter {chapter['title']}: {e}")

        await self._save_chapters(context, chapters)
        context.set_progress(100, "Rédaction complète terminée")

        written_count = sum(
            1 for ch in unwritten if ch.get("content")
        )

        return AgentResponse(
            content=f"{written_count}/{total} chapitres rédigés avec succès.",
            metadata={
                "type": "write_all_complete",
                "chapters": chapters,
                "writtenCount": written_count,
            }
        )

    async def _handle_improve_all_chapters(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Improve all chapters that already have content."""
        chapters = await self._get_chapters(context)
        docs = await self._get_documents_meta(context)
        analyses = await self._get_analyses(context)
        improvements = await self._get_improvements(context)

        # Collect all written chapters
        written = []
        for ch in chapters:
            if ch.get("content"):
                written.append(ch)
            for sub in ch.get("sub_chapters", []):
                if sub.get("content"):
                    written.append(sub)

        if not written:
            return AgentResponse(
                content="Aucun chapitre rédigé à améliorer.",
                metadata={"type": "improve_all_complete"}
            )

        total = len(written)
        pseudonyms = await self._get_pseudonyms(context)
        context.set_progress(5, f"Amélioration de {total} chapitre(s)...")

        for idx, chapter in enumerate(written):
            pct = int(5 + (idx / total) * 90)
            context.set_progress(pct, f"Amélioration {idx+1}/{total} : {chapter['title']}...")

            relevant_texts = await self._gather_relevant_context(context, chapter, docs, analyses)

            improvements_text = ""
            related_improvements = [
                imp for imp in improvements
                if chapter["id"] in imp.get("linkedChapters", [])
            ]
            if related_improvements:
                improvements_text = "\nPOINTS D'AMÉLIORATION À INTÉGRER :\n"
                for imp in related_improvements:
                    improvements_text += f"- [{imp.get('priority', 'normal')}] {imp['title']}: {imp.get('description', '')}\n"

            improve_prompt = f"""Améliore le chapitre suivant pour le rendre livrable dans un MÉMOIRE TECHNIQUE officiel.

CHAPITRE : {chapter['number']} - {chapter['title']}

CONTENU ACTUEL :
{chapter['content']}

CONTEXTE DOCUMENTAIRE :
{relevant_texts[:10000]}
{improvements_text}

CONSIGNES D'AMÉLIORATION IMPÉRATIVES :
1. DÉVELOPPE tous les passages trop concis : transforme les listes sèches en paragraphes
   développés de 3-6 phrases avec connecteurs logiques.
2. RENFORCE le langage professionnel : ton soutenu d'entreprise, argumentation structurée.
3. AJOUTE des engagements chiffrés (SLA, KPIs, délais, performances) partout où pertinent.
4. Pour chaque section, vérifie la structure : contexte → approche → mise en œuvre → engagements → bénéfices.
5. ENRICHIS avec les données du contexte documentaire et les points d'amélioration.
6. ASSURE que le volume est suffisant (min 400 mots par chapitre).
7. CORRIGE tout problème de formatage markdown (mermaid, tableaux, code fences parasites).
8. Retourne le contenu COMPLET amélioré (pas juste les modifications).
9. Ne commence PAS par un titre répétant le nom du chapitre.
10. Ne génère JAMAIS de JSON ou métadonnées. UNIQUEMENT du markdown rédigé."""

            try:
                improved = await self._llm_chat(
                    context, prompt=improve_prompt,
                    system_prompt=system_prompt,
                    temperature=0.5, max_tokens=8192,
                )
                self._update_chapter_content(chapters, chapter["id"], improved, pseudonyms)
            except Exception as e:
                logger.error(f"Failed to improve chapter {chapter['title']}: {e}")

        await self._save_chapters(context, chapters)
        context.set_progress(100, "Amélioration complète terminée")

        return AgentResponse(
            content=f"{total} chapitres améliorés avec succès.",
            metadata={
                "type": "improve_all_complete",
                "chapters": chapters,
                "improvedCount": total,
            }
        )

    def _find_chapter(self, chapters: list[dict], chapter_id: str) -> Optional[dict]:
        for ch in chapters:
            if ch["id"] == chapter_id:
                return ch
            for sub in ch.get("sub_chapters", []):
                if sub["id"] == chapter_id:
                    return sub
        return None

    def _update_chapter_content(self, chapters: list[dict], chapter_id: str, content: str, pseudonyms: list[dict] | None = None) -> None:
        cleaned = self._clean_chapter_content(content)
        # Auto-apply pseudonyms to new content
        if pseudonyms:
            for entry in pseudonyms:
                real = entry.get("real", "")
                placeholder = entry.get("placeholder", "")
                if real and placeholder and real in cleaned:
                    cleaned = cleaned.replace(real, placeholder)
        for ch in chapters:
            if ch["id"] == chapter_id:
                ch["content"] = cleaned
                ch["status"] = "written"
                ch["lastModified"] = datetime.now().isoformat()
                return
            for sub in ch.get("sub_chapters", []):
                if sub["id"] == chapter_id:
                    sub["content"] = cleaned
                    sub["status"] = "written"
                    sub["lastModified"] = datetime.now().isoformat()
                    return

    async def _gather_relevant_context(
        self, context: AgentContext, chapter: dict, docs: list[dict], analyses: dict
    ) -> str:
        parts = []
        chapter_title = chapter.get("title", "").lower()
        chapter_number = chapter.get("number", "")

        # Include analyses relevant to this chapter
        for key, analysis in analyses.items():
            if key.startswith("_"):
                continue
            parts.append(f"[Analyse: {analysis.get('fileName', '')}]\n{analysis.get('content', '')[:2000]}")
            if len(parts) >= 3:
                break

        # Include comparison if available
        comparison = analyses.get("_comparison", {}).get("content", "")
        if comparison:
            parts.append(f"[Comparaison AO]\n{comparison[:2000]}")

        # Include new AO requirements context
        for doc in docs:
            if doc["category"] == "nouvel_ao" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    text = raw.decode("utf-8")
                    parts.append(f"[Nouvel AO: {doc['fileName']}]\n{text[:4000]}")
                    break

        # Include previous response — try to find the matching section
        prev_texts = []
        for doc in docs:
            if doc["category"] == "ancienne_reponse" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    prev_texts.append((doc["fileName"], raw.decode("utf-8")))

        if prev_texts:
            # Try to extract the relevant section from the previous response
            for fname, full_text in prev_texts:
                relevant_section = self._extract_relevant_section(
                    full_text, chapter_title, chapter_number
                )
                if relevant_section:
                    parts.append(
                        f"[CONTENU RÉPONSE PRÉCÉDENTE - Section correspondante: {fname}]\n"
                        f"{relevant_section}"
                    )
                else:
                    # Fallback: give a large chunk of the full previous response
                    parts.append(
                        f"[CONTENU RÉPONSE PRÉCÉDENTE: {fname}]\n"
                        f"{full_text[:6000]}"
                    )

        return "\n\n".join(parts)

    def _extract_relevant_section(
        self, text: str, chapter_title: str, chapter_number: str
    ) -> str | None:
        """Extract the section from previous response that best matches the chapter."""
        lines = text.split("\n")
        title_lower = chapter_title.lower().strip()

        # Strategy 1: Find heading with matching title or number
        best_start = -1
        best_end = len(lines)
        best_score = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check if it's a heading (markdown or numbered)
            is_heading = (
                stripped.startswith("#")
                or re.match(r'^\d+(\.\d+)*\.?\s+', stripped)
                or re.match(r'^[IVXLC]+\.\s+', stripped)
            )
            if not is_heading:
                continue

            heading_text = re.sub(r'^#+\s*', '', stripped)
            heading_text = re.sub(r'^\d+(\.\d+)*\.?\s*', '', heading_text)
            heading_lower = heading_text.lower().strip()

            # Score matching
            score = 0
            if heading_lower == title_lower:
                score = 100
            elif title_lower in heading_lower or heading_lower in title_lower:
                score = 70
            else:
                # Word overlap
                title_words = set(title_lower.split())
                heading_words = set(heading_lower.split())
                common = title_words & heading_words
                if len(common) >= 2 or (len(common) >= 1 and len(title_words) <= 2):
                    score = 30 + 10 * len(common)

            # Also check number matching
            if chapter_number and re.match(rf'^{re.escape(chapter_number)}[\.\s]', stripped):
                score += 30

            if score > best_score:
                best_score = score
                best_start = i
                # Find end: next heading at same or higher level
                level = len(re.match(r'^(#+)', stripped).group(1)) if stripped.startswith("#") else 1
                for j in range(i + 1, len(lines)):
                    next_stripped = lines[j].strip()
                    if next_stripped.startswith("#"):
                        next_level = len(re.match(r'^(#+)', next_stripped).group(1))
                        if next_level <= level:
                            best_end = j
                            break
                    elif re.match(r'^\d+\.\s+[A-ZÀ-Ü]', next_stripped):
                        # Top-level numbered heading
                        best_end = j
                        break

        if best_start >= 0 and best_score >= 30:
            section = "\n".join(lines[best_start:best_end])
            # Return up to 8000 chars of the matching section
            return section[:8000]

        return None

    # =========================================================================
    # Compliance check
    # =========================================================================

    async def _handle_check_compliance(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        context.set_progress(10, "Chargement de la réponse en cours...")

        chapters = await self._get_chapters(context)
        docs = await self._get_documents_meta(context)
        analyses = await self._get_analyses(context)
        improvements = await self._get_improvements(context)

        if not chapters:
            return AgentResponse(
                content="Aucune structure de réponse définie. Générez d'abord la structure.",
                metadata={"error": True}
            )

        # Build full document content
        doc_content = []
        for ch in chapters:
            status = "rédigé" if ch.get("content") else "vide"
            doc_content.append(f"\n## {ch['number']} - {ch['title']} [{status}]")
            if ch.get("content"):
                doc_content.append(ch["content"][:2000])
            for sub in ch.get("sub_chapters", []):
                sub_status = "rédigé" if sub.get("content") else "vide"
                doc_content.append(f"\n### {sub['number']} - {sub['title']} [{sub_status}]")
                if sub.get("content"):
                    doc_content.append(sub["content"][:1500])

        # Load new AO texts for requirement verification
        new_ao_texts = []
        for doc in docs:
            if doc["category"] == "nouvel_ao" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    new_ao_texts.append(f"--- {doc['fileName']} ---\n{raw.decode('utf-8')[:5000]}")

        context.set_progress(40, "Vérification de conformité...")

        check_prompt = f"""Effectue une vérification de conformité complète de la réponse en cours de rédaction.

=== EXIGENCES DU NOUVEL AO ===
{chr(10).join(new_ao_texts) if new_ao_texts else "[Pas de documents AO chargés]"}

=== RÉPONSE EN COURS ===
{chr(10).join(doc_content)}

=== POINTS D'AMÉLIORATION ATTENDUS ===
{json.dumps([{"title": i["title"], "description": i.get("description", "")} for i in improvements], ensure_ascii=False) if improvements else "[Aucun]"}

Vérifie :
1. La couverture de toutes les exigences de l'AO
2. Le respect du cadre de réponse
3. La complétude de chaque section
4. La cohérence globale
5. Les sections manquantes ou incomplètes
6. La qualité rédactionnelle
7. L'intégration des points d'amélioration

IMPORTANT : Retourne un bloc JSON structuré (type compliance_check) avec le score global,
le statut par section et les actions prioritaires, EN PLUS de ton analyse textuelle."""

        check_result = await self._llm_chat(
            context, prompt=check_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=4096,
        )

        context.set_progress(100, "Vérification terminée")

        return AgentResponse(
            content=check_result,
            metadata={"type": "compliance_check"}
        )

    # =========================================================================
    # Improvements
    # =========================================================================

    async def _handle_add_improvement(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        improvement = {
            "id": f"imp-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": meta.get("title", message.content[:80]),
            "description": meta.get("description", message.content),
            "priority": meta.get("priority", "normal"),
            "source": meta.get("source", "manual"),
            "linkedChapters": meta.get("linkedChapters", []),
            "createdAt": datetime.now().isoformat(),
        }

        items = await self._get_improvements(context)
        items.append(improvement)
        await self._save_improvements(context, items)

        return AgentResponse(
            content=f"Point d'amélioration ajouté : **{improvement['title']}**",
            metadata={"type": "improvement_added", "improvement": improvement}
        )

    async def _handle_delete_improvement(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        imp_id = (message.metadata or {}).get("improvementId", "")
        items = await self._get_improvements(context)
        items = [i for i in items if i["id"] != imp_id]
        await self._save_improvements(context, items)

        return AgentResponse(
            content="Point d'amélioration supprimé.",
            metadata={"type": "improvement_deleted", "improvementId": imp_id}
        )

    # =========================================================================
    # Export
    # =========================================================================

    async def _handle_export_docx(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        context.set_progress(10, "Préparation de l'export...")

        chapters = await self._get_chapters(context)
        if not chapters:
            return AgentResponse(content="Aucune structure de réponse à exporter.", metadata={"error": True})

        meta = message.metadata or {}
        title = meta.get("title", "Réponse à l'Appel d'Offres")
        template_key = meta.get("templateKey")

        context.set_progress(30, "Génération du document Word...")

        # Load pseudonyms for depseudonymization in export
        pseudonyms = await self._get_pseudonyms(context)

        # Build paragraphs for word-crud
        paragraphs = [
            {"text": title, "style": "Title"},
            {"text": f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}", "style": "Normal"},
            {"text": "", "style": "Normal"},
        ]

        def _depr(text: str) -> str:
            """Depseudonymize text for export."""
            return self._depseudonymize(text, pseudonyms) if pseudonyms else text

        for ch in chapters:
            paragraphs.append({"text": f"{ch['number']}. {_depr(ch['title'])}", "style": "Heading 1"})

            if ch.get("description") and not ch.get("content"):
                paragraphs.append({"text": _depr(ch["description"]), "style": "Normal"})

            if ch.get("content"):
                for line in _depr(ch["content"]).split("\n"):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("### "):
                        paragraphs.append({"text": stripped[4:], "style": "Heading 3"})
                    elif stripped.startswith("## "):
                        paragraphs.append({"text": stripped[3:], "style": "Heading 2"})
                    elif stripped.startswith("# "):
                        paragraphs.append({"text": stripped[2:], "style": "Heading 1"})
                    elif stripped.startswith("- ") or stripped.startswith("* "):
                        paragraphs.append({"text": stripped[2:], "style": "List Bullet"})
                    else:
                        paragraphs.append({"text": stripped, "style": "Normal"})

            for sub in ch.get("sub_chapters", []):
                paragraphs.append({"text": f"{sub['number']}. {_depr(sub['title'])}", "style": "Heading 2"})

                if sub.get("description") and not sub.get("content"):
                    paragraphs.append({"text": _depr(sub["description"]), "style": "Normal"})

                if sub.get("content"):
                    for line in _depr(sub["content"]).split("\n"):
                        stripped = line.strip()
                        if not stripped:
                            continue
                        if stripped.startswith("### "):
                            paragraphs.append({"text": stripped[4:], "style": "Heading 3"})
                        elif stripped.startswith("## "):
                            paragraphs.append({"text": stripped[3:], "style": "Heading 2"})
                        elif stripped.startswith("- ") or stripped.startswith("* "):
                            paragraphs.append({"text": stripped[2:], "style": "List Bullet"})
                        else:
                            paragraphs.append({"text": stripped, "style": "Normal"})

        context.set_progress(70, "Création du fichier Word...")

        output_key = f"exports/reponse_ao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        create_params: dict[str, Any] = {
            "action": "create",
            "storage_key": output_key,
            "data": {
                "title": title,
                "paragraphs": paragraphs,
            },
            "options": {
                "font_name": "Calibri",
                "font_size": 11,
            },
        }

        if template_key:
            create_params["template_key"] = template_key

        result = await context.tools.execute("word-crud", create_params)

        if not result.success:
            return AgentResponse(
                content=f"Erreur lors de la génération du DOCX : {result.error}",
                metadata={"error": True}
            )

        context.set_progress(100, "Export terminé")

        return AgentResponse(
            content=f"Document Word généré avec succès : **{output_key}**",
            metadata={
                "type": "export_complete",
                "fileKey": output_key,
                "fileName": output_key.split("/")[-1],
            }
        )

    async def _handle_upload_template(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        file_key = meta.get("fileKey", "")
        file_name = meta.get("fileName", "template.docx")

        if not file_key:
            return AgentResponse(content="Aucun fichier template fourni.", metadata={"error": True})

        template_key = f"templates/{file_name}"
        raw = await context.storage.get(file_key)
        if raw:
            await context.storage.put(template_key, raw, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        return AgentResponse(
            content=f"Template **{file_name}** enregistré.",
            metadata={"type": "template_uploaded", "templateKey": template_key, "fileName": file_name}
        )

    # =========================================================================
    # State
    # =========================================================================

    async def _handle_get_state(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        docs = await self._get_documents_meta(context)
        chapters = await self._get_chapters(context)
        improvements = await self._get_improvements(context)
        analyses = await self._get_analyses(context)
        pseudonyms = await self._get_pseudonyms(context)

        state = {
            "documents": docs,
            "chapters": chapters,
            "improvements": improvements,
            "analyses": analyses,
            "pseudonyms": pseudonyms,
        }

        return AgentResponse(
            content=json.dumps(state, ensure_ascii=False),
            metadata={"type": "project_state", "state": state}
        )

    async def _handle_update_pseudonyms(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        meta = message.metadata or {}
        new_pseudonyms = meta.get("pseudonyms", [])
        old_pseudonyms = await self._get_pseudonyms(context)

        # Save new pseudonyms first
        await self._save_pseudonyms(context, new_pseudonyms)

        # Retroactive pseudonymization: apply to all existing chapter content
        # For entries that are new or changed, scan chapters and replace
        # real values with placeholders in stored content.
        chapters = await self._get_chapters(context)
        changed = False
        for entry in new_pseudonyms:
            real = entry.get("real", "")
            placeholder = entry.get("placeholder", "")
            if not real or not placeholder:
                continue
            for ch in chapters:
                if ch.get("content") and real in ch["content"]:
                    ch["content"] = ch["content"].replace(real, placeholder)
                    changed = True
                for sub in ch.get("sub_chapters", []):
                    if sub.get("content") and real in sub["content"]:
                        sub["content"] = sub["content"].replace(real, placeholder)
                        changed = True

        if changed:
            await self._save_chapters(context, chapters)
            logger.info("Retroactive pseudonymization applied to existing chapter content")

        return AgentResponse(
            content="Matrice de pseudonymisation mise à jour.",
            metadata={
                "type": "pseudonyms_updated",
                "pseudonyms": new_pseudonyms,
                "chapters": chapters if changed else None,
            }
        )

    async def _handle_apply_pseudonyms(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Force-apply all pseudonyms to every chapter content."""
        pseudonyms = await self._get_pseudonyms(context)
        if not pseudonyms:
            return AgentResponse(
                content="Aucune règle de pseudonymisation définie.",
                metadata={"type": "pseudonyms_applied", "replacements": 0}
            )

        chapters = await self._get_chapters(context)
        total_replacements = 0

        for entry in pseudonyms:
            real = entry.get("real", "")
            placeholder = entry.get("placeholder", "")
            if not real or not placeholder:
                continue
            # Case-insensitive replacement
            pattern = re.compile(re.escape(real), re.IGNORECASE)
            for ch in chapters:
                if ch.get("content") and pattern.search(ch["content"]):
                    ch["content"] = pattern.sub(placeholder, ch["content"])
                    total_replacements += 1
                for sub in ch.get("sub_chapters", []):
                    if sub.get("content") and pattern.search(sub["content"]):
                        sub["content"] = pattern.sub(placeholder, sub["content"])
                        total_replacements += 1

        if total_replacements > 0:
            await self._save_chapters(context, chapters)

        return AgentResponse(
            content=f"Pseudonymisation appliquée : {total_replacements} remplacement(s) effectué(s).",
            metadata={
                "type": "pseudonyms_applied",
                "replacements": total_replacements,
                "chapters": chapters,
            }
        )

    # =========================================================================
    # Full formatting cleanup pass
    # =========================================================================

    async def _handle_cleanup_formatting(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Run a full formatting cleanup pass on all written chapters."""
        chapters = await self._get_chapters(context)
        pseudonyms = await self._get_pseudonyms(context)

        written = []
        for ch in chapters:
            if ch.get("content"):
                written.append(ch)
            for sub in ch.get("sub_chapters", []):
                if sub.get("content"):
                    written.append(sub)

        if not written:
            return AgentResponse(
                content="Aucun chapitre rédigé à nettoyer.",
                metadata={"type": "formatting_cleaned", "chapters": chapters}
            )

        total = len(written)
        context.set_progress(5, f"Nettoyage de {total} chapitre(s)...")

        for idx, chapter in enumerate(written):
            pct = int(5 + (idx / total) * 90)
            context.set_progress(pct, f"Nettoyage {idx+1}/{total} : {chapter['title']}...")

            cleanup_prompt = f"""Tu es un expert en mise en page markdown pour mémoires techniques.
Nettoie et corrige le formatage du contenu suivant. Retourne le contenu COMPLET corrigé.

CONTENU À NETTOYER :
{chapter['content']}

CORRECTIONS À APPLIQUER :
1. MERMAID : Si tu trouves des blocs « graph TD », « graph LR », « flowchart », « sequenceDiagram »
   qui ne sont pas dans des code fences ```mermaid ... ```, encapsule-les correctement.
   Si un diagramme mermaid est mal formé ou invalide, supprime-le et remplace par un texte descriptif.
2. CODE FENCES : Supprime les code fences ```markdown ou ```json parasites qui enveloppent du contenu normal.
3. TABLEAUX : Vérifie que chaque tableau markdown a une ligne de séparation |---|---| et
   que les colonnes sont cohérentes. Corrige les tableaux cassés.
4. TITRES : Assure une ligne vide avant chaque # heading.
5. JSON PARASITES : Supprime tout bloc JSON structuré (type chapter_content, métadonnées).
6. LISTES : Assure une ligne vide avant chaque liste.
7. NE MODIFIE PAS le texte en lui-même, seulement le formatage markdown.
8. Ne génère JAMAIS de JSON. Retourne UNIQUEMENT le contenu markdown nettoyé."""

            try:
                cleaned = await self._llm_chat(
                    context, prompt=cleanup_prompt,
                    system_prompt="Tu es un expert en formatage markdown. Corrige le formatage sans modifier le contenu.",
                    temperature=0.1, max_tokens=4096,
                )
                self._update_chapter_content(chapters, chapter["id"], cleaned, pseudonyms)
            except Exception as e:
                logger.error(f"Failed to cleanup chapter {chapter['title']}: {e}")

        await self._save_chapters(context, chapters)
        context.set_progress(100, "Mise en page terminée")

        return AgentResponse(
            content=f"Mise en page terminée : {total} chapitres nettoyés.",
            metadata={
                "type": "formatting_cleaned",
                "chapters": chapters,
                "cleanedCount": total,
            }
        )

    # =========================================================================
    # Auto-detect confidential entities
    # =========================================================================

    async def _handle_detect_confidential(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Scan all analyzed documents and detect confidential entities using LLM."""
        context.set_progress(10, "Collecte des textes analysés...")

        docs = await self._get_documents_meta(context)
        existing_pseudonyms = await self._get_pseudonyms(context)

        # Collect text from all analyzed documents
        all_texts: list[str] = []
        for doc in docs:
            text_key = doc.get("textKey")
            if not text_key:
                continue
            try:
                raw = await context.storage.get(text_key)
                if raw:
                    text = raw.decode("utf-8")
                    # Limit per-document text to avoid huge prompts
                    all_texts.append(f"--- Document: {doc.get('fileName', '?')} ---\n{text[:8000]}")
            except Exception:
                pass

        if not all_texts:
            return AgentResponse(
                content="Aucun document analysé disponible pour la détection.",
                metadata={"type": "confidential_detected", "detected": []}
            )

        context.set_progress(30, "Analyse des données confidentielles par l'IA...")

        # Build the prompt for LLM entity detection
        combined = "\n\n".join(all_texts)
        # Limit total size
        if len(combined) > 30000:
            combined = combined[:30000]

        # List already-known real values to help LLM avoid duplicates
        known_reals = [e.get("real", "") for e in existing_pseudonyms if e.get("real")]

        detection_prompt = f"""Analyse les documents suivants et identifie TOUTES les données confidentielles qui devraient être pseudonymisées.

Catégories à détecter (sois EXHAUSTIF) :
- **company** : noms de sociétés, entreprises, organisations, groupements, filiales, marques, sous-traitants
- **person** : noms de personnes (prénom + nom ou nom seul), contacts, signataires, responsables
- **project** : noms de projets, programmes, noms de marchés, intitulés d'appels d'offres
- **client** : noms de clients, donneurs d'ordre, maîtres d'ouvrage, acheteurs publics, centrales d'achat (ex: UGAP, RESAH, CAIH, etc.)
- **reference** : codes d'appel d'offres, numéros de marché, références AO (ex: 19U045, 2024-AO-123), numéros BOAMP, numéros de lot
- **location** : adresses précises, noms de sites spécifiques, bâtiments
- **financial** : montants financiers spécifiques, prix unitaires, chiffres d'affaires précis
- **other** : numéros de contrat, numéros SIRET/SIREN, numéros de téléphone, emails, dates spécifiques de contrats

{f"Entités déjà connues (NE PAS les inclure dans les résultats) : {', '.join(known_reals)}" if known_reals else ""}

IMPORTANT :
- SOIS EXHAUSTIF : détecte TOUTES les entités, même les petites références comme les codes AO
- Inclus les acronymes et noms courts de clients ou organisations
- Les codes alphanumériques de type référence AO (ex: 19U045) DOIVENT être détectés
- Les noms de centrales d'achat et organismes publics DOIVENT être détectés
- Ignore les termes purement génériques (ex: "appel d'offres", "marché public")
- Pour chaque entité, propose un pseudonyme adapté :
  - Sociétés: [Société 1], [Société 2]...
  - Personnes: [Personne 1], [Personne 2]...
  - Clients: [Client 1], [Client 2]...
  - Références: [Réf. AO 1], [Réf. AO 2]...
  - Financier: [Montant 1], [Montant 2]...

Réponds UNIQUEMENT avec un JSON valide, sous la forme d'un tableau :
```json
[
  {{"placeholder": "[Société 1]", "real": "NomDeLaSociété", "category": "company"}},
  {{"placeholder": "[Client 1]", "real": "UGAP", "category": "client"}},
  {{"placeholder": "[Réf. AO 1]", "real": "19U045", "category": "reference"}}
]
```

Si aucune entité confidentielle n'est trouvée, réponds avec un tableau vide : []

Documents à analyser :
{combined}"""

        try:
            result = await context.llm.chat(
                prompt=detection_prompt,
                system_prompt="Tu es un expert en protection des données confidentielles. Tu identifies les entités sensibles dans les documents d'appels d'offres.",
                temperature=0.1,
                max_tokens=4096,
            )

            context.set_progress(70, "Traitement des résultats...")

            # Extract JSON from response
            detected = self._extract_json_array(result)

            if not detected:
                return AgentResponse(
                    content="Aucune entité confidentielle détectée dans les documents.",
                    metadata={"type": "confidential_detected", "detected": []}
                )

            # Filter out entities whose real value already exists in pseudonyms
            existing_reals_lower = {e.get("real", "").lower() for e in existing_pseudonyms}
            existing_placeholders = {e.get("placeholder", "") for e in existing_pseudonyms}

            new_entries = []
            for item in detected:
                real = item.get("real", "").strip()
                placeholder = item.get("placeholder", "").strip()
                category = item.get("category", "other").strip()
                if not real or not placeholder:
                    continue
                if real.lower() in existing_reals_lower:
                    continue
                if placeholder in existing_placeholders:
                    continue
                # Ensure placeholder is wrapped in brackets
                if not placeholder.startswith("["):
                    placeholder = f"[{placeholder}]"
                new_entries.append({
                    "id": f"ps-auto-{len(existing_pseudonyms) + len(new_entries) + 1}-{datetime.now().strftime('%H%M%S')}",
                    "placeholder": placeholder,
                    "real": real,
                    "category": category if category in ("company", "person", "project", "client", "location", "reference", "financial", "other") else "other",
                })

            context.set_progress(90, "Mise à jour de la liste...")

            # Merge with existing pseudonyms
            merged = existing_pseudonyms + new_entries
            await self._save_pseudonyms(context, merged)

            return AgentResponse(
                content=f"{len(new_entries)} entité(s) confidentielle(s) détectée(s) et ajoutée(s) automatiquement.",
                metadata={
                    "type": "confidential_detected",
                    "detected": new_entries,
                    "pseudonyms": merged,
                }
            )

        except Exception as e:
            logger.error(f"Error detecting confidential entities: {e}")
            return AgentResponse(
                content=f"Erreur lors de la détection : {str(e)}",
                metadata={"type": "error", "error": str(e)}
            )

    def _extract_json_array(self, text: str) -> list[dict]:
        """Extract a JSON array from LLM response text."""
        # Try fenced code block first
        match = re.search(r"```(?:json)?\s*\n(\[.*?\])\s*\n```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try raw JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return []

    # =========================================================================
    # Workspace export / import
    # =========================================================================

    async def _handle_export_workspace(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Export full workspace as a ZIP archive stored in MinIO."""
        context.set_progress(10, "Collecte des données...")

        docs = await self._get_documents_meta(context)
        chapters = await self._get_chapters(context)
        improvements = await self._get_improvements(context)
        analyses = await self._get_analyses(context)
        pseudonyms = await self._get_pseudonyms(context)

        # Build the manifest
        manifest = {
            "version": "1.0",
            "exportedAt": datetime.now().isoformat(),
            "documents": docs,
            "chapters": chapters,
            "improvements": improvements,
            "analyses": analyses,
            "pseudonyms": pseudonyms,
        }

        context.set_progress(30, "Création de l'archive ZIP...")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2)
            )

            # Include all document files (original + parsed text + images)
            total_files = 0
            for doc in docs:
                # Original uploaded file
                if doc.get("fileKey"):
                    try:
                        raw = await context.storage.get(doc["fileKey"])
                        if raw:
                            zf.writestr(f"files/{doc['fileKey']}", raw)
                            total_files += 1
                    except Exception as e:
                        logger.warning(f"Could not export file {doc['fileKey']}: {e}")

                # Parsed text
                if doc.get("textKey"):
                    try:
                        raw = await context.storage.get(doc["textKey"])
                        if raw:
                            zf.writestr(f"files/{doc['textKey']}", raw)
                            total_files += 1
                    except Exception as e:
                        logger.warning(f"Could not export text {doc['textKey']}: {e}")

                # Images
                for img in doc.get("images", []):
                    try:
                        raw = await context.storage.get(img["key"])
                        if raw:
                            zf.writestr(f"files/{img['key']}", raw)
                            total_files += 1
                    except Exception as e:
                        logger.warning(f"Could not export image {img['key']}: {e}")

            context.set_progress(70, f"Archive en cours ({total_files} fichiers)...")

        context.set_progress(90, "Enregistrement de l'archive...")

        archive_data = buf.getvalue()
        archive_key = f"exports/workspace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        await context.storage.put(archive_key, archive_data, "application/zip")

        context.set_progress(100, "Export terminé")

        return AgentResponse(
            content=f"Espace de travail exporté avec succès ({len(archive_data) // 1024} Ko, {total_files} fichiers).",
            metadata={
                "type": "workspace_exported",
                "fileKey": archive_key,
                "fileName": archive_key.split("/")[-1],
                "size": len(archive_data),
            }
        )

    async def _handle_import_workspace(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Import workspace from a previously exported ZIP archive."""
        meta = message.metadata or {}
        file_key = meta.get("fileKey", "")

        if not file_key:
            return AgentResponse(content="Aucun fichier d'import fourni.", metadata={"error": True})

        context.set_progress(10, "Lecture de l'archive...")

        raw = await context.storage.get(file_key)
        if not raw:
            return AgentResponse(content="Fichier d'archive introuvable.", metadata={"error": True})

        try:
            buf = io.BytesIO(raw)
            with zipfile.ZipFile(buf, "r") as zf:
                # Read manifest
                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data.decode("utf-8"))

                context.set_progress(30, "Restauration des fichiers...")

                # Restore all files
                restored_files = 0
                for name in zf.namelist():
                    if name == "manifest.json":
                        continue
                    if name.startswith("files/"):
                        storage_key = name[len("files/"):]
                        data = zf.read(name)
                        # Guess content type
                        ext = storage_key.rsplit(".", 1)[-1].lower() if "." in storage_key else ""
                        ct_map = {
                            "pdf": "application/pdf",
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "doc": "application/msword",
                            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "txt": "text/plain",
                            "json": "application/json",
                            "png": "image/png",
                            "jpg": "image/jpeg",
                            "jpeg": "image/jpeg",
                            "gif": "image/gif",
                            "svg": "image/svg+xml",
                            "csv": "text/csv",
                        }
                        ct = ct_map.get(ext, "application/octet-stream")
                        await context.storage.put(storage_key, data, ct)
                        restored_files += 1

                context.set_progress(70, "Restauration des données...")

                # Restore state
                if "documents" in manifest:
                    await self._save_documents_meta(context, manifest["documents"])
                if "chapters" in manifest:
                    await self._save_chapters(context, manifest["chapters"])
                if "improvements" in manifest:
                    await self._save_improvements(context, manifest["improvements"])
                if "analyses" in manifest:
                    await self._save_analyses(context, manifest["analyses"])
                if "pseudonyms" in manifest:
                    await self._save_pseudonyms(context, manifest["pseudonyms"])

            context.set_progress(100, "Import terminé")

            # Return full state so frontend can refresh
            state = {
                "documents": manifest.get("documents", []),
                "chapters": manifest.get("chapters", []),
                "improvements": manifest.get("improvements", []),
                "analyses": manifest.get("analyses", {}),
                "pseudonyms": manifest.get("pseudonyms", []),
            }

            return AgentResponse(
                content=f"Espace de travail importé avec succès ({restored_files} fichiers restaurés).",
                metadata={
                    "type": "workspace_imported",
                    "state": state,
                    "restoredFiles": restored_files,
                }
            )
        except zipfile.BadZipFile:
            return AgentResponse(
                content="Le fichier n'est pas une archive ZIP valide.",
                metadata={"error": True}
            )
        except Exception as e:
            logger.error(f"Workspace import failed: {e}", exc_info=True)
            return AgentResponse(
                content=f"Erreur lors de l'import : {str(e)}",
                metadata={"error": True}
            )

    # =========================================================================
    # Chat (default)
    # =========================================================================

    async def _handle_chat(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        history = await context.memory.get_history(limit=20) if context.memory else []

        # Build conversation with project context
        chapters = await self._get_chapters(context)
        docs = await self._get_documents_meta(context)

        project_context = f"""
ÉTAT DU PROJET :
- {len(docs)} documents chargés
- {len(chapters)} chapitres dans la structure
- Catégories de documents : {', '.join(set(d['category'] for d in docs)) if docs else 'aucune'}
"""

        conversation_parts = [project_context]
        for msg in history[-10:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            conversation_parts.append(f"[{role}]: {content[:500]}")

        conversation_parts.append(f"[user]: {message.content}")
        full_prompt = "\n\n".join(conversation_parts)

        response = await self._llm_chat(
            context, prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=2048,
        )

        return AgentResponse(
            content=response,
            metadata={"type": "chat_response"}
        )

    # =========================================================================
    # Streaming helper
    # =========================================================================

    async def _stream_handler(
        self, message: UserMessage, context: AgentContext, system_prompt: str, action: str
    ) -> AsyncIterator[AgentResponseChunk]:
        meta = message.metadata or {}

        if action in ("write_chapter", "improve_chapter"):
            chapter_id = meta.get("chapterId", "")
            chapters = await self._get_chapters(context)
            chapter = self._find_chapter(chapters, chapter_id)

            if not chapter:
                yield AgentResponseChunk(content="Chapitre non trouvé.")
                yield AgentResponseChunk(content="", is_final=True, metadata={"error": True})
                return

            if action == "write_chapter":
                relevant_texts = await self._gather_relevant_context(
                    context, chapter, await self._get_documents_meta(context), await self._get_analyses(context)
                )
                prompt = f"""Rédige le chapitre {chapter['number']} - {chapter['title']} pour un MÉMOIRE TECHNIQUE officiel.
Description : {chapter.get('description', '')}
Points clés : {json.dumps(chapter.get('key_points', []), ensure_ascii=False)}
Instructions : {message.content if message.content else 'Rédige de manière complète et professionnelle.'}

Contexte documentaire :
{relevant_texts[:10000]}

{f"Contenu existant du chapitre : {chapter.get('content', '')[:2000]}" if chapter.get('content') else ''}

CONSIGNES IMPÉRATIVES :
- RÉDIGE EN PARAGRAPHES DÉVELOPPÉS (3-6 phrases chacun). INTERDIT : listes sèches, style télégraphique.
- VOLUME : minimum 400 mots. Développe, argumente, détaille.
- LANGAGE PROFESSIONNEL SOUTENU avec connecteurs logiques.
- Inclus des ENGAGEMENTS CHIFFRÉS (SLA, KPIs, délais).
- Capitalise sur le contenu précédent s'il est fourni.
- Ne commence PAS par un titre répétant le nom du chapitre.
- Ne génère JAMAIS de JSON ou métadonnées. UNIQUEMENT du markdown rédigé."""
            else:
                prompt = f"""Améliore le chapitre {chapter['number']} - {chapter['title']} pour un MÉMOIRE TECHNIQUE officiel.
Contenu actuel : {chapter.get('content', '')}
Demande : {message.content}

CONSIGNES : Développe les passages concis en paragraphes de 3-6 phrases. Renforce le langage professionnel.
Ajoute des engagements chiffrés. Corrige le formatage markdown. Retourne le contenu COMPLET amélioré.
Ne génère JAMAIS de JSON ou métadonnées. UNIQUEMENT du markdown rédigé."""

            # Apply pseudonymization before streaming
            pseudonyms = await self._get_pseudonyms(context)
            if pseudonyms:
                prompt = self._pseudonymize(prompt, pseudonyms)
                system_prompt = self._pseudonymize(system_prompt, pseudonyms)

            collected = []
            async for token in context.llm.stream(
                prompt=prompt, system_prompt=system_prompt, temperature=0.5, max_tokens=8192
            ):
                collected.append(token)
                yield AgentResponseChunk(content=token)

            full_content = "".join(collected)
            self._update_chapter_content(chapters, chapter_id, full_content, pseudonyms)
            await self._save_chapters(context, chapters)

            yield AgentResponseChunk(
                content="", is_final=True,
                metadata={"type": f"chapter_{'written' if action == 'write_chapter' else 'improved'}", "chapterId": chapter_id}
            )
        else:
            # General chat streaming
            history = await context.memory.get_history(limit=10) if context.memory else []
            parts = []
            for msg in history[-10:]:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", str(msg))
                parts.append(f"[{role}]: {content[:500]}")
            parts.append(f"[user]: {message.content}")

            chat_prompt = "\n\n".join(parts)
            pseudonyms = await self._get_pseudonyms(context)
            if pseudonyms:
                chat_prompt = self._pseudonymize(chat_prompt, pseudonyms)
                system_prompt = self._pseudonymize(system_prompt, pseudonyms)

            async for token in context.llm.stream(
                prompt=chat_prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=2048
            ):
                yield AgentResponseChunk(content=token)

            yield AgentResponseChunk(content="", is_final=True, metadata={"type": "chat_response"})
