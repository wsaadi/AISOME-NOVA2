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
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from app.framework.base import BaseAgent

logger = logging.getLogger(__name__)
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
_EDIT_MODE_MARKER = "<!-- EDIT_MODE_INSTRUCTIONS -->"

# Minimum number of user messages before generation phase can be entered.
# The user must ALSO confirm explicitly (keyword match) — count alone
# never triggers generation.  This lets the LLM naturally progress
# through question → summary → confirmation.
_MIN_MESSAGES_FOR_GENERATION = 3
_MIN_MESSAGES_FOR_GENERATION_EDIT = 1  # Edit mode: generate on first confirmation

# Root path for reading existing agent source files
_AGENTS_ROOT = Path(__file__).parent.parent
_FRONTEND_AGENTS_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "src" / "agents"

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

        Transition to generation requires BOTH:
        - At least _MIN_MESSAGES_FOR_GENERATION user messages, AND
        - An explicit confirmation keyword in the latest message

        Edit mode:
        - Activated when message metadata contains edit_agent_slug
        - Loads existing agent source files and injects into context
        - Faster path to generation (fewer questions required)

        NOTE: engine.py saves the user message to the session BEFORE calling
        handle_message, so history already contains the current message.
        We do NOT add +1 to the count.
        """
        lang = context.lang

        context.set_progress(10, t("agent_creator.progress.loading_prompt", lang))

        # Detect edit mode from metadata
        edit_slug = self._detect_edit_mode(message, context)
        edit_source_files: dict[str, str] = {}
        if edit_slug:
            edit_source_files = self._load_agent_source(edit_slug)
            logger.info(
                f"[agent-creator] EDIT MODE: slug={edit_slug}, "
                f"files={list(edit_source_files.keys())}"
            )

        # Determine conversation phase from history
        # NOTE: the current user message is ALREADY in history (saved by engine.py)
        context.set_progress(20, t("agent_creator.progress.loading_history", lang))
        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)
        last_assistant_msg = self._get_last_assistant_message(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content, edit_mode=bool(edit_slug),
            last_assistant_message=last_assistant_msg,
        )
        logger.info(
            f"[agent-creator] handle_message: history={len(history)} msgs, "
            f"user_count={user_msg_count}, phase={'GENERATION' if in_generation_phase else 'QUESTION'}, "
            f"edit_mode={bool(edit_slug)}, summary_shown={self._assistant_showed_summary(last_assistant_msg)}, "
            f"msg={message.content[:80]!r}"
        )

        # Load live catalogs from registries
        tool_catalog = await self._build_tool_catalog(context)
        connector_catalog = await self._build_connector_catalog(context)

        # Load the appropriate system prompt (with injected catalogs)
        system_prompt = self._load_system_prompt(
            generation_phase=in_generation_phase,
            tool_catalog=tool_catalog,
            connector_catalog=connector_catalog,
            edit_mode=bool(edit_slug),
            edit_source_files=edit_source_files,
        )

        # Build conversation from history (current message already included)
        conversation = self._build_conversation(
            history, in_generation_phase, edit_slug=edit_slug,
            edit_source_files=edit_source_files,
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

            # Build set of known tool slugs for validation
            try:
                live_tools = await context.tools.list()
                known_tool_slugs = {t.slug for t in live_tools}
            except Exception:
                known_tool_slugs = None
            validation = self._validate(files, lang, known_tool_slugs=known_tool_slugs)

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
        edit_slug = self._detect_edit_mode(message, context)
        edit_source_files: dict[str, str] = {}
        if edit_slug:
            edit_source_files = self._load_agent_source(edit_slug)

        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)
        last_assistant_msg = self._get_last_assistant_message(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content, edit_mode=bool(edit_slug),
            last_assistant_message=last_assistant_msg,
        )
        logger.info(
            f"[agent-creator] handle_message_stream: history={len(history)} msgs, "
            f"user_count={user_msg_count}, phase={'GENERATION' if in_generation_phase else 'QUESTION'}, "
            f"edit_mode={bool(edit_slug)}, summary_shown={self._assistant_showed_summary(last_assistant_msg)}, "
            f"msg={message.content[:80]!r}"
        )

        tool_catalog = await self._build_tool_catalog(context)
        connector_catalog = await self._build_connector_catalog(context)
        system_prompt = self._load_system_prompt(
            generation_phase=in_generation_phase,
            tool_catalog=tool_catalog,
            connector_catalog=connector_catalog,
            edit_mode=bool(edit_slug),
            edit_source_files=edit_source_files,
        )
        conversation = self._build_conversation(
            history, in_generation_phase, edit_slug=edit_slug,
            edit_source_files=edit_source_files,
        )

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

            try:
                live_tools = await context.tools.list()
                known_tool_slugs = {t.slug for t in live_tools}
            except Exception:
                known_tool_slugs = None
            validation = self._validate(files, context.lang, known_tool_slugs=known_tool_slugs)

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

    @staticmethod
    def _get_last_assistant_message(history: list) -> str:
        """Return the content of the most recent assistant message in history."""
        for msg in reversed(history):
            role = getattr(msg, "role", None)
            role_str = role.value if hasattr(role, "value") else str(role)
            if role_str == "assistant":
                return getattr(msg, "content", "")
        return ""

    @staticmethod
    def _assistant_showed_summary(last_assistant_message: str) -> bool:
        """
        Check whether the assistant's last message was a requirements summary
        asking for user confirmation (Phase 2 → Phase 3 transition).

        Detected by the presence of the summary emoji or typical confirmation
        questions in any language.
        """
        if not last_assistant_message:
            return False
        text = last_assistant_message.lower()
        return (
            "\U0001f4cb" in last_assistant_message  # 📋 emoji
            or "générer l'agent" in text
            or "generer l'agent" in text
            or "generate the agent" in text
            or "should i generate" in text
            or "puis-je générer" in text
            or "puis-je generer" in text
        )

    def _should_enter_generation(
        self, user_msg_count: int, current_message: str,
        edit_mode: bool = False,
        last_assistant_message: str = "",
    ) -> bool:
        """
        Determine whether the conversation should enter generation phase.

        Rules:
        - Always question phase on 1st message (in creation mode)
        - Generation REQUIRES both:
          a) at least _MIN_MESSAGES_FOR_GENERATION user messages, AND
          b) an explicit confirmation keyword in the latest message
        - Keyword matching is **context-aware**:
          • If the assistant already showed a summary (📋), loose matching
            is used (keyword substring in short messages).
          • If no summary was shown yet, only an **exact match** (after
            stripping punctuation) is accepted.  This prevents normal
            answers like "ok je veux un chat" from triggering generation.
        - In edit mode: threshold is lower (_MIN_MESSAGES_FOR_GENERATION_EDIT)
          and any non-trivial message triggers generation immediately

        Even if the LLM ignores the question-phase prompt, the hard block
        in handle_message will prevent file extraction.
        """
        min_msgs = _MIN_MESSAGES_FOR_GENERATION_EDIT if edit_mode else _MIN_MESSAGES_FOR_GENERATION

        if user_msg_count < min_msgs:
            return False

        # In edit mode, always enter generation after min messages
        # (the user describes changes, no need for confirmation keywords)
        if edit_mode:
            return True

        # Require explicit confirmation keyword.
        lower = current_message.lower().strip()

        # Check if the assistant already presented a summary and asked
        # for confirmation.  Only then do we accept loose keyword matching.
        summary_shown = self._assistant_showed_summary(last_assistant_message)

        if summary_shown:
            # Loose matching: keyword anywhere in a short message
            is_short = len(lower) <= 30
            for keyword in _CONFIRMATION_KEYWORDS:
                if is_short and keyword in lower:
                    return True
                if lower == keyword:
                    return True
        else:
            # Strict matching: the message must be essentially just a
            # confirmation keyword (strip surrounding punctuation/whitespace).
            # This prevents "ok je veux un dashboard" from triggering.
            cleaned = re.sub(r"[^\w\s'àâäéèêëïîôùûüÿçœæ-]+", "", lower).strip()
            for keyword in _CONFIRMATION_KEYWORDS:
                if cleaned == keyword:
                    return True

        return False

    # ------------------------------------------------------------------
    # Edit mode helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_edit_mode(message: UserMessage, context: AgentContext) -> str | None:
        """
        Detect if the conversation is in edit mode.

        Checks current message metadata for edit_agent_slug.
        Since sendMessageWrapped in the frontend always includes
        edit_agent_slug in metadata when in edit mode, every message
        in the conversation will carry this flag.
        """
        return (message.metadata or {}).get("edit_agent_slug")

    @staticmethod
    def _load_agent_source(slug: str) -> dict[str, str]:
        """Load source files of an existing agent from the filesystem."""
        files: dict[str, str] = {}

        backend_dir = _AGENTS_ROOT / slug
        frontend_dir = _FRONTEND_AGENTS_ROOT / slug

        file_paths = {
            "backend/manifest.json": backend_dir / "manifest.json",
            "backend/agent.py": backend_dir / "agent.py",
            "backend/prompts/system.md": backend_dir / "prompts" / "system.md",
            "frontend/index.tsx": frontend_dir / "index.tsx",
            "frontend/styles.ts": frontend_dir / "styles.ts",
        }

        for key, path in file_paths.items():
            if path.exists():
                try:
                    files[key] = path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Failed to read {path}: {e}")

        return files

    # ------------------------------------------------------------------
    # Live catalog injection
    # ------------------------------------------------------------------

    @staticmethod
    async def _build_tool_catalog(context: AgentContext) -> str:
        """
        Build a detailed tool catalog from the live registry.

        Includes slug, description, input/output schemas, and examples
        so the LLM knows exactly what each tool can do and never invents
        non-existent tools.
        """
        try:
            tools = await context.tools.list()
        except Exception:
            return "_Could not load tool catalog._"

        if not tools:
            return "_No tools registered._"

        lines = ["### Tools (via context.tools)\n"]
        for tool in sorted(tools, key=lambda t: t.slug):
            lines.append(f"#### `{tool.slug}` — {tool.name}")
            lines.append(f"_{tool.description}_\n")

            if tool.input_schema:
                lines.append("**Input parameters:**")
                for p in tool.input_schema:
                    req = " (REQUIRED)" if p.required else ""
                    desc = f" — {p.description}" if p.description else ""
                    lines.append(f"- `{p.name}` ({p.type}{req}){desc}")
                lines.append("")

            if tool.output_schema:
                lines.append("**Output fields:**")
                for p in tool.output_schema:
                    desc = f" — {p.description}" if p.description else ""
                    lines.append(f"- `{p.name}` ({p.type}){desc}")
                lines.append("")

            if tool.examples:
                lines.append("**Example:**")
                ex = tool.examples[0]
                lines.append(f"```python\nresult = await context.tools.execute(\"{tool.slug}\", {json.dumps(ex.input, ensure_ascii=False)})\n# result.data => {json.dumps(ex.output, ensure_ascii=False)}\n```")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    async def _build_connector_catalog(context: AgentContext) -> str:
        """Build a connector catalog from the live registry."""
        try:
            connectors = await context.connectors.list()
        except Exception:
            return "_Could not load connector catalog._"

        if not connectors:
            return "_No connectors registered._"

        lines = ["### Connectors (via context.connectors)\n"]
        lines.append("| Slug | Description |")
        lines.append("|------|-------------|")
        for conn in connectors:
            slug = getattr(conn, "slug", "?")
            desc = getattr(conn, "description", "")
            lines.append(f"| `{slug}` | {desc} |")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # System prompt management
    # ------------------------------------------------------------------

    def _load_system_prompt(
        self,
        generation_phase: bool = False,
        tool_catalog: str = "",
        connector_catalog: str = "",
        edit_mode: bool = False,
        edit_source_files: dict[str, str] | None = None,
    ) -> str:
        """
        Load the system prompt, optionally truncated for question phase.

        In question phase:
          - Only the conversation flow rules are shown
          - The LLM cannot see file markers, framework spec, or code templates
          - A strong reminder is appended to force question-only behavior

        In generation phase:
          - The full prompt is returned including all framework reference
          - Tool and connector catalogs are injected dynamically from the live registries

        In edit mode:
          - Existing agent source files are injected into the prompt
          - The LLM is instructed to modify the existing code, not create from scratch
        """
        path = Path(__file__).parent / "prompts" / "system.md"
        full_prompt = path.read_text(encoding="utf-8")

        # Inject live catalogs (replace placeholders)
        full_prompt = full_prompt.replace("{{TOOL_CATALOG}}", tool_catalog or "_No tools available._")
        full_prompt = full_prompt.replace("{{CONNECTOR_CATALOG}}", connector_catalog or "_No connectors available._")

        if generation_phase:
            prompt = full_prompt
            # Append an explicit phase status so the LLM knows it must
            # generate files NOW (mirrors the QUESTION PHASE status block).
            prompt += (
                "\n\n---\n\n"
                "## CURRENT STATUS: GENERATION PHASE (Phase 3)\n\n"
                "The user has confirmed the requirements. You are NOW in **Phase 3 — Generate**.\n\n"
                "**Your ONLY task**: generate ALL 5 files immediately using "
                "`<<<FILE:path>>>` … `<<<END_FILE>>>` markers.\n\n"
                "**Do NOT** ask more questions, show another summary, or request confirmation.\n"
                "Start with a brief intro of what you built, then output all 5 files."
            )
            # In edit mode generation phase, append current source files
            if edit_mode and edit_source_files:
                prompt += self._build_edit_mode_prompt(edit_source_files)
            return prompt

        # Question phase: strip everything after the generation marker
        marker_pos = full_prompt.find(_GENERATION_MARKER)
        if marker_pos == -1:
            return full_prompt

        question_prompt = full_prompt[:marker_pos].rstrip()

        if edit_mode:
            # Edit mode question phase: shorter, focused on understanding the change
            question_prompt += (
                "\n\n---\n\n"
                "## CURRENT STATUS: EDIT MODE — UNDERSTANDING CHANGES\n\n"
                "You are editing an **existing agent**. The user will describe what they want to change, fix, or improve.\n\n"
                "Your job right now:\n"
                "1. Read the user's change request carefully\n"
                "2. If the request is clear enough, ask for confirmation to proceed\n"
                "3. If unclear, ask ONE clarifying question about what specifically to change\n"
                "4. Do NOT generate any code, files, or technical output yet\n"
                "5. Do NOT use <<<FILE: markers\n\n"
                "Present a brief summary of the planned changes and ask for confirmation. "
                "The system will then give you the current source files and generation instructions."
            )
        else:
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

    @staticmethod
    def _build_edit_mode_prompt(source_files: dict[str, str]) -> str:
        """Build the edit mode section injected into the system prompt."""
        parts = [
            "\n\n---\n\n"
            "## EDIT MODE — MODIFYING AN EXISTING AGENT\n\n"
            "You are **modifying an existing agent**, NOT creating one from scratch.\n\n"
            "### Rules for edit mode:\n"
            "1. **Read the current source files** below carefully before making changes\n"
            "2. **Only modify what the user requested** — do not refactor unrelated code\n"
            "3. **Preserve the existing structure** — keep the same class names, slug, and overall architecture\n"
            "4. **Output ALL 5 files** even if only some changed — the system replaces all files on deploy\n"
            "5. **Keep the same slug** in manifest.json — changing it would create a new agent instead of updating\n"
            "6. **Increment the patch version** (e.g., 1.0.0 → 1.0.1) to reflect the update\n\n"
            "### Current source files:\n\n"
        ]

        for filepath, content in sorted(source_files.items()):
            parts.append(f"#### `{filepath}`\n```\n{content}\n```\n\n")

        parts.append(
            "### Your task:\n"
            "Apply the user's requested changes to the files above. "
            "Output the complete updated files using <<<FILE:path>>> markers. "
            "Explain what you changed and why.\n"
        )

        return "".join(parts)

    # ------------------------------------------------------------------
    # Conversation building
    # ------------------------------------------------------------------

    def _build_conversation(
        self, history: list, generation_phase: bool,
        edit_slug: str | None = None,
        edit_source_files: dict[str, str] | None = None,
    ) -> str:
        """
        Build the conversation string from history.

        NOTE: the current user message is already in history (saved by
        engine.py before handle_message is called), so we don't re-add it.

        Injects a system reminder during question phase to reinforce behavior.
        In edit mode, injects context about the agent being edited.
        """
        parts: list[str] = []

        # In edit mode, inject context at the start of the conversation
        if edit_slug and edit_source_files:
            parts.append(
                f"[system]: EDIT MODE — The user is modifying the existing agent '{edit_slug}'. "
                f"The current source files have been provided in your instructions. "
                f"Apply the user's requested changes and regenerate all files."
            )

        for msg in history:
            role = getattr(msg, "role", "user")
            # Handle MessageRole enum
            role_str = role.value if hasattr(role, "value") else str(role)
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role_str}]: {content}")

        # Inject a phase-appropriate reminder after the conversation
        if not generation_phase:
            if edit_slug:
                parts.append(
                    f"[system]: REMINDER — You are in EDIT MODE for agent '{edit_slug}'. "
                    "Understand the user's change request. If clear, present a brief summary "
                    "of planned changes and ask for confirmation. "
                    "Do NOT generate code or use <<<FILE: markers yet."
                )
            else:
                parts.append(
                    "[system]: REMINDER — You are in the QUESTION PHASE. "
                    "Ask ONE clarifying question about the user's needs. "
                    "Do NOT generate code, files, or technical output. "
                    "Do NOT use <<<FILE: markers."
                )
        else:
            # GENERATION PHASE: inject an explicit trigger so the LLM
            # knows it must produce files NOW instead of showing yet
            # another summary or asking for confirmation again.
            if edit_slug:
                parts.append(
                    f"[system]: GENERATION PHASE ACTIVATED — The user has confirmed the changes for agent '{edit_slug}'. "
                    "You MUST now generate ALL 5 complete files using <<<FILE:path>>> ... <<<END_FILE>>> markers. "
                    "Do NOT ask any more questions. Do NOT show another summary or ask for confirmation. "
                    "Output a brief intro of what you built, then ALL 5 files immediately."
                )
            else:
                parts.append(
                    "[system]: GENERATION PHASE ACTIVATED — The user has confirmed the requirements. "
                    "You MUST now generate ALL 5 complete files using <<<FILE:path>>> ... <<<END_FILE>>> markers. "
                    "Do NOT ask any more questions. Do NOT show another summary or ask for confirmation. "
                    "Output a brief intro of what you built, then ALL 5 files immediately."
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

    def _validate(
        self,
        files: dict[str, str],
        lang: str = "en",
        known_tool_slugs: set[str] | None = None,
    ) -> dict:
        """
        Validate all generated files for framework compliance.

        Checks security rules, required structure, naming conventions,
        framework contract adherence, and tool/connector existence.
        """
        errors: list[str] = []
        warnings: list[str] = []

        self._validate_manifest(files, errors, lang)
        self._validate_agent_py(files, errors, warnings, lang)
        self._validate_system_md(files, errors, warnings, lang)
        self._validate_frontend(files, errors, lang)

        # Validate that declared tools actually exist in the registry
        if known_tool_slugs is not None:
            self._validate_tool_dependencies(files, errors, known_tool_slugs, lang)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def _validate_tool_dependencies(
        files: dict[str, str],
        errors: list[str],
        known_tool_slugs: set[str],
        lang: str,
    ) -> None:
        """Validate that all declared tool dependencies exist in the live registry."""
        raw = files.get("backend/manifest.json", "")
        if not raw:
            return
        try:
            manifest = json.loads(raw)
        except json.JSONDecodeError:
            return

        declared_tools = manifest.get("dependencies", {}).get("tools", [])
        for tool_slug in declared_tools:
            if tool_slug not in known_tool_slugs:
                errors.append(
                    f"Tool '{tool_slug}' does not exist in the platform registry. "
                    f"Available tools: {', '.join(sorted(known_tool_slugs))}"
                )

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

        # Check for styles import when styles.* is used
        if "styles." in code and "import styles" not in code:
            errors.append(
                t("agent_creator.val.missing_styles_import", lang)
            )

        for forbidden in FORBIDDEN_FRONTEND_IMPORTS:
            if forbidden in code:
                errors.append(
                    t(
                        "agent_creator.val.forbidden_frontend_import",
                        lang,
                        name=forbidden,
                    )
                )
