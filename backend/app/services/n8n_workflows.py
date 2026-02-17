"""
N8N Workflow Service — Analyzes, imports, and manages N8N workflows.

Core responsibilities:
- Analyze N8N workflow JSON to extract UI metadata (inputs, steps, human validations)
- Convert workflow analysis into dynamic UI specifications
- Manage workflow lifecycle (import, publish as agent, execute)
- Bridge between N8N API and NOVA2 agent system
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# N8N node type classifications
# ---------------------------------------------------------------------------

# Nodes that require user input
INPUT_NODE_TYPES = {
    "n8n-nodes-base.manualTrigger": "trigger",
    "n8n-nodes-base.webhook": "webhook",
    "n8n-nodes-base.formTrigger": "form",
    "n8n-nodes-base.chatTrigger": "chat",
    "@n8n/n8n-nodes-langchain.chatTrigger": "chat",
}

# Nodes that require files
FILE_NODE_TYPES = {
    "n8n-nodes-base.readBinaryFiles",
    "n8n-nodes-base.readBinaryFile",
    "n8n-nodes-base.spreadsheetFile",
    "n8n-nodes-base.convertToFile",
    "n8n-nodes-base.extractFromFile",
}

# Nodes that pause for human validation
HUMAN_VALIDATION_TYPES = {
    "n8n-nodes-base.wait",
    "n8n-nodes-base.form",
    "n8n-nodes-base.formTrigger",
}

# AI/LLM-related nodes
AI_NODE_TYPES = {
    "n8n-nodes-base.openAi",
    "@n8n/n8n-nodes-langchain.openAi",
    "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "@n8n/n8n-nodes-langchain.lmChatAnthropic",
    "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
    "@n8n/n8n-nodes-langchain.agent",
    "@n8n/n8n-nodes-langchain.chainLlm",
    "@n8n/n8n-nodes-langchain.chainSummarization",
    "@n8n/n8n-nodes-langchain.chainRetrievalQa",
}

# Output-producing nodes
OUTPUT_NODE_TYPES = {
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.sendEmail",
    "n8n-nodes-base.slack",
    "n8n-nodes-base.telegram",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.writeBinaryFile",
}

# Categories for node classification
NODE_CATEGORIES = {
    "trigger": {"n8n-nodes-base.manualTrigger", "n8n-nodes-base.webhook", "n8n-nodes-base.formTrigger", "n8n-nodes-base.chatTrigger", "@n8n/n8n-nodes-langchain.chatTrigger", "n8n-nodes-base.scheduleTrigger", "n8n-nodes-base.cronTrigger"},
    "input": FILE_NODE_TYPES,
    "processing": {"n8n-nodes-base.code", "n8n-nodes-base.function", "n8n-nodes-base.functionItem", "n8n-nodes-base.set", "n8n-nodes-base.merge", "n8n-nodes-base.splitInBatches", "n8n-nodes-base.filter", "n8n-nodes-base.if", "n8n-nodes-base.switch"},
    "ai": AI_NODE_TYPES,
    "output": OUTPUT_NODE_TYPES,
    "validation": HUMAN_VALIDATION_TYPES,
}


# ---------------------------------------------------------------------------
# Workflow analysis types
# ---------------------------------------------------------------------------

class WorkflowInput:
    """Represents a required user input for a workflow."""

    def __init__(
        self,
        name: str,
        input_type: str,
        label: str,
        description: str = "",
        required: bool = True,
        default: Any = None,
        options: list[str] | None = None,
    ):
        self.name = name
        self.input_type = input_type  # text, textarea, file, number, boolean, select, prompt
        self.label = label
        self.description = description
        self.required = required
        self.default = default
        self.options = options

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "type": self.input_type,
            "label": self.label,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            d["default"] = self.default
        if self.options:
            d["options"] = self.options
        return d


class WorkflowStep:
    """Represents a visible step in the workflow execution."""

    def __init__(
        self,
        order: int,
        name: str,
        node_type: str,
        category: str,
        description: str = "",
        requires_human: bool = False,
        icon: str = "settings",
    ):
        self.order = order
        self.name = name
        self.node_type = node_type
        self.category = category
        self.description = description
        self.requires_human = requires_human
        self.icon = icon

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "name": self.name,
            "node_type": self.node_type,
            "category": self.category,
            "description": self.description,
            "requires_human": self.requires_human,
            "icon": self.icon,
        }


class WorkflowAnalysis:
    """Complete analysis of an N8N workflow for UI generation."""

    def __init__(self):
        self.trigger_type: str = "manual"  # manual, webhook, form, chat, schedule
        self.inputs: list[WorkflowInput] = []
        self.steps: list[WorkflowStep] = []
        self.has_human_validation: bool = False
        self.has_file_upload: bool = False
        self.has_file_output: bool = False
        self.has_ai: bool = False
        self.has_chat: bool = False
        self.node_count: int = 0
        self.ui_mode: str = "form"  # form, chat, pipeline, simple
        self.output_type: str = "text"  # text, file, email, message, api_response

    def to_dict(self) -> dict:
        return {
            "trigger_type": self.trigger_type,
            "inputs": [i.to_dict() for i in self.inputs],
            "steps": [s.to_dict() for s in self.steps],
            "has_human_validation": self.has_human_validation,
            "has_file_upload": self.has_file_upload,
            "has_file_output": self.has_file_output,
            "has_ai": self.has_ai,
            "has_chat": self.has_chat,
            "node_count": self.node_count,
            "ui_mode": self.ui_mode,
            "output_type": self.output_type,
        }


# ---------------------------------------------------------------------------
# Core service functions
# ---------------------------------------------------------------------------

def analyze_workflow(workflow_json: dict) -> WorkflowAnalysis:
    """
    Analyze an N8N workflow JSON to extract UI-relevant metadata.

    This is the core intelligence that powers dynamic UI generation.
    It inspects every node, understands connections, and determines:
    - What inputs the user needs to provide
    - What steps are visible in the execution pipeline
    - Whether human validation checkpoints exist
    - What kind of UI best fits this workflow (form, chat, pipeline)
    """
    analysis = WorkflowAnalysis()
    nodes = workflow_json.get("nodes", [])
    connections = workflow_json.get("connections", {})
    analysis.node_count = len(nodes)

    if not nodes:
        return analysis

    # Sort nodes by position (left to right = execution order approximation)
    sorted_nodes = sorted(nodes, key=lambda n: n.get("position", [0, 0])[0])

    step_order = 0
    for node in sorted_nodes:
        node_type = node.get("type", "")
        node_name = node.get("name", "Unknown")
        params = node.get("parameters", {})

        # --- Detect trigger type ---
        if node_type in INPUT_NODE_TYPES:
            analysis.trigger_type = INPUT_NODE_TYPES[node_type]

        # --- Detect chat mode ---
        if node_type in ("n8n-nodes-base.chatTrigger", "@n8n/n8n-nodes-langchain.chatTrigger"):
            analysis.has_chat = True
            analysis.inputs.append(WorkflowInput(
                name="chat_message",
                input_type="prompt",
                label="Message",
                description="Enter your message",
                required=True,
            ))

        # --- Detect webhook inputs ---
        elif node_type == "n8n-nodes-base.webhook":
            _extract_webhook_inputs(node, params, analysis)

        # --- Detect form inputs ---
        elif node_type == "n8n-nodes-base.formTrigger":
            _extract_form_inputs(node, params, analysis)
            analysis.has_human_validation = True

        # --- Detect manual trigger ---
        elif node_type == "n8n-nodes-base.manualTrigger":
            # Check if downstream nodes need data — if so, add a generic input
            if _has_downstream_data_usage(node_name, connections, nodes):
                analysis.inputs.append(WorkflowInput(
                    name="input_data",
                    input_type="textarea",
                    label="Input Data",
                    description="Provide the data for this workflow",
                    required=False,
                ))

        # --- Detect file requirements ---
        if node_type in FILE_NODE_TYPES:
            analysis.has_file_upload = True
            # Only add file input if not already present
            if not any(i.input_type == "file" for i in analysis.inputs):
                analysis.inputs.append(WorkflowInput(
                    name="file_upload",
                    input_type="file",
                    label="Upload File",
                    description="Upload a file for processing",
                    required=True,
                ))

        # --- Detect human validation nodes ---
        if node_type in HUMAN_VALIDATION_TYPES and node_type != "n8n-nodes-base.formTrigger":
            analysis.has_human_validation = True

        # --- Detect AI nodes ---
        if node_type in AI_NODE_TYPES:
            analysis.has_ai = True
            # Check if it expects a user prompt
            prompt_param = params.get("prompt", params.get("text", params.get("messages", "")))
            if prompt_param and "{{" in str(prompt_param):
                if not analysis.has_chat and not any(i.input_type == "prompt" for i in analysis.inputs):
                    analysis.inputs.append(WorkflowInput(
                        name="prompt",
                        input_type="prompt",
                        label="Prompt",
                        description="Enter your request",
                        required=True,
                    ))

        # --- Detect file output ---
        if node_type in ("n8n-nodes-base.writeBinaryFile", "n8n-nodes-base.convertToFile"):
            analysis.has_file_output = True

        # --- Build step list (skip trigger nodes for cleaner UI) ---
        category = _categorize_node(node_type)
        if category != "trigger":
            step_order += 1
            analysis.steps.append(WorkflowStep(
                order=step_order,
                name=node_name,
                node_type=node_type,
                category=category,
                description=_describe_node(node_type, node_name, params),
                requires_human=node_type in HUMAN_VALIDATION_TYPES,
                icon=_node_icon(category),
            ))

    # --- Determine output type ---
    analysis.output_type = _determine_output_type(nodes)

    # --- Determine UI mode ---
    analysis.ui_mode = _determine_ui_mode(analysis)

    # --- If no inputs detected but workflow needs data, add generic input ---
    if not analysis.inputs and analysis.trigger_type == "manual":
        analysis.inputs.append(WorkflowInput(
            name="input_text",
            input_type="textarea",
            label="Input",
            description="Provide input for this workflow",
            required=False,
        ))

    return analysis


def _extract_webhook_inputs(node: dict, params: dict, analysis: WorkflowAnalysis):
    """Extract expected inputs from a webhook node's configuration."""
    http_method = params.get("httpMethod", "POST")
    if http_method in ("POST", "PUT", "PATCH"):
        # Check for defined request body parameters
        body_params = params.get("options", {}).get("requestBody", {})
        if body_params:
            for bp in body_params if isinstance(body_params, list) else [body_params]:
                analysis.inputs.append(WorkflowInput(
                    name=bp.get("name", "data"),
                    input_type="textarea",
                    label=bp.get("name", "Request Data"),
                    description=bp.get("description", ""),
                    required=bp.get("required", True),
                ))
        else:
            analysis.inputs.append(WorkflowInput(
                name="webhook_data",
                input_type="textarea",
                label="Data",
                description="JSON data to send to the workflow",
                required=True,
            ))


