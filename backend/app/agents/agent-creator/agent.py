"""
Agent: Agent Creator
Description: Creates complete NOVA2 agents from natural language descriptions.

This agent acts as an interactive factory:
1. Receives a natural language description of the desired agent
2. Asks clarifying questions to gather all requirements
3. Generates all required files (manifest.json, agent.py, system.md, index.tsx, styles.ts)
4. Validates compliance with AGENT_FRAMEWORK.md
5. Stores generated files in MinIO for download/deployment

All generated agents are multilingual by default.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from app.framework.base import BaseAgent
from app.framework.schemas import (
    AgentManifest,
    AgentResponse,
    AgentResponseChunk,
    UserMessage,
)
from app.i18n.translations import t

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext


# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

FILE_START_MARKER = "<<<FILE:"
FILE_END_MARKER = "<<<END_FILE>>>"

FORBIDDEN_IMPORTS = [
    "import os",
    "from os",
    "import subprocess",
    "from subprocess",
    "import shutil",
    "from shutil",
    "import requests",
    "from requests",
    "import httpx",
    "from httpx",
    "import urllib",
    "from urllib",
    "import socket",
    "from socket",
    "import aiohttp",
    "from aiohttp",
    "import sqlite3",
    "from sqlite3",
    "import psycopg2",
    "from psycopg2",
    "import asyncpg",
    "from asyncpg",
    "import sqlalchemy",
    "from sqlalchemy",
    "import redis",
    "from redis",
    "import celery",
    "from celery",
    "import boto3",
    "from boto3",
    "import minio",
    "from minio",
]

FORBIDDEN_BUILTINS = ["exec(", "eval(", "compile(", "__import__(", "globals(", "locals("]

FORBIDDEN_FRONTEND_IMPORTS = [
    "from '@mui",
    "from \"@mui",
    "import axios",
    "from 'axios",
    "from \"axios",
    "from 'recharts",
    "from \"recharts",
]


class AgentCreatorAgent(BaseAgent):
    """
    Agent Creator — Creates complete NOVA2 agents via natural language.

    Workflow:
        1. User describes the agent they want in natural language
        2. This agent asks clarifying questions (purpose, tools, connectors, UI, triggers)
        3. Once requirements are gathered, generates all 5 files
        4. Validates the generated code for framework compliance
        5. Stores files in MinIO and returns them in response metadata
        6. Supports iterative refinement — user can request changes

    All generated agents include multilingual support by default.
    """

    @property
    def manifest(self) -> AgentManifest:
        """Retourne le manifeste de l'agent depuis manifest.json."""
        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        return AgentManifest(**data)

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """
        Traite un message utilisateur dans le flux de création d'agent.

        Le flux est entièrement piloté par le LLM qui décide de :
        - Poser des questions clarificatrices
        - Générer les fichiers de l'agent
        - Proposer des modifications

        Args:
            message: Message de l'utilisateur (description, réponses, demandes)
            context: Contexte d'exécution framework

        Returns:
            AgentResponse avec le contenu conversationnel et les fichiers générés en metadata
        """
        lang = context.lang

        context.set_progress(10, t("agent_creator.progress.loading_prompt", lang))

        # Get conversation history for continuity
        context.set_progress(20, t("agent_creator.progress.loading_history", lang))
        history = await context.memory.get_history(limit=50) if context.memory else []

        # Count user messages to determine conversation phase
        user_msg_count = sum(
            1 for msg in history if (getattr(msg, "role", "user") == "user")
        ) + 1
        in_generation_phase = user_msg_count >= 4

        # Load system prompt — question-only version in early phase
        # so the LLM literally cannot see file format instructions
        system_prompt = self._load_system_prompt(generation_phase=in_generation_phase)

        # Build the full conversation for the LLM
        conversation = self._build_conversation(history, message)

        context.set_progress(30, t("agent_creator.progress.generating", lang))

        # Call LLM with comprehensive context
        llm_response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        context.set_progress(70, t("agent_creator.progress.processing", lang))

        # Extract any generated files from the response
        files = self._extract_files(llm_response)
        clean_response = llm_response

        metadata: dict = {"phase": "conversation"}

        if files:
            context.set_progress(80, t("agent_creator.progress.validating", lang))

            # Auto-generate agent.json for import compatibility
            files = self._inject_agent_json(files)

            # Validate the generated files
            validation = self._validate_generated_files(files, lang)

            # Store files in MinIO (if storage is available)
            slug = self._extract_slug_from_files(files)
            stored_files = {}

            if context.storage:
                for filepath, content in files.items():
                    storage_key = f"generated/{slug}/{filepath}"
                    await context.storage.put(
                        storage_key,
                        content.encode("utf-8"),
                        "text/plain",
                    )
                    stored_files[filepath] = storage_key

            # Clean response: remove file markers but keep surrounding text
            clean_response = self._clean_response(llm_response)

            metadata = {
                "phase": "generated",
                "agent_slug": slug,
                "files": files,
                "stored_files": stored_files,
                "validation": validation,
            }

            # Append validation feedback to response if there are issues
            if validation.get("warnings"):
                warnings_text = f"\n\n---\n**{t('agent_creator.val.validation_warnings', lang)}**\n"
                for w in validation["warnings"]:
                    warnings_text += f"- {w}\n"
                clean_response += warnings_text

        context.set_progress(100, t("agent_creator.progress.done", lang))

        # Include token usage in metadata for consumption tracking
        usage = context.llm.last_usage
        metadata["tokens_in"] = usage.get("tokens_in", 0)
        metadata["tokens_out"] = usage.get("tokens_out", 0)

        return AgentResponse(content=clean_response, metadata=metadata)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Version streaming — envoie les tokens au fur et à mesure.

        Pour le mode interactif (questions), le streaming améliore l'UX.
        Pour la génération de code, on accumule pour parser les fichiers.

        Args:
            message: Message de l'utilisateur
            context: Contexte d'exécution framework

        Yields:
            AgentResponseChunk avec les tokens progressifs
        """
        history = await context.memory.get_history(limit=50) if context.memory else []
        conversation = self._build_conversation(history, message)

        # Count user messages for question-phase enforcement
        user_msg_count = sum(
            1 for msg in history if (getattr(msg, "role", "user") == "user")
        ) + 1
        in_generation_phase = user_msg_count >= 4

        # Only give the LLM the generation instructions when ready
        system_prompt = self._load_system_prompt(generation_phase=in_generation_phase)

        accumulated = ""
        async for token in context.llm.stream(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        ):
            accumulated += token
            yield AgentResponseChunk(content=token)

        # After streaming completes, check for generated files
        files = self._extract_files(accumulated)

        if files:
            # Auto-generate agent.json for import compatibility
            files = self._inject_agent_json(files)

            slug = self._extract_slug_from_files(files)
            validation = self._validate_generated_files(files, context.lang)

            if context.storage:
                for filepath, content in files.items():
                    storage_key = f"generated/{slug}/{filepath}"
                    await context.storage.put(
                        storage_key,
                        content.encode("utf-8"),
                        "text/plain",
                    )

            yield AgentResponseChunk(
                content="",
                is_final=True,
                metadata={
                    "phase": "generated",
                    "agent_slug": slug,
                    "files": files,
                    "validation": validation,
                },
            )
        else:
            yield AgentResponseChunk(
                content="",
                is_final=True,
                metadata={},
            )

    # =====================================================================
    # Private helpers
    # =====================================================================

    # Marker used to split the system prompt into question vs generation phases
    _GENERATION_MARKER = "<!-- GENERATION_PHASE_START -->"

    def _load_system_prompt(self, generation_phase: bool = True) -> str:
        """
        Charge le system prompt depuis prompts/system.md.

        In question phase (generation_phase=False), only the first part of
        the prompt is returned — the LLM literally does not see the file
        format, framework spec, or code examples.  It can only ask questions.

        Args:
            generation_phase: If True, return the full prompt.
                              If False, return only the question-phase portion.
        """
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        full_prompt = system_prompt_path.read_text(encoding="utf-8")

        if generation_phase:
            return full_prompt

        # Return only the part before the generation marker
        marker_pos = full_prompt.find(self._GENERATION_MARKER)
        if marker_pos == -1:
            return full_prompt

        question_prompt = full_prompt[:marker_pos].rstrip()
        question_prompt += (
            "\n\n---\n"
            "You are currently in the QUESTION PHASE. "
            "Your ONLY task is to ask ONE clarifying question per message. "
            "Do NOT generate code, files, or technical specifications yet. "
            "Just have a natural conversation to understand what the user needs."
        )
        return question_prompt

    def _build_conversation(
        self, history: list, message: UserMessage
    ) -> str:
        """
        Construit le prompt complet avec historique de conversation.

        Injecte un rappel pour forcer la phase de questions si la conversation
        est encore courte (< 4 échanges).

        Args:
            history: Messages précédents de la session
            message: Message actuel de l'utilisateur

        Returns:
            Texte complet de la conversation formaté pour le LLM
        """
        parts: list[str] = []

        for msg in history:
            role = msg.role if hasattr(msg, "role") else "user"
            content = msg.content if hasattr(msg, "content") else str(msg)
            parts.append(f"[{role}]: {content}")

        parts.append(f"[user]: {message.content}")

        # If conversation is short, remind the LLM to ask questions first
        user_msg_count = sum(1 for msg in history if (getattr(msg, "role", "user") == "user")) + 1
        if user_msg_count < 4:
            parts.append(
                "[system]: REMINDER — You are still in the question phase. "
                "Do NOT generate files yet (no <<<FILE:>>> markers). "
                "Ask the next clarifying question, one at a time."
            )

        return "\n\n".join(parts)

    def _extract_files(self, response: str) -> dict[str, str]:
        """
        Extrait les fichiers générés depuis la réponse LLM.

        Cherche les marqueurs <<<FILE:path>>> ... <<<END_FILE>>> et extrait
        le contenu de chaque fichier.

        Args:
            response: Réponse complète du LLM

        Returns:
            Dict {filepath: content} des fichiers extraits
        """
        files: dict[str, str] = {}

        pattern = re.compile(
            r"<<<FILE:(.*?)>>>\s*\n(.*?)<<<END_FILE>>>",
            re.DOTALL,
        )

        for match in pattern.finditer(response):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            # Remove markdown code block wrappers if present
            content = re.sub(r"^```\w*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            files[filepath] = content

        return files

    def _clean_response(self, response: str) -> str:
        """
        Retire les marqueurs de fichiers de la réponse pour l'affichage.

        Garde le texte conversationnel et remplace les blocs de fichiers
        par des résumés lisibles.

        Args:
            response: Réponse brute du LLM avec marqueurs

        Returns:
            Réponse nettoyée pour l'affichage utilisateur
        """
        pattern = re.compile(
            r"<<<FILE:(.*?)>>>\s*\n.*?<<<END_FILE>>>",
            re.DOTALL,
        )

        def replacer(match: re.Match) -> str:
            filepath = match.group(1).strip()
            return f"**`{filepath}`** — Generated"

        cleaned = pattern.sub(replacer, response)
        return cleaned.strip()

    def _inject_agent_json(self, files: dict[str, str]) -> dict[str, str]:
        """
        Auto-génère un fichier agent.json compatible avec l'import platform.

        Construit agent.json à partir de backend/manifest.json et
        backend/prompts/system.md pour que le ZIP soit directement importable
        via /api/agents/import.

        Args:
            files: Dict des fichiers générés par le LLM

        Returns:
            Dict enrichi avec agent.json à la racine
        """
        manifest_content = files.get("backend/manifest.json", "")
        system_md = files.get("backend/prompts/system.md", "")

        if not manifest_content:
            return files

        try:
            manifest = json.loads(manifest_content)
        except json.JSONDecodeError:
            return files

        agent_json = {
            "name": manifest.get("name", "Unknown Agent"),
            "slug": manifest.get("slug", "unknown-agent"),
            "description": manifest.get("description", ""),
            "version": manifest.get("version", "1.0.0"),
            "agent_type": manifest.get("category", "conversational"),
            "config": {
                "icon": manifest.get("icon", "smart_toy"),
                "category": manifest.get("category", "general"),
                "tags": manifest.get("tags", []),
                "dependencies": manifest.get("dependencies", {}),
                "triggers": manifest.get("triggers", []),
                "capabilities": manifest.get("capabilities", []),
            },
            "system_prompt": system_md,
            "moderation_rules": [],
            "export_version": "1.0",
        }

        files["agent.json"] = json.dumps(agent_json, indent=2, ensure_ascii=False)
        return files

    def _extract_slug_from_files(self, files: dict[str, str]) -> str:
        """
        Extrait le slug de l'agent depuis le manifest.json généré.

        Args:
            files: Dict des fichiers générés

        Returns:
            Le slug de l'agent, ou 'unknown-agent' si non trouvé
        """
        manifest_content = files.get("backend/manifest.json", "")
        if manifest_content:
            try:
                data = json.loads(manifest_content)
                return data.get("slug", "unknown-agent")
            except json.JSONDecodeError:
                pass
        return "unknown-agent"

    def _validate_generated_files(self, files: dict[str, str], lang: str = "en") -> dict:
        """
        Valide les fichiers générés pour la conformité framework.

        Vérifie les règles de sécurité, la structure, et les conventions
        sans exécuter le code.

        Args:
            files: Dict {filepath: content} des fichiers générés
            lang: Langue pour les messages de validation

        Returns:
            Dict avec 'valid': bool, 'errors': list, 'warnings': list
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- Validate manifest.json ---
        manifest_content = files.get("backend/manifest.json", "")
        if not manifest_content:
            errors.append(t("agent_creator.val.missing_manifest", lang))
        else:
            try:
                manifest = json.loads(manifest_content)
                for field in ["name", "slug", "version", "description"]:
                    if field not in manifest:
                        errors.append(t("agent_creator.val.manifest_missing_field", lang, field=field))
                slug = manifest.get("slug", "")
                if slug and not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
                    errors.append(t("agent_creator.val.invalid_slug", lang, slug=slug))
            except json.JSONDecodeError as exc:
                errors.append(t("agent_creator.val.manifest_invalid_json", lang, detail=str(exc)))

        # --- Validate agent.py ---
        agent_content = files.get("backend/agent.py", "")
        if not agent_content:
            errors.append(t("agent_creator.val.missing_agent", lang))
        else:
            if "BaseAgent" not in agent_content:
                errors.append(t("agent_creator.val.no_base_agent", lang))
            if "handle_message" not in agent_content:
                errors.append(t("agent_creator.val.no_handle_message", lang))
            if '"""' not in agent_content and "'''" not in agent_content:
                warnings.append(t("agent_creator.val.no_docstrings", lang))

            # Check forbidden imports
            for forbidden in FORBIDDEN_IMPORTS:
                if forbidden in agent_content:
                    errors.append(t("agent_creator.val.forbidden_import", lang, name=forbidden))

            # Check forbidden builtins
            for forbidden in FORBIDDEN_BUILTINS:
                # Allow open() only for manifest/prompt loading
                if forbidden == "open(" and agent_content.count("open(") <= 2:
                    continue
                if forbidden in agent_content:
                    errors.append(t("agent_creator.val.forbidden_builtin", lang, name=forbidden))

        # --- Validate system.md ---
        system_content = files.get("backend/prompts/system.md", "")
        if not system_content:
            errors.append(t("agent_creator.val.missing_system_md", lang))
        elif len(system_content.strip()) < 50:
            warnings.append(t("agent_creator.val.system_md_short", lang))

        # --- Validate frontend ---
        frontend_content = files.get("frontend/index.tsx", "")
        if not frontend_content:
            errors.append(t("agent_creator.val.missing_frontend", lang))
        else:
            if "export default" not in frontend_content:
                errors.append(t("agent_creator.val.no_default_export", lang))
            if "AgentViewProps" not in frontend_content:
                errors.append(t("agent_creator.val.no_agent_view_props", lang))

            # Check forbidden frontend imports
            for forbidden in FORBIDDEN_FRONTEND_IMPORTS:
                if forbidden in frontend_content:
                    errors.append(t("agent_creator.val.forbidden_frontend_import", lang, name=forbidden))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
