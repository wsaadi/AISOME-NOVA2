import json
import io
import zipfile
from datetime import datetime
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
    ) -> Agent:
        buffer = io.BytesIO(data)
        with zipfile.ZipFile(buffer, "r") as zf:
            agent_json = json.loads(zf.read("agent.json"))

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
