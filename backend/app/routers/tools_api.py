"""
Tools API — Catalogue et exécution des tools de la plateforme.

Endpoints:
    GET  /api/tools              — Catalogue complet des tools
    GET  /api/tools/{slug}       — Détail d'un tool (schema, exemples)
    POST /api/tools/{slug}/execute — Exécuter un tool
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/tools", tags=["Tools"])

# Instance globale du registre (initialisée au démarrage)
_tool_registry = None


def get_tool_registry():
    """Retourne le registre de tools (initialisé au démarrage de l'app)."""
    global _tool_registry
    if _tool_registry is None:
        from app.framework.tools.registry import ToolRegistry

        _tool_registry = ToolRegistry()
        _tool_registry.discover()
    return _tool_registry


class ToolExecuteRequest(BaseModel):
    """Requête d'exécution d'un tool."""

    params: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    """Réponse d'exécution d'un tool."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


@router.get("")
async def list_tools(current_user=Depends(get_current_user)):
    """
    Catalogue complet des tools disponibles.

    Retourne tous les tools avec leurs schemas input/output et exemples.
    Auto-généré depuis le registre (auto-discovery).
    """
    registry = get_tool_registry()
    return registry.get_catalog()


@router.get("/{slug}")
async def get_tool_detail(slug: str, current_user=Depends(get_current_user)):
    """
    Détail d'un tool avec son schema complet.

    Args:
        slug: Slug du tool
    """
    registry = get_tool_registry()
    tool = registry.get_tool(slug)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{slug}' non trouvé")
    return tool.metadata.model_dump()


@router.post("/{slug}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    slug: str,
    request: ToolExecuteRequest,
    current_user=Depends(get_current_user),
):
    """
    Exécute un tool.

    Args:
        slug: Slug du tool
        request: Paramètres d'exécution
    """
    registry = get_tool_registry()
    result = await registry.execute_tool(slug, request.params)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return ToolExecuteResponse(
        success=result.success,
        data=result.data,
        error=result.error,
    )
