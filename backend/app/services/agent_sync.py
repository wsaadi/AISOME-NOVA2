"""
Agent Sync — Synchronise les agents framework du filesystem vers la DB.

Auto-discovery bridge : backend/app/agents/*/manifest.json → table agents.
Appelé au démarrage de l'application pour que les agents built-in
apparaissent dans le catalogue sans création manuelle.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

logger = logging.getLogger(__name__)

AGENTS_ROOT = Path(__file__).parent.parent / "agents"


async def sync_agents_to_db(db: AsyncSession) -> dict:
    """
    Synchronise les agents framework vers la DB.

    Pour chaque dossier dans backend/app/agents/ contenant un manifest.json :
    - Crée l'Agent en base s'il n'existe pas (par slug)
    - Met à jour name/description/version si l'agent existe déjà

    Returns:
        Résumé avec compteurs (created, updated, scanned)
    """
    if not AGENTS_ROOT.exists():
        logger.warning(f"Agents directory not found: {AGENTS_ROOT}")
        return {"created": 0, "updated": 0, "scanned": 0}

    created = 0
    updated = 0
    scanned = 0

    for agent_dir in sorted(AGENTS_ROOT.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
            continue

        manifest_path = agent_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        scanned += 1

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cannot read manifest for {agent_dir.name}: {e}")
            continue

        slug = manifest.get("slug", agent_dir.name)
        name = manifest.get("name", slug)
        description = manifest.get("description", "")
        version = manifest.get("version", "1.0.0")
        icon = manifest.get("icon", "smart_toy")
        category = manifest.get("category", "general")
        tags = manifest.get("tags", [])
        capabilities = manifest.get("capabilities", [])
        triggers = manifest.get("triggers", [])

        config = {
            "icon": icon,
            "category": category,
            "tags": tags,
            "capabilities": capabilities,
            "triggers": triggers,
            "dependencies": manifest.get("dependencies", {}),
            "framework_agent": True,
        }

        result = await db.execute(select(Agent).where(Agent.slug == slug))
        existing = result.scalar_one_or_none()

        if not existing:
            agent = Agent(
                name=name,
                slug=slug,
                description=description,
                version=version,
                agent_type="framework",
                config=config,
                is_active=True,
            )
            db.add(agent)
            created += 1
            logger.info(f"Agent sync: created {name} ({slug})")
        else:
            # Update metadata if changed
            changed = False
            if existing.name != name:
                existing.name = name
                changed = True
            if existing.description != description:
                existing.description = description
                changed = True
            if existing.version != version:
                existing.version = version
                changed = True
            if existing.config != config:
                existing.config = config
                changed = True
            if changed:
                updated += 1
                logger.info(f"Agent sync: updated {name} ({slug})")

    await db.commit()

    summary = {"created": created, "updated": updated, "scanned": scanned}
    logger.info(f"Agent sync complete: {summary}")
    return summary
