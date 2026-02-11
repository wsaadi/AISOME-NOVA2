"""
Tools API — Catalogue, exécution et health check des tools de la plateforme.

Endpoints:
    GET  /api/tools              — Catalogue complet des tools
    GET  /api/tools/health       — Health check de tous les tools
    GET  /api/tools/categories   — Liste des catégories
    GET  /api/tools/{slug}       — Détail d'un tool (schema, exemples)
    GET  /api/tools/{slug}/health — Health check d'un tool
    POST /api/tools/{slug}/execute — Exécuter un tool
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    error_code: str | None = None


class ToolHealthResponse(BaseModel):
    """Réponse de health check d'un tool."""

    healthy: bool
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_tools(
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    current_user=Depends(get_current_user),
):
    """
    Catalogue complet des tools disponibles.

    Retourne tous les tools avec leurs schemas input/output et exemples.
    Auto-généré depuis le registre (auto-discovery).

    Filtrage optionnel par catégorie.
    """
    registry = get_tool_registry()
    if category:
        return [m.model_dump() for m in registry.list_by_category(category)]
    return registry.get_catalog()


@router.get("/health")
async def health_check_all(current_user=Depends(get_current_user)):
    """
    Health check de tous les tools.

    Retourne l'état de santé de chaque tool enregistré.
    """
    registry = get_tool_registry()
    results = await registry.health_check_all()
    return {
        slug: result.model_dump()
        for slug, result in results.items()
    }


@router.get("/categories")
async def list_categories(current_user=Depends(get_current_user)):
    """
    Liste des catégories de tools disponibles.
    """
    registry = get_tool_registry()
    return registry.get_categories()


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


@router.get("/{slug}/health")
async def health_check_tool(slug: str, current_user=Depends(get_current_user)):
    """
    Health check d'un tool spécifique.

    Args:
        slug: Slug du tool
    """
    registry = get_tool_registry()
    result = await registry.health_check_tool(slug)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Tool '{slug}' non trouvé")
    return result.model_dump()


@router.post("/{slug}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    slug: str,
    request: ToolExecuteRequest,
    current_user=Depends(get_current_user),
):
    """
    Exécute un tool.

    Le framework gère automatiquement:
    - Validation des paramètres contre le schema
    - Timeout selon le mode (sync/async)
    - Error codes standardisés

    Args:
        slug: Slug du tool
        request: Paramètres d'exécution
    """
    from app.framework.runtime.context import ToolContext

    registry = get_tool_registry()

    context = ToolContext(user_id=current_user.id)
    result = await registry.execute_tool(slug, request.params, context)

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.error,
                "error_code": result.error_code.value if result.error_code else None,
            },
        )

    return ToolExecuteResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        error_code=result.error_code.value if result.error_code else None,
    )