def _extract_form_inputs(node: dict, params: dict, analysis: WorkflowAnalysis):
    """Extract form fields from a form trigger node."""
    form_fields = params.get("formFields", {}).get("values", [])
    for field in form_fields:
        field_type = field.get("fieldType", "text")
        input_type_map = {
            "text": "text",
            "textarea": "textarea",
            "number": "number",
            "email": "text",
            "password": "text",
            "date": "text",
            "dropdown": "select",
            "file": "file",
        }
        wf_input = WorkflowInput(
            name=field.get("fieldLabel", "field").lower().replace(" ", "_"),
            input_type=input_type_map.get(field_type, "text"),
            label=field.get("fieldLabel", "Field"),
            description=field.get("fieldDescription", ""),
            required=field.get("requiredField", False),
        )
        if field_type == "dropdown":
            wf_input.options = [
                opt.get("option", opt.get("value", ""))
                for opt in field.get("fieldOptions", {}).get("values", [])
            ]
        analysis.inputs.append(wf_input)


def _has_downstream_data_usage(trigger_name: str, connections: dict, nodes: list) -> bool:
    """Check if any node downstream of the trigger uses expression data."""
    connected = connections.get(trigger_name, {})
    if not connected:
        return False
    for node in nodes:
        params_str = json.dumps(node.get("parameters", {}))
        if "{{" in params_str or "$json" in params_str or "$input" in params_str:
            return True
    return False


