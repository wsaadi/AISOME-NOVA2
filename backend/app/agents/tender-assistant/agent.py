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

import json
import logging
import re
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
            "improve_chapter": self._handle_improve_chapter,
            "check_compliance": self._handle_check_compliance,
            "add_improvement": self._handle_add_improvement,
            "delete_improvement": self._handle_delete_improvement,
            "export_docx": self._handle_export_docx,
            "upload_template": self._handle_upload_template,
            "get_project_state": self._handle_get_state,
            "update_pseudonyms": self._handle_update_pseudonyms,
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

        write_prompt = f"""Rédige le chapitre suivant de la réponse à l'appel d'offres.

CHAPITRE : {chapter['number']} - {chapter['title']}
DESCRIPTION : {chapter.get('description', '')}
POINTS CLÉS À COUVRIR : {json.dumps(chapter.get('key_points', []), ensure_ascii=False)}
EXIGENCES COUVERTES : {json.dumps(chapter.get('requirements_covered', []), ensure_ascii=False)}

INSTRUCTIONS DE L'UTILISATEUR :
{user_instructions if user_instructions else "Rédige ce chapitre de manière complète et professionnelle."}

CONTEXTE DOCUMENTAIRE :
{relevant_texts[:8000]}
{improvements_text}

CONTENU EXISTANT DU CHAPITRE :
{chapter.get('content', '[Aucun contenu existant]')}

Rédige un contenu professionnel, structuré et complet pour ce chapitre.
Utilise du markdown pour la mise en forme (titres, listes, tableaux, etc.).
Sois concret, factuel et orienté solution."""

        content = await self._llm_chat(
            context, prompt=write_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4096,
        )

        # Update chapter content
        self._update_chapter_content(chapters, chapter_id, content)
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

        improve_prompt = f"""Améliore le contenu suivant du chapitre "{chapter['number']} - {chapter['title']}".

CONTENU ACTUEL :
{chapter['content']}

DEMANDE DE L'UTILISATEUR :
{user_instructions}

Améliore le contenu en tenant compte de la demande. Conserve la structure existante
sauf si l'utilisateur demande explicitement de la modifier. Retourne le contenu complet
amélioré (pas juste les modifications)."""

        improved = await self._llm_chat(
            context, prompt=improve_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4096,
        )

        self._update_chapter_content(chapters, chapter_id, improved)
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

    def _find_chapter(self, chapters: list[dict], chapter_id: str) -> Optional[dict]:
        for ch in chapters:
            if ch["id"] == chapter_id:
                return ch
            for sub in ch.get("sub_chapters", []):
                if sub["id"] == chapter_id:
                    return sub
        return None

    def _update_chapter_content(self, chapters: list[dict], chapter_id: str, content: str) -> None:
        for ch in chapters:
            if ch["id"] == chapter_id:
                ch["content"] = content
                ch["status"] = "written"
                ch["lastModified"] = datetime.now().isoformat()
                return
            for sub in ch.get("sub_chapters", []):
                if sub["id"] == chapter_id:
                    sub["content"] = content
                    sub["status"] = "written"
                    sub["lastModified"] = datetime.now().isoformat()
                    return

    async def _gather_relevant_context(
        self, context: AgentContext, chapter: dict, docs: list[dict], analyses: dict
    ) -> str:
        parts = []

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

        # Include previous response excerpts
        for doc in docs:
            if doc["category"] == "ancienne_reponse" and doc.get("textKey"):
                raw = await context.storage.get(doc["textKey"])
                if raw:
                    parts.append(f"[Réponse précédente: {doc['fileName']}]\n{raw.decode('utf-8')[:3000]}")
                    break

        return "\n\n".join(parts)

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
        pseudonyms = meta.get("pseudonyms", [])
        await self._save_pseudonyms(context, pseudonyms)
        return AgentResponse(
            content="Matrice de pseudonymisation mise à jour.",
            metadata={"type": "pseudonyms_updated", "pseudonyms": pseudonyms}
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
                prompt = f"""Rédige le chapitre {chapter['number']} - {chapter['title']}.
Description : {chapter.get('description', '')}
Points clés : {json.dumps(chapter.get('key_points', []), ensure_ascii=False)}
Instructions : {message.content if message.content else 'Rédige de manière complète et professionnelle.'}
Contexte : {relevant_texts[:6000]}
{f"Contenu existant : {chapter.get('content', '')[:2000]}" if chapter.get('content') else ''}"""
            else:
                prompt = f"""Améliore le chapitre {chapter['number']} - {chapter['title']}.
Contenu actuel : {chapter.get('content', '')}
Demande : {message.content}"""

            # Apply pseudonymization before streaming
            pseudonyms = await self._get_pseudonyms(context)
            if pseudonyms:
                prompt = self._pseudonymize(prompt, pseudonyms)
                system_prompt = self._pseudonymize(system_prompt, pseudonyms)

            collected = []
            async for token in context.llm.stream(
                prompt=prompt, system_prompt=system_prompt, temperature=0.5, max_tokens=4096
            ):
                collected.append(token)
                yield AgentResponseChunk(content=token)

            full_content = "".join(collected)
            self._update_chapter_content(chapters, chapter_id, full_content)
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
