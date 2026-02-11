"""
Connector Sync — Synchronise les connecteurs AI du framework vers la DB.

Auto-discovery bridge : connector registry → tables llm_providers / llm_models.
Appelé au démarrage de l'application et disponible via API pour sync manuel.
"""

from __future__ import annotations

import logging
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_provider import LLMProvider, LLMModel

logger = logging.getLogger(__name__)


def _get_connector_models(connector) -> list[dict]:
    """Extrait le catalogue de modèles depuis le module du connecteur.

    Chaque connecteur AI définit une constante *_MODELS (ex: OPENAI_MODELS).
    Tente sys.modules d'abord, puis importlib en fallback.
    """
    import importlib
    import importlib.util

    module_name = type(connector).__module__

    # Try sys.modules first
    mod = sys.modules.get(module_name)

    # Fallback: import the module directly
    if mod is None:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            pass

    if mod is None:
        logger.warning(f"Cannot find module {module_name} for connector models")
        return []

    for attr_name in dir(mod):
        attr = getattr(mod, attr_name, None)
        if attr_name.endswith("_MODELS") and isinstance(attr, list):
            return attr
    return []


def _get_base_url(metadata) -> str | None:
    """Extrait le base_url par défaut du config_schema du connecteur."""
    for param in metadata.config_schema:
        if param.name == "base_url" and param.default:
            return param.default
    return None


async def sync_connectors_to_db(db: AsyncSession) -> dict:
    """
    Synchronise les connecteurs AI du framework vers la DB.

    Pour chaque connecteur de catégorie 'ai' :
    - Upsert du LLMProvider (par slug)
    - Upsert des LLMModel depuis le catalogue du connecteur

    Returns:
        Résumé avec compteurs (providers_created, models_created, etc.)
    """
    from app.routers.connectors_api import get_connector_registry

    registry = get_connector_registry()
    ai_connectors = registry.list_by_category("ai")

    providers_created = 0
    providers_updated = 0
    models_created = 0

    for meta in ai_connectors:
        connector = registry.get_connector(meta.slug)
        if not connector:
            continue

        base_url = _get_base_url(meta)
        models = _get_connector_models(connector)

        # ── Upsert provider ──
        result = await db.execute(
            select(LLMProvider).where(LLMProvider.slug == meta.slug)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            provider = LLMProvider(
                name=meta.name,
                slug=meta.slug,
                base_url=base_url,
                is_active=True,
            )
            db.add(provider)
            await db.flush()
            providers_created += 1
            logger.info(f"Sync: created provider {meta.name} ({meta.slug})")
        else:
            if base_url and provider.base_url != base_url:
                provider.base_url = base_url
                providers_updated += 1

        # ── Upsert models ──
        existing_result = await db.execute(
            select(LLMModel.slug).where(LLMModel.provider_id == provider.id)
        )
        existing_slugs = {row[0] for row in existing_result.all()}

        for model_data in models:
            model_slug = model_data.get("id", model_data.get("slug", ""))
            model_name = model_data.get("name", model_slug)

            if model_slug and model_slug not in existing_slugs:
                db.add(LLMModel(
                    provider_id=provider.id,
                    name=model_name,
                    slug=model_slug,
                    is_active=True,
                ))
                models_created += 1

    await db.commit()

    summary = {
        "providers_created": providers_created,
        "providers_updated": providers_updated,
        "models_created": models_created,
        "connectors_scanned": len(ai_connectors),
    }
    logger.info(f"Connector sync complete: {summary}")
    return summary