def _categorize_node(node_type: str) -> str:
    """Classify a node into a UI-friendly category."""
    for category, type_set in NODE_CATEGORIES.items():
        if node_type in type_set:
            return category
    if "langchain" in node_type.lower():
        return "ai"
    return "processing"


def _describe_node(node_type: str, name: str, params: dict) -> str:
    """Generate a human-readable description for a node."""
    type_short = node_type.split(".")[-1] if "." in node_type else node_type
    descriptions = {
        "code": "Execute custom code",
        "function": "Run JavaScript function",
        "set": "Transform data",
        "merge": "Merge data streams",
        "if": "Conditional branching",
        "switch": "Multi-path routing",
        "filter": "Filter data",
        "httpRequest": "HTTP API call",
        "openAi": "AI processing (OpenAI)",
        "agent": "AI Agent execution",
        "chainLlm": "LLM Chain processing",
        "chainSummarization": "AI Summarization",
        "sendEmail": "Send email",
        "slack": "Send to Slack",
        "telegram": "Send to Telegram",
        "respondToWebhook": "Return response",
        "wait": "Wait for approval",
        "form": "User form input",
        "spreadsheetFile": "Process spreadsheet",
        "readBinaryFile": "Read file",
        "writeBinaryFile": "Write file",
        "splitInBatches": "Batch processing",
    }
    return descriptions.get(type_short, f"Process: {name}")


