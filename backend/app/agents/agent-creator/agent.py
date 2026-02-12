"""
Agent Creator — Creates complete NOVA2 agents from natural language descriptions.

Interactive workflow:
    1. User describes the agent they want
    2. Clarifying questions are asked one at a time (question phase)
    3. Requirements are confirmed with the user
    4. All framework-compliant files are generated (generation phase)
    5. Generated code is validated and packaged for download

The system prompt is split into two parts:
  - QUESTION PHASE: The LLM only sees conversation rules, NOT file format.
    This physically prevents premature code generation.
  - GENERATION PHASE: The LLM sees the full spec including file markers,
    framework reference, and code templates.
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
# Constants
# ---------------------------------------------------------------------------

_GENERATION_MARKER = "<!-- GENERATION_INSTRUCTIONS_START -->"

# Minimum number of user messages before we allow generation phase.
# 1st = initial description, 2nd = answer to question, 3rd = confirmation
_MIN_MESSAGES_FOR_GENERATION = 3

# Keywords that signal the user wants to skip to generation or confirm
_CONFIRMATION_KEYWORDS = [
    "ok", "oui", "yes", "go", "génère", "genere", "generate",
    "c'est bon", "c est bon", "parfait", "valide", "lance",
    "fais-le", "fais le", "do it", "let's go", "lets go",
    "confirm", "confirme", "approved", "approuvé",
]

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

        Phase detection:
        - Question phase: LLM only sees conversation rules (cannot generate files)
        - Generation phase: LLM sees full spec with file format and framework ref

        Transition to generation when:
        - At least 3 user messages exchanged, OR
        - At least 2 user messages + user explicitly confirms

        NOTE: engine.py saves the user message to the session BEFORE calling
        handle_message, so history already contains the current message.
        We do NOT add +1 to the count.
        """
        lang = context.lang

        context.set_progress(10, t("agent_creator.progress.loading_prompt", lang))

        # Determine conversation phase from history
        # NOTE: the current user message is ALREADY in history (saved by engine.py)
        context.set_progress(20, t("agent_creator.progress.loading_history", lang))
        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content
        )

        # Load the appropriate system prompt
        system_prompt = self._load_system_prompt(generation_phase=in_generation_phase)

        # Build conversation from history (current message already included)
        conversation = self._build_conversation(
            history, in_generation_phase
        )

        context.set_progress(30, t("agent_creator.progress.generating", lang))
        llm_response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        context.set_progress(70, t("agent_creator.progress.processing", lang))

        # HARD BLOCK: never extract files during question phase,
        # even if the LLM ignores instructions and outputs markers
        files: dict[str, str] = {}
        if in_generation_phase:
            files = self._extract_files(llm_response)
        elif _FILE_PATTERN.search(llm_response):
            # LLM tried to generate during question phase — strip it
            llm_response = self._strip_file_markers(llm_response)

        metadata: dict = {"phase": "conversation"}

        if files:
            context.set_progress(80, t("agent_creator.progress.validating", lang))

            files = self._build_agent_json(files)
            validation = self._validate(files, lang)

            slug = self._get_slug(files)
            stored_files: dict[str, str] = {}
            if context.storage:
                for filepath, content in files.items():
                    key = f"generated/{slug}/{filepath}"
                    await context.storage.put(
                        key, content.encode("utf-8"), "text/plain"
                    )
                    stored_files[filepath] = key

            display_text = self._strip_file_markers(llm_response)

            if validation.get("warnings"):
                display_text += (
                    f"\n\n---\n**{t('agent_creator.val.validation_warnings', lang)}**\n"
                )
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

        usage = context.llm.last_usage
        metadata["tokens_in"] = usage.get("tokens_in", 0)
        metadata["tokens_out"] = usage.get("tokens_out", 0)

        return AgentResponse(content=llm_response, metadata=metadata)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Streaming version — sends tokens progressively.

        Uses the same phase detection as handle_message.
        Files are extracted after the full response is accumulated.
        HARD BLOCK: files are never extracted during question phase.
        """
        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content
        )

        system_prompt = self._load_system_prompt(generation_phase=in_generation_phase)
        conversation = self._build_conversation(history, in_generation_phase)

        accumulated = ""
        async for token in context.llm.stream(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        ):
            accumulated += token
            yield AgentResponseChunk(content=token)

        # HARD BLOCK: never extract files during question phase
        files: dict[str, str] = {}
        if in_generation_phase:
            files = self._extract_files(accumulated)

        if files:
            files = self._build_agent_json(files)
            slug = self._get_slug(files)
            validation = self._validate(files, context.lang)

            if context.storage:
                for filepath, content in files.items():
                    key = f"generated/{slug}/{filepath}"
                    await context.storage.put(
                        key, content.encode("utf-8"), "text/plain"
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
            yield AgentResponseChunk(content="", is_final=True, metadata={})

    # ------------------------------------------------------------------
    # Phase detection
    # ------------------------------------------------------------------

    @staticmethod
    def _count_user_messages(history: list) -> int:
        """
        Count user messages in history.

        NOTE: engine.py saves the current user message to the session
        BEFORE calling handle_message, so history already contains it.
        No +1 adjustment is needed.
        """
        count = 0
        for msg in history:
            role = getattr(msg, "role", None)
            # role can be a MessageRole enum (inherits from str) or a string
            role_str = role.value if hasattr(role, "value") else str(role)
            if role_str == "user":
                count += 1
        return count

    def _should_enter_generation(
        self, user_msg_count: int, current_message: str
    ) -> bool:
        """
        Determine whether the conversation should enter generation phase.

        Rules:
        - Always question phase on 1st or 2nd message
        - Generation allowed after 3+ user messages (enough Q&A happened)
        - Generation allowed after 2+ user messages IF user explicitly confirms

        Even if the LLM ignores the question-phase prompt, the hard block
        in handle_message will prevent file extraction.
        """
        if user_msg_count <= 1:
            return False

        if user_msg_count >= _MIN_MESSAGES_FOR_GENERATION:
            return True

        # Check for explicit confirmation keywords (2+ messages)
        if user_msg_count >= 2:
            lower = current_message.lower().strip()
            for keyword in _CONFIRMATION_KEYWORDS:
                if keyword in lower:
                    return True

        return False

    # ------------------------------------------------------------------
    # System prompt management
    # ------------------------------------------------------------------

    def _load_system_prompt(self, generation_phase: bool = False) -> str:
        """
        Load the system prompt, optionally truncated for question phase.

        In question phase:
          - Only the conversation flow rules are shown
          - The LLM cannot see file markers, framework spec, or code templates
          - A strong reminder is appended to force question-only behavior

        In generation phase:
          - The full prompt is returned including all framework reference
        """
        path = Path(__file__).parent / "prompts" / "system.md"
        full_prompt = path.read_text(encoding="utf-8")

        if generation_phase:
            return full_prompt

        # Question phase: strip everything after the generation marker
        marker_pos = full_prompt.find(_GENERATION_MARKER)
        if marker_pos == -1:
            return full_prompt

        question_prompt = full_prompt[:marker_pos].rstrip()
        question_prompt += (
            "\n\n---\n\n"
            "## CURRENT STATUS: QUESTION PHASE\n\n"
            "You are in the **QUESTION PHASE**. Your ONLY job right now:\n"
            "1. Read the user's message\n"
            "2. Ask ONE clarifying question to better understand their needs\n"
            "3. Do NOT generate any code, files, or technical output\n"
            "4. Do NOT use <<<FILE: markers — you don't have access to them yet\n"
            "5. Keep your response conversational and focused\n\n"
            "Once you have gathered enough information (purpose, workflow, UI layout, "
            "tools/connectors), present a structured summary and ask for confirmation. "
            "The system will then give you access to the generation instructions."
        )
        return question_prompt

    # ------------------------------------------------------------------
    # Conversation building
    # ------------------------------------------------------------------

    def _build_conversation(
        self, history: list, generation_phase: bool
    ) -> str:
        """
        Build the conversation string from history.

        NOTE: the current user message is already in history (saved by
        engine.py before handle_message is called), so we don't re-add it.

        Injects a system reminder during question phase to reinforce behavior.
        """
        parts: list[str] = []
        for msg in history:
            role = getattr(msg, "role", "user")
            # Handle MessageRole enum
            role_str = role.value if hasattr(role, "value") else str(role)
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role_str}]: {content}")

        # In question phase, inject a reminder after the conversation
        if not generation_phase:
            parts.append(
                "[system]: REMINDER — You are in the QUESTION PHASE. "
                "Ask ONE clarifying question about the user's needs. "
                "Do NOT generate code, files, or technical output. "
                "Do NOT use <<<FILE: markers."
            )

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # File extraction & cleaning
    # ------------------------------------------------------------------

    def _extract_files(self, text: str) -> dict[str, str]:
        """Extract files from <<<FILE:path>>> ... <<<END_FILE>>> markers."""
        files: dict[str, str] = {}
        for match in _FILE_PATTERN.finditer(text):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            content = re.sub(r"^```\w*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            files[filepath] = content
        return files

    def _strip_file_markers(self, text: str) -> str:
        """Remove file markers from response, replacing with brief summaries."""

        def _replace(m: re.Match) -> str:
            return f"`{m.group(1).strip()}` — generated"

        return _FILE_PATTERN.sub(_replace, text).strip()

    # ------------------------------------------------------------------
    # Agent JSON generation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, files: dict[str, str], lang: str = "en") -> dict:
        """
        Validate all generated files for framework compliance.

        Checks security rules, required structure, naming conventions,
        and framework contract adherence.
        """
        errors: list[str] = []
        warnings: list[str] = []

        self._validate_manifest(files, errors, lang)
        self._validate_agent_py(files, errors, warnings, lang)
        self._validate_system_md(files, errors, warnings, lang)
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
            errors.append(
                t("agent_creator.val.manifest_invalid_json", lang, detail=str(exc))
            )
            return

        for field in ("name", "slug", "version", "description"):
            if field not in manifest:
                errors.append(
                    t("agent_creator.val.manifest_missing_field", lang, field=field)
                )

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
                errors.append(
                    t("agent_creator.val.forbidden_import", lang, name=forbidden)
                )

        for forbidden in FORBIDDEN_PYTHON_BUILTINS:
            if forbidden == "open(" and code.count("open(") <= 2:
                continue
            if forbidden in code:
                errors.append(
                    t("agent_creator.val.forbidden_builtin", lang, name=forbidden)
                )

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
                errors.append(
                    t(
                        "agent_creator.val.forbidden_frontend_import",
                        lang,
                        name=forbidden,
                    )
                )
