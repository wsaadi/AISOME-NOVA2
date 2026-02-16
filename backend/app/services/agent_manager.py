import json
import io
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from minio import Minio
from app.config import get_settings
from app.models.agent import Agent, AgentPermission
from app.models.moderation import ModerationRule

settings = get_settings()
logger = logging.getLogger(__name__)

# Filesystem roots for deploying framework agents
_BACKEND_AGENTS_ROOT = Path(__file__).parent.parent / "agents"
_FRONTEND_AGENTS_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "src" / "agents"


class AgentManager:
    def __init__(self):
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.minio_client.bucket_exists(settings.MINIO_BUCKET):
                self.minio_client.make_bucket(settings.MINIO_BUCKET)
        except Exception:
            pass

    async def export_agent(self, db: AsyncSession, agent_id: UUID) -> bytes:
        result = await db.execute(
            select(Agent)
            .options(selectinload(Agent.moderation_rules))
            .where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")

        export_data = {
            "name": agent.name,
            "slug": agent.slug,
            "description": agent.description,
            "version": agent.version,
            "agent_type": agent.agent_type,
            "config": agent.config,
            "system_prompt": agent.system_prompt,
            "moderation_rules": [
                {
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "config": rule.config,
                    "entity_types": rule.entity_types,
                    "action": rule.action,
                    "replacement_template": rule.replacement_template,
                    "is_active": rule.is_active,
                }
                for rule in agent.moderation_rules
            ],
            "export_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("agent.json", json.dumps(export_data, indent=2, default=str))
        buffer.seek(0)

        object_name = f"exports/{agent.slug}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        self.minio_client.put_object(
            settings.MINIO_BUCKET, object_name, buffer, buffer.getbuffer().nbytes,
            content_type="application/zip",
        )
        buffer.seek(0)
        return buffer.read()

    async def import_agent(
        self, db: AsyncSession, data: bytes, created_by: Optional[UUID] = None,
        name_override: Optional[str] = None, slug_override: Optional[str] = None,
        overwrite_slug: Optional[str] = None,
    ) -> Agent:
        buffer = io.BytesIO(data)
        with zipfile.ZipFile(buffer, "r") as zf:
            names = zf.namelist()
            is_framework = "backend/manifest.json" in names or "backend/agent.py" in names

            if "agent.json" in names:
                agent_json = json.loads(zf.read("agent.json"))
            elif "backend/manifest.json" in names:
                manifest = json.loads(zf.read("backend/manifest.json"))
                system_prompt = ""
                if "backend/prompts/system.md" in names:
                    system_prompt = zf.read("backend/prompts/system.md").decode("utf-8")
                agent_json = {
                    "name": manifest.get("name", "Imported Agent"),
                    "slug": manifest.get("slug", "imported-agent"),
                    "description": manifest.get("description", ""),
                    "version": manifest.get("version", "1.0.0"),
                    "agent_type": manifest.get("category", "conversational"),
                    "config": {
                        "icon": manifest.get("icon", "smart_toy"),
                        "category": manifest.get("category", "general"),
                        "tags": manifest.get("tags", []),
                        "dependencies": manifest.get("dependencies", {}),
                        "triggers": manifest.get("triggers", []),
                        "capabilities": manifest.get("capabilities", []),
                    },
                    "system_prompt": system_prompt,
                    "moderation_rules": [],
                }
            else:
                raise ValueError(
                    f"Invalid archive: expected agent.json or backend/manifest.json. "
                    f"Found: {names[:10]}"
                )

            # ── Deploy framework files to filesystem ──
            if is_framework:
                deploy_slug = overwrite_slug or slug_override or agent_json.get("slug", "unknown-agent")
                self._deploy_framework_files(zf, names, deploy_slug)

        # ── Overwrite mode: update existing agent ──
        if overwrite_slug:
            result = await db.execute(select(Agent).where(Agent.slug == overwrite_slug))
            existing_agent = result.scalar_one_or_none()
            if existing_agent:
                existing_agent.name = name_override or agent_json["name"]
                existing_agent.description = agent_json.get("description")
                existing_agent.version = agent_json.get("version", "1.0.0")
                existing_agent.agent_type = agent_json.get("agent_type", "conversational")
                existing_agent.config = agent_json.get("config", {})
                existing_agent.system_prompt = agent_json.get("system_prompt")
                await db.commit()
                await db.refresh(existing_agent)
                logger.info(f"Overwritten agent '{overwrite_slug}'")
                return existing_agent

        slug = slug_override or agent_json["slug"]
        existing = await db.execute(select(Agent).where(Agent.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{uuid4().hex[:8]}"

        agent = Agent(
            name=name_override or agent_json["name"],
            slug=slug,
            description=agent_json.get("description"),
            version=agent_json.get("version", "1.0.0"),
            agent_type=agent_json.get("agent_type", "conversational"),
            config=agent_json.get("config", {}),
            system_prompt=agent_json.get("system_prompt"),
            created_by=created_by,
        )
        db.add(agent)
        await db.flush()

        for rule_data in agent_json.get("moderation_rules", []):
            rule = ModerationRule(
                name=rule_data["name"],
                agent_id=agent.id,
                rule_type=rule_data["rule_type"],
                config=rule_data.get("config", {}),
                entity_types=rule_data.get("entity_types", []),
                action=rule_data.get("action", "redact"),
                replacement_template=rule_data.get("replacement_template", "[REDACTED]"),
                is_active=rule_data.get("is_active", True),
            )
            db.add(rule)

        await db.commit()
        await db.refresh(agent)
        return agent

    # ──────────────────────────────────────────────────────────────────────
    # Framework file deployment
    # ──────────────────────────────────────────────────────────────────────

    def _deploy_framework_files(
        self, zf: zipfile.ZipFile, names: list[str], slug: str
    ) -> None:
        """
        Deploy backend & frontend framework files from a ZIP to the filesystem
        and update the frontend registry so the custom view is loaded.
        """
        # Sanitize slug — only allow safe characters
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
            logger.warning(f"Skipping deploy for invalid slug: {slug}")
            return

        # ── Backend files ──
        backend_dir = _BACKEND_AGENTS_ROOT / slug
        backend_dir.mkdir(parents=True, exist_ok=True)
        (backend_dir / "prompts").mkdir(exist_ok=True)

        file_mapping = {
            "backend/manifest.json": backend_dir / "manifest.json",
            "backend/agent.py": backend_dir / "agent.py",
            "backend/prompts/system.md": backend_dir / "prompts" / "system.md",
        }

        for zip_path, fs_path in file_mapping.items():
            if zip_path in names:
                content = zf.read(zip_path)
                fs_path.write_bytes(content)
                logger.info(f"Deployed {zip_path} → {fs_path}")

        # ── Frontend files ──
        frontend_dir = _FRONTEND_AGENTS_ROOT / slug
        frontend_dir.mkdir(parents=True, exist_ok=True)

        frontend_mapping = {
            "frontend/index.tsx": frontend_dir / "index.tsx",
            "frontend/styles.ts": frontend_dir / "styles.ts",
        }

        has_frontend = False
        for zip_path, fs_path in frontend_mapping.items():
            if zip_path in names:
                content = zf.read(zip_path)
                fs_path.write_bytes(content)
                has_frontend = True
                logger.info(f"Deployed {zip_path} → {fs_path}")

        # NOTE: Frontend registry uses require.context auto-discovery.
        # No manual registry update needed — just deploying the files is enough.
        # The frontend will pick up new agent views at next build.

    async def duplicate_agent(
        self, db: AsyncSession, agent_id: UUID, new_name: str, new_slug: str,
        created_by: Optional[UUID] = None,
    ) -> Agent:
        result = await db.execute(
            select(Agent)
            .options(selectinload(Agent.moderation_rules), selectinload(Agent.permissions))
            .where(Agent.id == agent_id)
        )
        original = result.scalar_one_or_none()
        if not original:
            raise ValueError("Agent not found")

        new_agent = Agent(
            name=new_name,
            slug=new_slug,
            description=original.description,
            version=original.version,
            agent_type=original.agent_type,
            config=original.config.copy() if original.config else {},
            system_prompt=original.system_prompt,
            created_by=created_by,
        )
        db.add(new_agent)
        await db.flush()

        for perm in original.permissions:
            db.add(AgentPermission(agent_id=new_agent.id, role_id=perm.role_id))

        for rule in original.moderation_rules:
            db.add(ModerationRule(
                name=rule.name,
                agent_id=new_agent.id,
                rule_type=rule.rule_type,
                config=rule.config,
                entity_types=rule.entity_types,
                action=rule.action,
                replacement_template=rule.replacement_template,
                is_active=rule.is_active,
            ))

        await db.commit()
        await db.refresh(new_agent)
        return new_agent


def get_agent_manager() -> AgentManager:
    return AgentManager()