def _node_icon(category: str) -> str:
    """Return a Material Icon name for a node category."""
    icons = {
        "trigger": "play_circle",
        "input": "upload_file",
        "processing": "settings",
        "ai": "psychology",
        "output": "output",
        "validation": "verified_user",
    }
    return icons.get(category, "settings")


def _determine_output_type(nodes: list) -> str:
    """Determine the primary output type of the workflow."""
    for node in reversed(nodes):
        node_type = node.get("type", "")
        if "respondToWebhook" in node_type:
            return "api_response"
        if "sendEmail" in node_type:
            return "email"
        if "slack" in node_type or "telegram" in node_type:
            return "message"
        if "writeBinaryFile" in node_type or "convertToFile" in node_type:
            return "file"
    return "text"


def _determine_ui_mode(analysis: WorkflowAnalysis) -> str:
    """
    Determine the best UI mode for this workflow.

    - chat: Has a chat trigger or AI chat interaction
    - form: Has form inputs or webhook with defined parameters
    - pipeline: Has multiple steps with human validation
    - simple: Basic trigger-and-run workflow
    """
    if analysis.has_chat:
        return "chat"
    if analysis.has_human_validation and len(analysis.steps) > 3:
        return "pipeline"
    if len(analysis.inputs) > 0:
        return "form"
    return "simple"


# ---------------------------------------------------------------------------
# N8N API client helper — auto-setup + API key auth
# ---------------------------------------------------------------------------

# Cached API key (populated by auto-setup, manual setup, or settings)
_n8n_api_key: str = ""

# Default credentials for auto-created N8N owner
_N8N_OWNER_EMAIL = "nova2@platform.local"
_N8N_OWNER_PASSWORD = "Nova2Admin!2024"
_N8N_OWNER_FIRST = "NOVA2"
_N8N_OWNER_LAST = "Platform"

_setup_attempted: bool = False


def _extract_api_key(data: dict) -> str:
    """Extract the API key string from various N8N response formats."""
    if isinstance(data, dict):
        return (
            data.get("apiKey")
            or data.get("rawApiKey")
            or data.get("data", {}).get("apiKey", "")
            or data.get("data", {}).get("rawApiKey", "")
        )
    return ""


