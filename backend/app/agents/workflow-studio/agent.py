"""
Workflow Studio Agent — Creates N8N workflow automations via natural language.

Interactive workflow:
    1. User describes the automation they want
    2. Clarifying questions are asked (question phase)
    3. Workflow design is confirmed
    4. N8N workflow JSON is generated (generation phase)
    5. Workflow can be published as a NOVA2 agent

The system prompt is split:
  - QUESTION PHASE: LLM only sees conversation rules, NOT JSON format
  - GENERATION PHASE: LLM sees full N8N spec and can output workflow JSON
"""

from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GENERATION_MARKER = "## N8N WORKFLOW JSON FORMAT"

_MIN_MESSAGES_FOR_GENERATION = 3

_CONFIRMATION_KEYWORDS = [
    "ok", "oui", "yes", "go", "génère", "genere", "generate",
    "c'est bon", "c est bon", "parfait", "valide", "lance",
    "fais-le", "fais le", "do it", "let's go", "lets go",
    "confirm", "confirme", "approved", "approuvé",
]

_WORKFLOW_JSON_PATTERN = re.compile(
    r"<<<WORKFLOW_JSON>>>\s*\n(.*?)<<<END_WORKFLOW_JSON>>>",
    re.DOTALL,
)

_PUBLISH_CONFIG_PATTERN = re.compile(
    r"<<<PUBLISH_CONFIG>>>\s*\n(.*?)<<<END_PUBLISH_CONFIG>>>",
    re.DOTALL,
)


