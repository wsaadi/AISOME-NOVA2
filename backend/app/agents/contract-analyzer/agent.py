"""
Contract Analyzer Agent - Analyse juridique de contrats commerciaux.

Fonctionnalites:
    - Analyse de contrats PDF/DOCX uploades
    - Identification des risques par categorie
    - Reponses aux questions specifiques sur le contrat
    - Export Word du rapport d'analyse
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator
from datetime import datetime

from app.framework.base import BaseAgent
from app.framework.schemas import (
    AgentManifest,
    AgentResponse,
    AgentResponseChunk,
    UserMessage,
)

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext


class ContractAnalyzerAgent(BaseAgent):
    """Agent specialise dans l'analyse juridique de contrats commerciaux."""

    @property
    def manifest(self) -> AgentManifest:
        """Load agent manifest from manifest.json."""
        with open(Path(__file__).parent / "manifest.json") as f:
            return AgentManifest(**json.load(f))

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """Process contract analysis requests and questions."""
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")

        if message.metadata and message.metadata.get("fileKey"):
            return await self._analyze_contract(message, context, system_prompt)

        return await self._answer_question(message, context, system_prompt)

    async def _analyze_contract(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Analyze uploaded contract document."""
        file_key = message.metadata["fileKey"]
        file_name = message.metadata.get("fileName", "contract")

        context.set_progress(10, "Lecture du contrat...")

        # Extract text from document
        text_result = await context.tools.execute(
            "file-text-reader",
            {"file_key": file_key}
        )

        if not text_result.success:
            return AgentResponse(
                content=f"Erreur lors de la lecture du document : {text_result.error}"
            )

        contract_text = text_result.data.get("text", "")

        context.set_progress(30, "Analyse en cours...")

        settings = message.metadata.get("settings", {})
        analysis_mode = settings.get("analysisMode", "contract_only")

        analysis_prompt = f"""
Analyse le contrat suivant : {file_name}

CONTRAT :
{contract_text}

MODE D'ANALYSE : {analysis_mode}
- contract_only : Analyse uniquement basee sur le contenu du contrat
- best_practices : Inclure les recommandations basees sur les bonnes pratiques du secteur IT
- comparison : Comparer avec des clauses standards

Fournis une analyse complete structuree avec :
1. Une synthese globale
2. Les risques identifies par categorie
3. Un tableau de synthese des risques avec niveaux
4. Les recommandations prioritaires
"""

        history = await context.memory.get_history(limit=10) if context.memory else []

        context.set_progress(50, "Generation de l'analyse...")

        analysis = await context.llm.chat(
            prompt=analysis_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        context.set_progress(80, "Preparation du rapport...")

        # Store contract text in memory for future questions
        await context.storage.put(
            f"contracts/{file_key}_text.txt",
            contract_text.encode("utf-8"),
            "text/plain"
        )

        word_result = await self._generate_word_report(
            context, file_name, analysis, contract_text[:500]
        )

        context.set_progress(100, "Analyse terminee")

        return AgentResponse(
            content=analysis,
            metadata={
                "type": "contract_analysis",
                "fileName": file_name,
                "contractKey": file_key,
                "wordReportKey": word_result.get("key") if word_result else None,
                "analysisDate": datetime.now().isoformat(),
            }
        )

    async def _answer_question(
        self, message: UserMessage, context: AgentContext, system_prompt: str
    ) -> AgentResponse:
        """Answer specific questions about analyzed contract."""
        history = await context.memory.get_history(limit=20) if context.memory else []

        contract_key = None
        contract_text = None

        for msg in reversed(history):
            if hasattr(msg, "metadata") and msg.metadata.get("type") == "contract_analysis":
                contract_key = msg.metadata.get("contractKey")
                break

        if contract_key:
            try:
                contract_bytes = await context.storage.get(f"contracts/{contract_key}_text.txt")
                if contract_bytes:
                    contract_text = contract_bytes.decode("utf-8")
            except Exception:
                pass

        conversation_parts = []
        for msg in history[-10:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            conversation_parts.append(f"[{role}]: {content}")

        if contract_text:
            conversation_parts.append(f"\n[Contexte - Contrat analyse]:\n{contract_text[:2000]}...\n")

        conversation_parts.append(f"[user]: {message.content}")
        full_prompt = "\n\n".join(conversation_parts)

        context.set_progress(50, "Analyse de votre question...")

        settings = message.metadata.get("settings", {}) if message.metadata else {}
        analysis_mode = settings.get("analysisMode", "contract_only")

        enhanced_system_prompt = system_prompt + f"\nMODE D'ANALYSE ACTUEL : {analysis_mode}"

        response = await context.llm.chat(
            prompt=full_prompt,
            system_prompt=enhanced_system_prompt,
            temperature=0.5,
            max_tokens=2048,
        )

        context.set_progress(100, "Reponse prete")

        return AgentResponse(
            content=response,
            metadata={"type": "question_answer"}
        )

    async def _generate_word_report(
        self, context: AgentContext, file_name: str, analysis: str, contract_excerpt: str
    ) -> dict:
        """Generate Word document with analysis report."""
        try:
            doc_content = {
                "title": f"Analyse Juridique - {file_name}",
                "sections": [
                    {
                        "title": "Informations du Document",
                        "content": (
                            f"Document analyse : {file_name}\n"
                            f"Date d'analyse : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                            f"Extrait du contrat :\n{contract_excerpt}..."
                        )
                    },
                    {
                        "title": "Analyse Complete",
                        "content": analysis
                    }
                ],
                "format": {
                    "font": "Calibri",
                    "title_size": 16,
                    "heading_size": 14,
                    "body_size": 11,
                    "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
                }
            }

            result = await context.tools.execute(
                "document-generator",
                {
                    "format": "docx",
                    "content": doc_content,
                    "output_key": f"reports/analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                }
            )

            if result.success:
                return {"success": True, "key": result.data.get("file_key")}
            else:
                return {"success": False, "error": result.error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """Streaming version for real-time responses."""
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")

        if message.metadata and message.metadata.get("fileKey"):
            response = await self._analyze_contract(message, context, system_prompt)
            yield AgentResponseChunk(content=response.content, metadata=response.metadata)
            yield AgentResponseChunk(content="", is_final=True)
            return

        history = await context.memory.get_history(limit=20) if context.memory else []

        contract_key = None
        contract_text = None

        for msg in reversed(history):
            if hasattr(msg, "metadata") and msg.metadata.get("type") == "contract_analysis":
                contract_key = msg.metadata.get("contractKey")
                break

        if contract_key:
            try:
                contract_bytes = await context.storage.get(f"contracts/{contract_key}_text.txt")
                if contract_bytes:
                    contract_text = contract_bytes.decode("utf-8")
            except Exception:
                pass

        conversation_parts = []
        for msg in history[-10:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            conversation_parts.append(f"[{role}]: {content}")

        if contract_text:
            conversation_parts.append(f"\n[Contexte - Contrat analyse]:\n{contract_text[:2000]}...\n")

        conversation_parts.append(f"[user]: {message.content}")
        full_prompt = "\n\n".join(conversation_parts)

        settings = message.metadata.get("settings", {}) if message.metadata else {}
        analysis_mode = settings.get("analysisMode", "contract_only")
        enhanced_system_prompt = system_prompt + f"\nMODE D'ANALYSE ACTUEL : {analysis_mode}"

        async for token in context.llm.stream(
            prompt=full_prompt,
            system_prompt=enhanced_system_prompt,
            temperature=0.5,
            max_tokens=2048,
        ):
            yield AgentResponseChunk(content=token)

        yield AgentResponseChunk(content="", is_final=True, metadata={"type": "question_answer"})