async def _login_and_create_key(
    client: httpx.AsyncClient, email: str, password: str,
) -> str:
    """Login to N8N and create/retrieve an API key. Returns the key or ''."""
    login_resp = await client.post(
        "/api/v1/login",
        json={"email": email, "password": password},
    )
    if login_resp.status_code != 200:
        return ""

    cookies = login_resp.cookies

    # Try creating a new API key
    create_resp = await client.post("/api/v1/me/api-keys", cookies=cookies)
    if create_resp.status_code in (200, 201):
        key = _extract_api_key(create_resp.json())
        if key:
            return key

    # Fallback: list existing keys
    list_resp = await client.get("/api/v1/me/api-keys", cookies=cookies)
    if list_resp.status_code == 200:
        keys_data = list_resp.json()
        keys = keys_data.get("data", keys_data) if isinstance(keys_data, dict) else keys_data
        if isinstance(keys, list) and keys:
            key = _extract_api_key(keys[0])
            if key:
                return key

    return ""


async def _auto_setup_n8n() -> str:
    """
    Attempt automatic N8N setup: create owner → login → generate API key.

    Returns the API key on success, empty string on failure.
    """
    global _setup_attempted
    _setup_attempted = True

    base_url = settings.N8N_BASE_URL.rstrip("/")
    logger.info("N8N API key not configured — attempting auto-setup...")

    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
        ) as client:
            # Step 1: Try to create the owner (only works on fresh N8N)
            try:
                setup_resp = await client.post(
                    "/api/v1/owner/setup",
                    json={
                        "email": _N8N_OWNER_EMAIL,
                        "password": _N8N_OWNER_PASSWORD,
                        "firstName": _N8N_OWNER_FIRST,
                        "lastName": _N8N_OWNER_LAST,
                    },
                )
                if setup_resp.status_code in (200, 201):
                    logger.info("N8N owner created via auto-setup")
                else:
                    logger.debug(
                        f"N8N owner setup returned {setup_resp.status_code} "
                        "(instance already configured)"
                    )
            except Exception as e:
                logger.debug(f"N8N owner setup skipped: {e}")

            # Step 2: Login and create API key
            key = await _login_and_create_key(
                client, _N8N_OWNER_EMAIL, _N8N_OWNER_PASSWORD,
            )
            if key:
                logger.info("N8N API key auto-generated successfully")
                return key

            logger.warning(
                "N8N auto-setup failed — instance was likely configured "
                "manually. Use POST /api/n8n/setup to provide credentials."
            )
    except httpx.ConnectError:
        logger.error("Cannot connect to N8N at %s", base_url)
    except Exception as e:
        logger.error("N8N auto-setup error: %s", e)

    return ""


async def setup_n8n_with_credentials(email: str, password: str) -> str:
    """
    Manual setup: login with user-provided N8N credentials and generate
    an API key. Called from the /api/n8n/setup endpoint.

    Returns the (masked) API key on success, raises RuntimeError on failure.
    """
    global _n8n_api_key

    base_url = settings.N8N_BASE_URL.rstrip("/")

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(30.0, connect=10.0),
    ) as client:
        key = await _login_and_create_key(client, email, password)

    if not key:
        raise RuntimeError(
            "N8N login failed. Check your email/password "
            "and make sure the N8N instance is running."
        )

    _n8n_api_key = key
    logger.info("N8N API key configured via manual setup")
    return f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"