class WorkflowStudioAgent(BaseAgent):
    """Creates N8N workflow automations via interactive conversation."""

    @property
    def manifest(self) -> AgentManifest:
        with open(Path(__file__).parent / "manifest.json") as f:
            return AgentManifest(**json.load(f))

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """Process a user message in the workflow creation flow."""
        lang = context.lang

        context.set_progress(10, "Loading workflow studio...")

        # Determine conversation phase
        context.set_progress(20, "Analyzing conversation...")
        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content,
        )
        logger.info(
            f"[workflow-studio] handle_message: history={len(history)} msgs, "
            f"user_count={user_msg_count}, phase={'GENERATION' if in_generation_phase else 'QUESTION'}, "
            f"msg={message.content[:80]!r}"
        )

        # Check if user is importing a workflow JSON directly
        import_json = self._detect_json_import(message.content)
        if import_json:
            return await self._handle_import(import_json, context)

        # Load system prompt
        system_prompt = self._load_system_prompt(generation_phase=in_generation_phase)

        # Build conversation
        conversation = self._build_conversation(history, in_generation_phase)

        context.set_progress(30, "Generating response...")
        llm_response = await context.llm.chat(
            prompt=conversation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=16384,
        )

        context.set_progress(70, "Processing response...")

        # Extract workflow JSON if in generation phase
        metadata: dict = {"phase": "conversation"}

        if in_generation_phase:
            workflow_json = self._extract_workflow_json(llm_response)
            publish_config = self._extract_publish_config(llm_response)

            if workflow_json:
                # Analyze the workflow for UI metadata
                from app.services.n8n_workflows import analyze_workflow
                analysis = analyze_workflow(workflow_json)

                # Store in MinIO
                if context.storage:
                    await context.storage.put(
                        "generated/workflow.json",
                        json.dumps(workflow_json, indent=2).encode("utf-8"),
                        "application/json",
                    )

                metadata = {
                    "phase": "generated",
                    "workflow_json": workflow_json,
                    "publish_config": publish_config,
                    "analysis": analysis.to_dict(),
                }

                # Clean markers from display text
                llm_response = self._clean_display_text(llm_response)
        elif _WORKFLOW_JSON_PATTERN.search(llm_response):
            # LLM tried to generate during question phase — strip it
            llm_response = self._clean_display_text(llm_response)

        context.set_progress(100, "Done")

        usage = context.llm.last_usage
        metadata["tokens_in"] = usage.get("tokens_in", 0)
        metadata["tokens_out"] = usage.get("tokens_out", 0)

        return AgentResponse(content=llm_response, metadata=metadata)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """Streaming version — sends tokens progressively."""
        # Check for JSON import first
        import_json = self._detect_json_import(message.content)
        if import_json:
            response = await self._handle_import(import_json, context)
            yield AgentResponseChunk(
                content=response.content,
                is_final=True,
                metadata=response.metadata,
            )
            return

        history = await context.memory.get_history(limit=50) if context.memory else []
        user_msg_count = self._count_user_messages(history)

        in_generation_phase = self._should_enter_generation(
            user_msg_count, message.content,
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

        # Extract workflow JSON after full response
        metadata: dict = {}
        if in_generation_phase:
            workflow_json = self._extract_workflow_json(accumulated)
            publish_config = self._extract_publish_config(accumulated)

            if workflow_json:
                from app.services.n8n_workflows import analyze_workflow
                analysis = analyze_workflow(workflow_json)

                if context.storage:
                    await context.storage.put(
                        "generated/workflow.json",
                        json.dumps(workflow_json, indent=2).encode("utf-8"),
                        "application/json",
                    )

                metadata = {
                    "phase": "generated",
                    "workflow_json": workflow_json,
                    "publish_config": publish_config,
                    "analysis": analysis.to_dict(),
                }

        yield AgentResponseChunk(content="", is_final=True, metadata=metadata)

    # ------------------------------------------------------------------
    # Import handler
    # ------------------------------------------------------------------

    async def _handle_import(
        self, workflow_json: dict, context: AgentContext,
    ) -> AgentResponse:
        """Handle direct JSON import of a workflow."""
        from app.services.n8n_workflows import analyze_workflow

        analysis = analyze_workflow(workflow_json)
        workflow_name = workflow_json.get("name", "Imported Workflow")

        # Generate a slug from the name
        slug = re.sub(r"[^a-z0-9]+", "-", workflow_name.lower()).strip("-")
        if not slug or len(slug) < 3:
            slug = "imported-workflow"

        publish_config = {
            "name": workflow_name,
            "slug": slug,
            "description": f"Imported N8N workflow: {workflow_name}",
            "icon": "account_tree",
        }

        if context.storage:
            await context.storage.put(
                "generated/workflow.json",
                json.dumps(workflow_json, indent=2).encode("utf-8"),
                "application/json",
            )

        # Build a nice response
        lang = context.lang
        steps_text = "\n".join(
            f"  {s['order']}. **{s['name']}** — {s['description']}"
            for s in analysis.to_dict()["steps"]
        )
        inputs_text = "\n".join(
            f"  - **{i['label']}** ({i['type']})"
            for i in analysis.to_dict()["inputs"]
        ) or "  - None detected"

        content = (
            f"**Workflow imported successfully!**\n\n"
            f"**Name**: {workflow_name}\n"
            f"**Nodes**: {analysis.node_count}\n"
            f"**UI Mode**: {analysis.ui_mode}\n"
            f"**Trigger**: {analysis.trigger_type}\n\n"
            f"**Steps**:\n{steps_text}\n\n"
            f"**Required Inputs**:\n{inputs_text}\n\n"
            f"The workflow is ready to be published as a platform agent. "
            f"Use the **Publish** button to make it available in the catalog."
        )

        return AgentResponse(
            content=content,
            metadata={
                "phase": "generated",
                "workflow_json": workflow_json,
                "publish_config": publish_config,
                "analysis": analysis.to_dict(),
            },
        )

    # ------------------------------------------------------------------
    # Phase detection
    # ------------------------------------------------------------------

    @staticmethod
    def _count_user_messages(history: list) -> int:
        count = 0
        for msg in history:
            role = getattr(msg, "role", None)
            role_str = role.value if hasattr(role, "value") else str(role)
            if role_str == "user":
                count += 1
        return count

    def _should_enter_generation(
        self, user_msg_count: int, current_message: str,
    ) -> bool:
        if user_msg_count < _MIN_MESSAGES_FOR_GENERATION:
            return False

        lower = current_message.lower().strip()
        is_short = len(lower) <= 30
        for keyword in _CONFIRMATION_KEYWORDS:
            if is_short and keyword in lower:
                return True
            if lower == keyword:
                return True
        return False

    @staticmethod
    def _detect_json_import(content: str) -> dict | None:
        """Detect if the user pasted a valid N8N workflow JSON."""
        content = content.strip()
        # Quick check for JSON-like content
        if not (content.startswith("{") and content.endswith("}")):
            return None
        try:
            data = json.loads(content)
            # Must have nodes to be an N8N workflow
            if isinstance(data, dict) and "nodes" in data:
                return data
        except json.JSONDecodeError:
            pass
        return None

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _load_system_prompt(self, generation_phase: bool = False) -> str:
        path = Path(__file__).parent / "prompts" / "system.md"
        full_prompt = path.read_text(encoding="utf-8")

        if generation_phase:
            prompt = full_prompt
            prompt += (
                "\n\n---\n\n"
                "## CURRENT STATUS: GENERATION PHASE\n\n"
                "The user has confirmed the workflow design. You are NOW in the generation phase.\n\n"
                "**Your ONLY task**: generate the complete N8N workflow JSON immediately using "
                "`<<<WORKFLOW_JSON>>>` ... `<<<END_WORKFLOW_JSON>>>` markers, "
                "followed by the publish config using "
                "`<<<PUBLISH_CONFIG>>>` ... `<<<END_PUBLISH_CONFIG>>>` markers.\n\n"
                "**Do NOT** ask more questions or request confirmation.\n"
                "Start with a brief intro, then output the workflow JSON and publish config."
            )
            return prompt

        # Question phase: strip the JSON format section
        marker_pos = full_prompt.find(_GENERATION_MARKER)
        if marker_pos == -1:
            return full_prompt

        question_prompt = full_prompt[:marker_pos].rstrip()
        question_prompt += (
            "\n\n---\n\n"
            "## CURRENT STATUS: QUESTION PHASE\n\n"
            "You are in the **QUESTION PHASE**. Your ONLY job right now:\n"
            "1. Read the user's message\n"
            "2. Ask ONE clarifying question about their automation needs\n"
            "3. Do NOT generate JSON, workflow code, or technical output\n"
            "4. Do NOT use <<<WORKFLOW_JSON>>> markers\n"
            "5. Keep your response conversational and focused\n\n"
            "Once you have enough information, present a structured workflow design summary "
            "and ask for confirmation."
        )
        return question_prompt

    # ------------------------------------------------------------------
    # Conversation building
    # ------------------------------------------------------------------

    def _build_conversation(self, history: list, generation_phase: bool) -> str:
        parts: list[str] = []

        for msg in history:
            role = getattr(msg, "role", "user")
            role_str = role.value if hasattr(role, "value") else str(role)
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role_str}]: {content}")

        if not generation_phase:
            parts.append(
                "[system]: REMINDER — You are in the QUESTION PHASE. "
                "Ask ONE clarifying question about the automation needs. "
                "Do NOT generate JSON or workflow code."
            )
        else:
            parts.append(
                "[system]: GENERATION PHASE ACTIVATED — The user has confirmed. "
                "You MUST now generate the complete N8N workflow JSON using "
                "<<<WORKFLOW_JSON>>> ... <<<END_WORKFLOW_JSON>>> markers, "
                "and the publish config using "
                "<<<PUBLISH_CONFIG>>> ... <<<END_PUBLISH_CONFIG>>> markers. "
                "Do NOT ask any more questions."
            )

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Extraction & cleaning
    # ------------------------------------------------------------------

    def _extract_workflow_json(self, text: str) -> dict | None:
        match = _WORKFLOW_JSON_PATTERN.search(text)
        if not match:
            return None
        raw = match.group(1).strip()
        # Remove markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse workflow JSON: {raw[:200]}")
            return None

    def _extract_publish_config(self, text: str) -> dict | None:
        match = _PUBLISH_CONFIG_PATTERN.search(text)
        if not match:
            return None
        raw = match.group(1).strip()
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _clean_display_text(self, text: str) -> str:
        """Remove JSON markers from display, keeping the human-readable parts."""
        text = _WORKFLOW_JSON_PATTERN.sub("[Workflow JSON generated]", text)
        text = _PUBLISH_CONFIG_PATTERN.sub("[Publication config generated]", text)
        return text.strip()
