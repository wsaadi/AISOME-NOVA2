"""
Connectors API — Catalogue et exécution des connecteurs de la plateforme.

Endpoints:
    GET  /api/connectors                      — Catalogue complet
    GET  /api/connectors/{slug}               — Détail d'un connecteur
    GET  /api/connectors/{slug}/actions       — Actions disponibles
    POST /api/connectors/{slug}/execute       — Exécuter une action
    GET  /api/connectors/health               — Santé des connecteurs
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/connectors", tags=["Connectors"])

_connector_registry = None


def get_connector_registry():
    """Retourne le registre de connecteurs."""
    global _connector_registry
    if _connector_registry is None:
        from app.framework.connectors.registry import ConnectorRegistry

        _connector_registry = ConnectorRegistry()
        _connector_registry.discover()
    return _connector_registry


class ConnectorExecuteRequest(BaseModel):
    """Requête d'exécution d'une action connecteur."""

    action: str = Field(..., description="Nom de l'action à exécuter")
    params: dict[str, Any] = Field(default_factory=dict)


class ConnectorExecuteResponse(BaseModel):
    """Réponse d'exécution d'une action connecteur."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


@router.get("")
async def list_connectors(current_user=Depends(get_current_user)):
    """
    Catalogue complet des connecteurs disponibles.

    Retourne tous les connecteurs avec leurs actions et schemas.
    """
    registry = get_connector_registry()
    return registry.get_catalog()


@router.get("/health")
async def connectors_health(current_user=Depends(get_current_user)):
    """
    Vérifie la santé de tous les connecteurs actifs.

    Returns:
        Dict slug → is_healthy
    """
    registry = get_connector_registry()
    return await registry.health_check_all()


@router.get("/{slug}")
async def get_connector_detail(slug: str, current_user=Depends(get_current_user)):
    """
    Détail d'un connecteur avec son schema complet.

    Args:
        slug: Slug du connecteur
    """
    registry = get_connector_registry()
    connector = registry.get_connector(slug)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connecteur '{slug}' non trouvé")
    return connector.metadata.model_dump()


@router.get("/{slug}/actions")
async def get_connector_actions(slug: str, current_user=Depends(get_current_user)):
    """
    Liste les actions disponibles pour un connecteur.

    Args:
        slug: Slug du connecteur
    """
    registry = get_connector_registry()
    connector = registry.get_connector(slug)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connecteur '{slug}' non trouvé")

    return [action.model_dump() for action in connector.metadata.actions]


@router.post("/{slug}/execute", response_model=ConnectorExecuteResponse)
async def execute_connector(
    slug: str,
    request: ConnectorExecuteRequest,
    current_user=Depends(get_current_user),
):
    """
    Exécute une action sur un connecteur.

    Args:
        slug: Slug du connecteur
        request: Action et paramètres
    """
    registry = get_connector_registry()
    result = await registry.execute_connector(slug, request.action, request.params)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return ConnectorExecuteResponse(
        success=result.success,
        data=result.data,
        error=result.error,
    )
