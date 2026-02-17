"""
N8N Connector — Communicates with the embedded N8N instance.

Provides actions for:
- Listing workflows
- Getting workflow details (with node analysis)
- Creating/updating workflows
- Executing workflows and polling results
- Importing/exporting workflow JSON

Authentication uses N8N's REST API key (X-N8N-API-KEY header).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.framework.base.connector import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)

logger = logging.getLogger(__name__)


class N8NConnector(BaseConnector):
    """Platform connector for the embedded N8N automation engine."""

    slug = "n8n"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._base_url: str = ""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="n8n",
            name="N8N Workflow Engine",
            description="Native integration with the embedded N8N open-source workflow automation engine",
            version="1.0.0",
            category="automation",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="base_url", type="string", description="N8N base URL", required=True),
                ToolParameter(name="api_key", type="string", description="N8N REST API key", required=True),
            ],
            actions=[
                ConnectorAction(
                    name="list_workflows",
                    description="List all workflows in N8N",
                    input_schema=[],
                    output_schema=[
                        ToolParameter(name="workflows", type="array", description="List of workflow summaries"),
                    ],
                ),
                ConnectorAction(
                    name="get_workflow",
                    description="Get a workflow by ID with full node details",
                    input_schema=[
                        ToolParameter(name="workflow_id", type="string", description="N8N workflow ID", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="workflow", type="object", description="Full workflow JSON"),
                    ],
                ),
                ConnectorAction(
                    name="create_workflow",
                    description="Create a new workflow in N8N",
                    input_schema=[
                        ToolParameter(name="workflow_json", type="object", description="N8N workflow JSON", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="workflow", type="object", description="Created workflow"),
                    ],
                ),
                ConnectorAction(
                    name="update_workflow",
                    description="Update an existing workflow in N8N",
                    input_schema=[
                        ToolParameter(name="workflow_id", type="string", description="N8N workflow ID", required=True),
                        ToolParameter(name="workflow_json", type="object", description="Updated workflow JSON", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="workflow", type="object", description="Updated workflow"),
                    ],
                ),
                ConnectorAction(
                    name="execute_workflow",
                    description="Execute a workflow and return results",
                    input_schema=[
                        ToolParameter(name="workflow_id", type="string", description="N8N workflow ID", required=True),
                        ToolParameter(name="input_data", type="object", description="Input data for the workflow"),
                    ],
                    output_schema=[
                        ToolParameter(name="execution", type="object", description="Execution result"),
                    ],
                ),
                ConnectorAction(
                    name="get_execution",
                    description="Get execution details and status",
                    input_schema=[
                        ToolParameter(name="execution_id", type="string", description="Execution ID", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="execution", type="object", description="Execution details"),
                    ],
                ),
                ConnectorAction(
                    name="activate_workflow",
                    description="Activate or deactivate a workflow",
                    input_schema=[
                        ToolParameter(name="workflow_id", type="string", description="N8N workflow ID", required=True),
                        ToolParameter(name="active", type="boolean", description="Activate (true) or deactivate (false)", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="workflow", type="object", description="Updated workflow"),
                    ],
                ),
                ConnectorAction(
                    name="delete_workflow",
                    description="Delete a workflow from N8N",
                    input_schema=[
                        ToolParameter(name="workflow_id", type="string", description="N8N workflow ID", required=True),
                    ],
                    output_schema=[],
                ),
            ],
            tags=["automation", "workflow", "n8n", "no-code"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialize HTTP client with API key auth."""
        self._base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["X-N8N-API-KEY"] = api_key

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers,
        )

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if N8N is reachable."""
        if not self._client:
            return False
        try:
            resp = await self._client.get("/healthz")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        """Execute an N8N connector action."""
        if not self._client:
            return self.error(
                "N8N connector not connected",
                ConnectorErrorCode.NOT_CONNECTED,
            )

        handler = {
            "list_workflows": self._list_workflows,
            "get_workflow": self._get_workflow,
            "create_workflow": self._create_workflow,
            "update_workflow": self._update_workflow,
            "execute_workflow": self._execute_workflow,
            "get_execution": self._get_execution,
            "activate_workflow": self._activate_workflow,
            "delete_workflow": self._delete_workflow,
        }.get(action)

        if not handler:
            return self.error(
                f"Unknown action: {action}",
                ConnectorErrorCode.INVALID_ACTION,
            )

        try:
            return await handler(params)
        except httpx.HTTPStatusError as e:
            logger.error(f"N8N API error: {e.response.status_code} - {e.response.text}")
            return self.error(
                f"N8N API error: {e.response.status_code}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except httpx.ConnectError:
            return self.error(
                "Cannot connect to N8N",
                ConnectorErrorCode.CONNECTION_FAILED,
            )
        except Exception as e:
            logger.exception(f"N8N connector error: {e}")
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _list_workflows(self, params: dict) -> ConnectorResult:
        resp = await self._client.get("/api/v1/workflows")
        resp.raise_for_status()
        data = resp.json()
        workflows = data.get("data", data) if isinstance(data, dict) else data
        return self.success({"workflows": workflows})

    async def _get_workflow(self, params: dict) -> ConnectorResult:
        wf_id = params["workflow_id"]
        resp = await self._client.get(f"/api/v1/workflows/{wf_id}")
        resp.raise_for_status()
        return self.success({"workflow": resp.json()})

    async def _create_workflow(self, params: dict) -> ConnectorResult:
        workflow_json = params["workflow_json"]
        if isinstance(workflow_json, str):
            workflow_json = json.loads(workflow_json)
        resp = await self._client.post("/api/v1/workflows", json=workflow_json)
        resp.raise_for_status()
        return self.success({"workflow": resp.json()})

    async def _update_workflow(self, params: dict) -> ConnectorResult:
        wf_id = params["workflow_id"]
        workflow_json = params["workflow_json"]
        if isinstance(workflow_json, str):
            workflow_json = json.loads(workflow_json)
        resp = await self._client.put(f"/api/v1/workflows/{wf_id}", json=workflow_json)
        resp.raise_for_status()
        return self.success({"workflow": resp.json()})

    async def _execute_workflow(self, params: dict) -> ConnectorResult:
        wf_id = params["workflow_id"]
        input_data = params.get("input_data", {})
        resp = await self._client.post(
            f"/api/v1/workflows/{wf_id}/execute",
            json={"data": input_data} if input_data else {},
        )
        resp.raise_for_status()
        return self.success({"execution": resp.json()})

    async def _get_execution(self, params: dict) -> ConnectorResult:
        exec_id = params["execution_id"]
        resp = await self._client.get(f"/api/v1/executions/{exec_id}")
        resp.raise_for_status()
        return self.success({"execution": resp.json()})

    async def _activate_workflow(self, params: dict) -> ConnectorResult:
        wf_id = params["workflow_id"]
        active = params["active"]
        resp = await self._client.patch(
            f"/api/v1/workflows/{wf_id}",
            json={"active": active},
        )
        resp.raise_for_status()
        return self.success({"workflow": resp.json()})

    async def _delete_workflow(self, params: dict) -> ConnectorResult:
        wf_id = params["workflow_id"]
        resp = await self._client.delete(f"/api/v1/workflows/{wf_id}")
        resp.raise_for_status()
        return self.success({})