async def _ensure_n8n_api_key() -> str:
    """
    Ensure we have a valid N8N API key.

    Priority:
    1. N8N_API_KEY env var
    2. Cached key from previous setup
    3. Auto-setup (create owner → login → key)
    """
    global _n8n_api_key

    # 1. From env
    if settings.N8N_API_KEY:
        return settings.N8N_API_KEY

    # 2. Cached
    if _n8n_api_key:
        return _n8n_api_key

    # 3. Auto-setup (try once)
    if not _setup_attempted:
        key = await _auto_setup_n8n()
        if key:
            _n8n_api_key = key
            return _n8n_api_key

    raise RuntimeError(
        "N8N API key not configured. Either:\n"
        "  1. Open N8N, go to Settings > API, create a key, "
        "and set N8N_API_KEY env var\n"
        "  2. Use POST /api/n8n/setup with your N8N email/password"
    )


async def get_n8n_client() -> httpx.AsyncClient:
    """Create an authenticated httpx client for N8N API."""
    api_key = await _ensure_n8n_api_key()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return httpx.AsyncClient(
        base_url=settings.N8N_BASE_URL.rstrip("/"),
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers=headers,
    )


async def list_n8n_workflows() -> list[dict]:
    """List all workflows from N8N."""
    async with await get_n8n_client() as client:
        resp = await client.get("/api/v1/workflows")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data


async def get_n8n_workflow(workflow_id: str) -> dict:
    """Get a specific workflow from N8N."""
    async with await get_n8n_client() as client:
        resp = await client.get(f"/api/v1/workflows/{workflow_id}")
        resp.raise_for_status()
        return resp.json()


async def create_n8n_workflow(workflow_json: dict) -> dict:
    """Create a new workflow in N8N."""
    async with await get_n8n_client() as client:
        resp = await client.post("/api/v1/workflows", json=workflow_json)
        resp.raise_for_status()
        return resp.json()


async def execute_n8n_workflow(workflow_id: str, input_data: dict | None = None) -> dict:
    """Execute a workflow in N8N and return results."""
    async with await get_n8n_client() as client:
        payload = {}
        if input_data:
            payload["data"] = input_data
        resp = await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def get_n8n_execution(execution_id: str) -> dict:
    """Get execution status and results."""
    async with await get_n8n_client() as client:
        resp = await client.get(f"/api/v1/executions/{execution_id}")
        resp.raise_for_status()
        return resp.json()


async def check_n8n_health() -> bool:
    """Check if N8N is reachable."""
    try:
        async with await get_n8n_client() as client:
            resp = await client.get("/healthz")
            return resp.status_code == 200
    except Exception:
        return False


def generate_agent_config_from_analysis(
    analysis: WorkflowAnalysis,
    workflow_id: str,
    workflow_name: str,
) -> dict:
    """
    Generate a NOVA2 agent config dict from a workflow analysis.

    This config is stored in Agent.config and used by the dynamic UI
    renderer to build the appropriate interface for each workflow agent.
    """
    return {
        "n8n_workflow_id": workflow_id,
        "n8n_workflow_name": workflow_name,
        "workflow_analysis": analysis.to_dict(),
        "ui_mode": analysis.ui_mode,
        "icon": _agent_icon_from_analysis(analysis),
        "category": _agent_category_from_analysis(analysis),
        "tags": _agent_tags_from_analysis(analysis),
    }


def _agent_icon_from_analysis(analysis: WorkflowAnalysis) -> str:
    """Choose the best icon for the agent based on workflow content."""
    if analysis.has_chat:
        return "chat"
    if analysis.has_ai:
        return "psychology"
    if analysis.has_file_upload:
        return "upload_file"
    if analysis.has_human_validation:
        return "verified_user"
    return "account_tree"


def _agent_category_from_analysis(analysis: WorkflowAnalysis) -> str:
    """Determine agent category from workflow analysis."""
    if analysis.has_ai:
        return "ai"
    if analysis.has_chat:
        return "conversational"
    return "automation"


def _agent_tags_from_analysis(analysis: WorkflowAnalysis) -> list[str]:
    """Generate tags from workflow analysis."""
    tags = ["n8n", "workflow"]
    if analysis.has_ai:
        tags.append("ai")
    if analysis.has_chat:
        tags.append("chat")
    if analysis.has_file_upload:
        tags.append("file-processing")
    if analysis.has_human_validation:
        tags.append("human-in-the-loop")
    return tags
