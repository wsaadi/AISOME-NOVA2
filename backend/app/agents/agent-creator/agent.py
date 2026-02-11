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
        context.set_progress(10, "Loading system prompt...")

        # Load the system prompt with all framework specs
        system_prompt = self._load_system_prompt()

        context.set_progress(20, "Loading conversation history...")

        # Get conversation history for continuity
        history = await context.memory.get_history(limit=50)

        # Build the full conversation for the LLM
        conversation = self._build_conversation(history, message)

        context.set_progress(30, "Generating response...")

        # Call LLM with comprehensive context
        llm_response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        context.set_progress(70, "Processing response...")

        # Extract any generated files from the response
        files = self._extract_files(llm_response)
        clean_response = llm_response

        metadata: dict = {"phase": "conversation"}

        if files:
            context.set_progress(80, "Validating generated code...")

            # Validate the generated files
            validation = self._validate_generated_files(files)

            # Store files in MinIO
            slug = self._extract_slug_from_files(files)
            stored_files = {}

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
                warnings_text = "\n\n---\n**Validation warnings:**\n"
                for w in validation["warnings"]:
                    warnings_text += f"- {w}\n"
                clean_response += warnings_text

        context.set_progress(100, "Done")

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
        system_prompt = self._load_system_prompt()
        history = await context.memory.get_history(limit=50)
        conversation = self._build_conversation(history, message)

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
            slug = self._extract_slug_from_files(files)
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
            metadata={"files": files} if files else {},
        )

    # =====================================================================
    # Private helpers
    # =====================================================================

    def _load_system_prompt(self) -> str:
        """Charge le system prompt depuis prompts/system.md."""
        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        return system_prompt_path.read_text(encoding="utf-8")

    def _build_conversation(
        self, history: list, message: UserMessage
    ) -> str:
        """
        Construit le prompt complet avec historique de conversation.

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

    def _validate_generated_files(self, files: dict[str, str]) -> dict:
        """
        Valide les fichiers générés pour la conformité framework.

        Vérifie les règles de sécurité, la structure, et les conventions
        sans exécuter le code.

        Args:
            files: Dict {filepath: content} des fichiers générés

        Returns:
            Dict avec 'valid': bool, 'errors': list, 'warnings': list
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- Validate manifest.json ---
        manifest_content = files.get("backend/manifest.json", "")
        if not manifest_content:
            errors.append("Missing backend/manifest.json")
        else:
            try:
                manifest = json.loads(manifest_content)
                for field in ["name", "slug", "version", "description"]:
                    if field not in manifest:
                        errors.append(f"manifest.json missing required field: {field}")
                slug = manifest.get("slug", "")
                if slug and not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
                    errors.append(f"Invalid slug format: {slug}")
            except json.JSONDecodeError as exc:
                errors.append(f"manifest.json is not valid JSON: {exc}")

        # --- Validate agent.py ---
        agent_content = files.get("backend/agent.py", "")
        if not agent_content:
            errors.append("Missing backend/agent.py")
        else:
            if "BaseAgent" not in agent_content:
                errors.append("agent.py must extend BaseAgent")
            if "handle_message" not in agent_content:
                errors.append("agent.py must implement handle_message()")
            if '"""' not in agent_content and "'''" not in agent_content:
                warnings.append("agent.py should have docstrings")

            # Check forbidden imports
            for forbidden in FORBIDDEN_IMPORTS:
                if forbidden in agent_content:
                    errors.append(f"Forbidden import in agent.py: {forbidden}")

            # Check forbidden builtins
            for forbidden in FORBIDDEN_BUILTINS:
                # Allow open() only for manifest/prompt loading
                if forbidden == "open(" and agent_content.count("open(") <= 2:
                    continue
                if forbidden in agent_content:
                    errors.append(f"Forbidden builtin in agent.py: {forbidden}")

        # --- Validate system.md ---
        system_content = files.get("backend/prompts/system.md", "")
        if not system_content:
            errors.append("Missing backend/prompts/system.md")
        elif len(system_content.strip()) < 50:
            warnings.append("system.md seems too short — consider adding more instructions")

        # --- Validate frontend ---
        frontend_content = files.get("frontend/index.tsx", "")
        if not frontend_content:
            errors.append("Missing frontend/index.tsx")
        else:
            if "export default" not in frontend_content:
                errors.append("index.tsx must have a default export")
            if "AgentViewProps" not in frontend_content:
                errors.append("index.tsx must implement AgentViewProps")

            # Check forbidden frontend imports
            for forbidden in FORBIDDEN_FRONTEND_IMPORTS:
                if forbidden in frontend_content:
                    errors.append(f"Forbidden import in index.tsx: {forbidden}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
