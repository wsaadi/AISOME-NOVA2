"""
N8N Workflows API — Manage N8N workflows and publish them as NOVA2 agents.

Endpoints:
- GET  /api/n8n/health          — Check N8N connectivity
- GET  /api/n8n/workflows       — List all N8N workflows
- GET  /api/n8n/workflows/{id}  — Get workflow details + analysis
- POST /api/n8n/workflows       — Create workflow in N8N (from JSON or natural language)
- POST /api/n8n/workflows/import — Import workflow JSON into N8N
- POST /api/n8n/workflows/{id}/analyze  — Analyze workflow for UI generation
- POST /api/n8n/workflows/{id}/execute  — Execute workflow with input data
- GET  /api/n8n/executions/{id} — Get execution status
- POST /api/n8n/workflows/{id}/publish  — Publish workflow as NOVA2 agent
"""

import json
import logging
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_permission
from app.models.agent import Agent, AgentPermission
from app.models.user import User
from app.services.n8n_workflows import (
    analyze_workflow,
    check_n8n_health,
    create_n8n_workflow,
    execute_n8n_workflow,
    generate_agent_config_from_analysis,
    get_n8n_execution,
    get_n8n_workflow,
    list_n8n_workflows,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/n8n", tags=["N8N Workflows"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class WorkflowCreateRequest(BaseModel):
    """Create a workflow in N8N from raw JSON."""
    workflow_json: dict


class WorkflowExecuteRequest(BaseModel):
    """Execute a workflow with optional input data."""
    input_data: dict = {}


class WorkflowPublishRequest(BaseModel):
    """Publish an N8N workflow as a NOVA2 agent."""
    name: str
    slug: str
    description: str = ""
    icon: str = "account_tree"
    role_ids: list[UUID] = []


class WorkflowAnalysisResponse(BaseModel):
    """Response containing workflow analysis for UI generation."""
    workflow_id: str
    workflow_name: str
    analysis: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
async def n8n_health(
    current_user: User = Depends(get_current_user),
):
    """Check if the N8N engine is running and reachable."""
    healthy = await check_n8n_health()
    return {"healthy": healthy, "service": "n8n"}


@router.get("/workflows")
async def list_workflows(
    current_user: User = Depends(get_current_user),
):
    """List all workflows available in the N8N instance."""
    try:
        workflows = await list_n8n_workflows()
        # Return simplified list for the UI
        return {
            "workflows": [
                {
                    "id": str(wf.get("id", "")),
                    "name": wf.get("name", "Unnamed"),
                    "active": wf.get("active", False),
                    "created_at": wf.get("createdAt", ""),
                    "updated_at": wf.get("updatedAt", ""),
                    "node_count": len(wf.get("nodes", [])),
                    "tags": [t.get("name", "") for t in wf.get("tags", [])],
                }
                for wf in workflows
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list N8N workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot reach N8N: {e}",
        )


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get full workflow details including node analysis."""
    try:
        workflow = await get_n8n_workflow(workflow_id)
        analysis = analyze_workflow(workflow)
        return {
            "workflow": workflow,
            "analysis": analysis.to_dict(),
        }
    except Exception as e:
        logger.error(f"Failed to get N8N workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot fetch workflow: {e}",
        )


@router.post("/workflows")
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: User = Depends(require_permission("agents", "write")),
):
    """Create a new workflow in N8N from raw JSON."""
    try:
        result = await create_n8n_workflow(request.workflow_json)
        analysis = analyze_workflow(result)
        return {
            "workflow": result,
            "analysis": analysis.to_dict(),
        }
    except Exception as e:
        logger.error(f"Failed to create N8N workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot create workflow: {e}",
        )


@router.post("/workflows/import")
async def import_workflow(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("agents", "write")),
):
    """Import a workflow JSON file into N8N."""
    content = await file.read()
    try:
        workflow_json = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON file",
        )

    try:
        result = await create_n8n_workflow(workflow_json)
        analysis = analyze_workflow(result)
        return {
            "workflow": result,
            "analysis": analysis.to_dict(),
        }
    except Exception as e:
        logger.error(f"Failed to import N8N workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot import workflow: {e}",
        )


@router.post("/workflows/{workflow_id}/analyze")
async def analyze_workflow_endpoint(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Analyze a workflow and return UI metadata."""
    try:
        workflow = await get_n8n_workflow(workflow_id)
        analysis = analyze_workflow(workflow)
        return WorkflowAnalysisResponse(
            workflow_id=workflow_id,
            workflow_name=workflow.get("name", "Unnamed"),
            analysis=analysis.to_dict(),
        )
    except Exception as e:
        logger.error(f"Failed to analyze workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot analyze workflow: {e}",
        )


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a workflow with input data and return results."""
    try:
        result = await execute_n8n_workflow(workflow_id, request.input_data)
        return {"execution": result}
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot execute workflow: {e}",
        )


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get execution details and status."""
    try:
        result = await get_n8n_execution(execution_id)
        return {"execution": result}
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot fetch execution: {e}",
        )


@router.post("/workflows/{workflow_id}/publish")
async def publish_workflow_as_agent(
    workflow_id: str,
    request: WorkflowPublishRequest,
    current_user: User = Depends(require_permission("agents", "write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish an N8N workflow as a NOVA2 platform agent.

    This creates an Agent entry in the DB with agent_type='n8n_workflow'
    and stores the workflow analysis in the config field, which the
    frontend dynamic renderer uses to build the appropriate UI.
    """
    # Validate slug format
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", request.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid slug format. Must be kebab-case (e.g., my-workflow-agent)",
        )

    # Check slug uniqueness
    existing = await db.execute(select(Agent).where(Agent.slug == request.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent slug '{request.slug}' already exists",
        )

    # Fetch and analyze the workflow
    try:
        workflow = await get_n8n_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot fetch workflow from N8N: {e}",
        )

    analysis = analyze_workflow(workflow)
    agent_config = generate_agent_config_from_analysis(
        analysis, workflow_id, workflow.get("name", request.name),
    )
    # Override icon if user specified one
    if request.icon != "account_tree":
        agent_config["icon"] = request.icon

    # Create the agent
    agent = Agent(
        name=request.name,
        slug=request.slug,
        description=request.description or f"Workflow agent powered by N8N: {workflow.get('name', '')}",
        version="1.0.0",
        agent_type="n8n_workflow",
        config=agent_config,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(agent)
    await db.flush()

    # Set role permissions
    for role_id in request.role_ids:
        db.add(AgentPermission(agent_id=agent.id, role_id=role_id))

    await db.commit()
    await db.refresh(agent)

    return {
        "id": str(agent.id),
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "config": agent.config,
        "analysis": analysis.to_dict(),
    }
