"""
Agent Creator — Creates complete NOVA2 agents from natural language descriptions.

Interactive workflow:
    1. User describes the agent they want
    2. Clarifying questions are asked one at a time
    3. Requirements are confirmed with the user
    4. All framework-compliant files are generated
    5. Generated code is validated and packaged for download
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


# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

FORBIDDEN_PYTHON_IMPORTS = [
    "import os", "from os",
    "import subprocess", "from subprocess",
    "import shutil", "from shutil",
    "import requests", "from requests",
    "import httpx", "from httpx",
    "import urllib", "from urllib",
    "import socket", "from socket",
    "import aiohttp", "from aiohttp",
    "import sqlite3", "from sqlite3",
    "import psycopg2", "from psycopg2",
    "import asyncpg", "from asyncpg",
    "import sqlalchemy", "from sqlalchemy",
    "import redis", "from redis",
    "import celery", "from celery",
    "import boto3", "from boto3",
    "import minio", "from minio",
]

FORBIDDEN_PYTHON_BUILTINS = [
    "exec(", "eval(", "compile(",
    "__import__(", "globals(", "locals(",
]

FORBIDDEN_FRONTEND_IMPORTS = [
    "from '@mui", 'from "@mui',
    "import axios", "from 'axios", 'from "axios',
    "from 'recharts", 'from "recharts',
    "from 'd3", 'from "d3',
    "from 'lodash", 'from "lodash',
]

_FILE_PATTERN = re.compile(
    r"<<<FILE:(.*?)>>>\s*\n(.*?)<<<END_FILE>>>",
    re.DOTALL,
)


class AgentCreatorAgent(BaseAgent):
    """Creates complete NOVA2 agents from natural language via interactive conversation."""

    @property
    def manifest(self) -> AgentManifest:
        """Load agent manifest from manifest.json."""
        with open(Path(__file__).parent / "manifest.json") as f:
            return AgentManifest(**json.load(f))

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """
        Process a user message in the agent creation flow.

        The LLM drives the conversation naturally — asking questions,
        confirming requirements, then generating files when ready.
        """
        lang = context.lang

        context.set_progress(10, t("agent_creator.progress.loading_prompt", lang))
        system_prompt = self._load_system_prompt()

        context.set_progress(20, t("agent_creator.progress.loading_history", lang))
        history = await context.memory.get_history(limit=50) if context.memory else []
        conversation = self._build_conversation(history, message)

        context.set_progress(30, t("agent_creator.progress.generating", lang))
        llm_response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        context.set_progress(70, t("agent_creator.progress.processing", lang))

        # Try to extract generated files from the response
        files = self._extract_files(llm_response)
        metadata: dict = {"phase": "conversation"}

        if files:
            context.set_progress(80, t("agent_creator.progress.validating", lang))

            # Add agent.json for platform import compatibility
            files = self._build_agent_json(files)

            # Validate all generated files
            validation = self._validate(files, lang)

            # Store files in MinIO
            slug = self._get_slug(files)
            stored_files: dict[str, str] = {}
            if context.storage:
                for filepath, content in files.items():
                    key = f"generated/{slug}/{filepath}"
                    await context.storage.put(key, content.encode("utf-8"), "text/plain")
                    stored_files[filepath] = key

            # Clean the response for display
            display_text = self._strip_file_markers(llm_response)

            # Append validation warnings if any
            if validation.get("warnings"):
                display_text += f"\n\n---\n**{t('agent_creator.val.validation_warnings', lang)}**\n"
                for warning in validation["warnings"]:
                    display_text += f"- {warning}\n"

            metadata = {
                "phase": "generated",
                "agent_slug": slug,
                "files": files,
                "stored_files": stored_files,
                "validation": validation,
            }
            llm_response = display_text

        context.set_progress(100, t("agent_creator.progress.done", lang))

        # Track token usage
        usage = context.llm.last_usage
        metadata["tokens_in"] = usage.get("tokens_in", 0)
        metadata["tokens_out"] = usage.get("tokens_out", 0)

        return AgentResponse(content=llm_response, metadata=metadata)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Streaming version — sends tokens progressively.

        Files are extracted and processed after the full response is accumulated.
        """
        system_prompt = self._load_system_prompt()
        history = await context.memory.get_history(limit=50) if context.memory else []
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

        # Process files after streaming completes
        files = self._extract_files(accumulated)

        if files:
            files = self._build_agent_json(files)
            slug = self._get_slug(files)
            validation = self._validate(files, context.lang)

            if context.storage:
                for filepath, content in files.items():
                    key = f"generated/{slug}/{filepath}"
                    await context.storage.put(key, content.encode("utf-8"), "text/plain")

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
            yield AgentResponseChunk(content="", is_final=True, metadata={})

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_system_prompt(self) -> str:
        """Load the full system prompt from prompts/system.md."""
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    def _build_conversation(self, history: list, message: UserMessage) -> str:
        """Build the conversation string from history + current message for the LLM."""
        parts: list[str] = []
        for msg in history:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role}]: {content}")
        parts.append(f"[user]: {message.content}")
        return "\n\n".join(parts)

    def _extract_files(self, text: str) -> dict[str, str]:
        """Extract files from <<<FILE:path>>> ... <<<END_FILE>>> markers."""
        files: dict[str, str] = {}
        for match in _FILE_PATTERN.finditer(text):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            # Strip markdown code fence wrappers if present
            content = re.sub(r"^```\w*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            files[filepath] = content
        return files

    def _strip_file_markers(self, text: str) -> str:
        """Remove file markers from response, replacing with brief summaries."""
        def _replace(m: re.Match) -> str:
            return f"`{m.group(1).strip()}` — generated"
        return _FILE_PATTERN.sub(_replace, text).strip()

    def _get_slug(self, files: dict[str, str]) -> str:
        """Extract the agent slug from the generated manifest.json."""
        raw = files.get("backend/manifest.json", "")
        if raw:
            try:
                return json.loads(raw).get("slug", "unknown-agent")
            except json.JSONDecodeError:
                pass
        return "unknown-agent"

    def _build_agent_json(self, files: dict[str, str]) -> dict[str, str]:
        """Generate agent.json for platform import from manifest + system prompt."""
        raw = files.get("backend/manifest.json", "")
        if not raw:
            return files

        try:
            m = json.loads(raw)
        except json.JSONDecodeError:
            return files

        agent_json = {
            "name": m.get("name", "Unknown"),
            "slug": m.get("slug", "unknown"),
            "description": m.get("description", ""),
            "version": m.get("version", "1.0.0"),
            "agent_type": m.get("category", "conversational"),
            "config": {
                "icon": m.get("icon", "smart_toy"),
                "category": m.get("category", "general"),
                "tags": m.get("tags", []),
                "dependencies": m.get("dependencies", {}),
                "triggers": m.get("triggers", []),
                "capabilities": m.get("capabilities", []),
            },
            "system_prompt": files.get("backend/prompts/system.md", ""),
            "moderation_rules": [],
            "export_version": "1.0",
        }

        files["agent.json"] = json.dumps(agent_json, indent=2, ensure_ascii=False)
        return files

    def _validate(self, files: dict[str, str], lang: str = "en") -> dict:
        """
        Validate all generated files for framework compliance.

        Checks security rules, required structure, naming conventions,
        and framework contract adherence.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- manifest.json ---
        self._validate_manifest(files, errors, lang)

        # --- agent.py ---
        self._validate_agent_py(files, errors, warnings, lang)

        # --- prompts/system.md ---
        self._validate_system_md(files, errors, warnings, lang)

        # --- frontend/index.tsx ---
        self._validate_frontend(files, errors, lang)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _validate_manifest(
        self, files: dict[str, str], errors: list[str], lang: str
    ) -> None:
        """Validate manifest.json structure and content."""
        raw = files.get("backend/manifest.json", "")
        if not raw:
            errors.append(t("agent_creator.val.missing_manifest", lang))
            return

        try:
            manifest = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(t("agent_creator.val.manifest_invalid_json", lang, detail=str(exc)))
            return

        for field in ("name", "slug", "version", "description"):
            if field not in manifest:
                errors.append(t("agent_creator.val.manifest_missing_field", lang, field=field))

        slug = manifest.get("slug", "")
        if slug and not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
            errors.append(t("agent_creator.val.invalid_slug", lang, slug=slug))

    def _validate_agent_py(
        self, files: dict[str, str], errors: list[str], warnings: list[str], lang: str
    ) -> None:
        """Validate agent.py for BaseAgent inheritance, forbidden imports, etc."""
        code = files.get("backend/agent.py", "")
        if not code:
            errors.append(t("agent_creator.val.missing_agent", lang))
            return

        if "BaseAgent" not in code:
            errors.append(t("agent_creator.val.no_base_agent", lang))
        if "handle_message" not in code:
            errors.append(t("agent_creator.val.no_handle_message", lang))
        if '"""' not in code and "'''" not in code:
            warnings.append(t("agent_creator.val.no_docstrings", lang))

        for forbidden in FORBIDDEN_PYTHON_IMPORTS:
            if forbidden in code:
                errors.append(t("agent_creator.val.forbidden_import", lang, name=forbidden))

        for forbidden in FORBIDDEN_PYTHON_BUILTINS:
            # Allow open() for manifest/prompt loading (max 2 occurrences)
            if forbidden == "open(" and code.count("open(") <= 2:
                continue
            if forbidden in code:
                errors.append(t("agent_creator.val.forbidden_builtin", lang, name=forbidden))

    def _validate_system_md(
        self, files: dict[str, str], errors: list[str], warnings: list[str], lang: str
    ) -> None:
        """Validate system.md presence and content quality."""
        content = files.get("backend/prompts/system.md", "")
        if not content:
            errors.append(t("agent_creator.val.missing_system_md", lang))
        elif len(content.strip()) < 50:
            warnings.append(t("agent_creator.val.system_md_short", lang))

    def _validate_frontend(
        self, files: dict[str, str], errors: list[str], lang: str
    ) -> None:
        """Validate frontend/index.tsx for required exports and forbidden imports."""
        code = files.get("frontend/index.tsx", "")
        if not code:
            errors.append(t("agent_creator.val.missing_frontend", lang))
            return

        if "export default" not in code:
            errors.append(t("agent_creator.val.no_default_export", lang))
        if "AgentViewProps" not in code:
            errors.append(t("agent_creator.val.no_agent_view_props", lang))

        for forbidden in FORBIDDEN_FRONTEND_IMPORTS:
            if forbidden in code:
                errors.append(t("agent_creator.val.forbidden_frontend_import", lang, name=forbidden))
