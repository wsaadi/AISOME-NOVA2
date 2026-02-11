"""
Connectors API — Catalogue, connexion et exécution des connecteurs de la plateforme.

Endpoints:
    GET  /api/connectors                      — Catalogue complet
    GET  /api/connectors/health               — Santé de tous les connecteurs
    GET  /api/connectors/categories           — Catégories disponibles
    GET  /api/connectors/{slug}               — Détail d'un connecteur
    GET  /api/connectors/{slug}/actions       — Actions disponibles
    GET  /api/connectors/{slug}/health        — Santé d'un connecteur spécifique
    POST /api/connectors/{slug}/connect       — Initialiser la connexion (via Vault)
    POST /api/connectors/{slug}/disconnect    — Fermer la connexion
    POST /api/connectors/{slug}/execute       — Exécuter une action
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/connectors", tags=["Connectors"])

_connector_registry = None


def get_connector_registry():
    """Retourne le registre de connecteurs (singleton)."""
    global _connector_registry
    if _connector_registry is None:
        from app.framework.connectors.registry import ConnectorRegistry

        _connector_registry = ConnectorRegistry()
        _connector_registry.discover()
    return _connector_registry


# =============================================================================
# Request / Response schemas
# =============================================================================


class ConnectorExecuteRequest(BaseModel):
    """Requête d'exécution d'une action connecteur."""

    action: str = Field(..., description="Nom de l'action à exécuter")
    params: dict[str, Any] = Field(default_factory=dict)


class ConnectorExecuteResponse(BaseModel):
    """Réponse d'exécution d'une action connecteur."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None


class ConnectorConnectResponse(BaseModel):
    """Réponse de connexion."""

    connected: bool
    slug: str
    message: str = ""


class ConnectorHealthResponse(BaseModel):
    """Réponse de health check."""

    healthy: bool
    message: str = ""


# =============================================================================
# Catalogue
# =============================================================================


@router.get("")
async def list_connectors(
    category: str | None = Query(None, description="Filtrer par catégorie"),
    current_user=Depends(get_current_user),
):
    """
    Catalogue des connecteurs disponibles.

    Retourne tous les connecteurs avec leurs actions, schemas et statut.
    Filtrage optionnel par catégorie.
    """
    registry = get_connector_registry()
    if category:
        connectors = registry.list_by_category(category)
        return [c.model_dump() for c in connectors]
    return registry.get_catalog()


@router.get("/categories")
async def list_categories(current_user=Depends(get_current_user)):
    """
    Liste les catégories de connecteurs disponibles.

    Returns:
        Liste des catégories ayant au moins 1 connecteur
    """
    registry = get_connector_registry()
    return registry.get_categories()


# =============================================================================
# Health
# =============================================================================


@router.get("/health")
async def connectors_health(current_user=Depends(get_current_user)):
    """
    Vérifie la santé de tous les connecteurs actifs.

    Returns:
        Dict slug → is_healthy
    """
    registry = get_connector_registry()
    return await registry.health_check_all()


@router.get("/{slug}/health", response_model=ConnectorHealthResponse)
async def connector_health(slug: str, current_user=Depends(get_current_user)):
    """
    Vérifie la santé d'un connecteur spécifique.

    Args:
        slug: Slug du connecteur
    """
    registry = get_connector_registry()
    if not registry.connector_exists(slug):
        raise HTTPException(status_code=404, detail=f"Connecteur '{slug}' non trouvé")

    result = await registry.health_check(slug)
    return ConnectorHealthResponse(healthy=result["healthy"], message=result["message"])


# =============================================================================
# Détail
# =============================================================================


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

    detail = connector.metadata.model_dump()
    detail["is_connected"] = registry.is_connected(slug)
    return detail


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


# =============================================================================
# Connexion / Déconnexion
# =============================================================================


@router.post("/{slug}/connect", response_model=ConnectorConnectResponse)
async def connect_connector(slug: str, current_user=Depends(get_current_user)):
    """
    Initialise la connexion d'un connecteur via les credentials Vault.

    Le framework récupère automatiquement la config depuis Vault
    et appelle connector.connect(config).

    Args:
        slug: Slug du connecteur
    """
    registry = get_connector_registry()
    if not registry.connector_exists(slug):
        raise HTTPException(status_code=404, detail=f"Connecteur '{slug}' non trouvé")

    if registry.is_connected(slug):
        return ConnectorConnectResponse(
            connected=True, slug=slug, message="Déjà connecté"
        )

    success = await registry.connect_from_vault(slug)
    if not success:
        return ConnectorConnectResponse(
            connected=False, slug=slug,
            message="Connexion échouée — vérifier la configuration Vault",
        )

    return ConnectorConnectResponse(
        connected=True, slug=slug, message="Connecté avec succès"
    )


@router.post("/{slug}/disconnect", response_model=ConnectorConnectResponse)
async def disconnect_connector(slug: str, current_user=Depends(get_current_user)):
    """
    Ferme la connexion d'un connecteur.

    Args:
        slug: Slug du connecteur
    """
    registry = get_connector_registry()
    if not registry.connector_exists(slug):
        raise HTTPException(status_code=404, detail=f"Connecteur '{slug}' non trouvé")

    await registry.disconnect(slug)
    return ConnectorConnectResponse(
        connected=False, slug=slug, message="Déconnecté"
    )


# =============================================================================
# Exécution
# =============================================================================


@router.post("/{slug}/execute", response_model=ConnectorExecuteResponse)
async def execute_connector(
    slug: str,
    request: ConnectorExecuteRequest,
    current_user=Depends(get_current_user),
):
    """
    Exécute une action sur un connecteur.

    Si le connecteur n'est pas encore connecté, une lazy connection via Vault est tentée.

    Args:
        slug: Slug du connecteur
        request: Action et paramètres
    """
    registry = get_connector_registry()
    result = await registry.execute_connector(slug, request.action, request.params)

    return ConnectorExecuteResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        error_code=result.error_code.value if result.error_code else None,
    )
