import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date, text
from app.models.consumption import Consumption
from app.models.quota import Quota

logger = logging.getLogger(__name__)


class ConsumptionService:
    """Service de logging de consommation utilisé par le pipeline d'exécution."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def log(
        self,
        user_id: UUID,
        agent_slug: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """
        Enregistre un usage de tokens en base.

        Résout l'agent_slug vers l'agent_id, récupère le provider/model actifs,
        calcule les coûts et crée un enregistrement Consumption.
        """
        if tokens_in == 0 and tokens_out == 0:
            return

        # Resolve agent_slug → agent_id
        agent_id = None
        try:
            result = await self._db.execute(
                text("SELECT id FROM agents WHERE slug = :slug LIMIT 1"),
                {"slug": agent_slug},
            )
            row = result.fetchone()
            if row:
                agent_id = row[0]
        except Exception:
            pass

        # Resolve active provider/model (with per-agent config fallback)
        provider_id = None
        model_id = None
        cost_in = 0.0
        cost_out = 0.0

        try:
            # Try agent-specific config first
            result = await self._db.execute(
                text("""
                    SELECT alc.provider_id, alc.model_id
                    FROM agent_llm_configs alc
                    WHERE alc.agent_slug = :slug AND alc.is_active = true
                    LIMIT 1
                """),
                {"slug": agent_slug},
            )
            row = result.fetchone()

            if not row:
                # Fallback to default
                result = await self._db.execute(
                    text("""
                        SELECT p.id as provider_id, m.id as model_id
                        FROM llm_providers p
                        JOIN llm_models m ON m.provider_id = p.id
                        WHERE p.is_active = true AND m.is_active = true
                        ORDER BY p.id ASC, m.id ASC
                        LIMIT 1
                    """)
                )
                row = result.fetchone()

            if row:
                provider_id = row[0]
                model_id = row[1]

                # Lookup cost per token
                cost_result = await self._db.execute(
                    text("""
                        SELECT cost_per_token_in, cost_per_token_out
                        FROM model_costs
                        WHERE model_id = :model_id
                        ORDER BY effective_date DESC
                        LIMIT 1
                    """),
                    {"model_id": model_id},
                )
                cost_row = cost_result.fetchone()
                if cost_row:
                    cost_in = tokens_in * (cost_row[0] or 0.0)
                    cost_out = tokens_out * (cost_row[1] or 0.0)
        except Exception as e:
            logger.warning(f"Failed to resolve provider/model for consumption: {e}")

        record = Consumption(
            user_id=user_id,
            agent_id=agent_id,
            provider_id=provider_id,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_in=cost_in,
            cost_out=cost_out,
        )
        self._db.add(record)
        try:
            await self._db.commit()
        except Exception as e:
            logger.error(f"Failed to commit consumption record: {e}")
            await self._db.rollback()


async def get_consumption_data(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    agent_id: Optional[UUID] = None,
    provider_id: Optional[UUID] = None,
    model_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Consumption]:
    query = select(Consumption)
    if user_id:
        query = query.where(Consumption.user_id == user_id)
    if agent_id:
        query = query.where(Consumption.agent_id == agent_id)
    if provider_id:
        query = query.where(Consumption.provider_id == provider_id)
    if model_id:
        query = query.where(Consumption.model_id == model_id)
    if date_from:
        query = query.where(Consumption.created_at >= date_from)
    if date_to:
        query = query.where(Consumption.created_at <= date_to)
    query = query.order_by(Consumption.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_consumption_summary(
    db: AsyncSession,
    group_by: str = "day",
    user_id: Optional[UUID] = None,
    agent_id: Optional[UUID] = None,
    provider_id: Optional[UUID] = None,
    model_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    group_column_map = {
        "user": Consumption.user_id,
        "agent": Consumption.agent_id,
        "provider": Consumption.provider_id,
        "model": Consumption.model_id,
        "day": cast(Consumption.created_at, Date),
    }
    group_col = group_column_map.get(group_by, cast(Consumption.created_at, Date))
    query = select(
        group_col.label("group_value"),
        func.sum(Consumption.tokens_in).label("total_tokens_in"),
        func.sum(Consumption.tokens_out).label("total_tokens_out"),
        func.sum(Consumption.cost_in).label("total_cost_in"),
        func.sum(Consumption.cost_out).label("total_cost_out"),
        func.count().label("count"),
    )
    if user_id:
        query = query.where(Consumption.user_id == user_id)
    if agent_id:
        query = query.where(Consumption.agent_id == agent_id)
    if provider_id:
        query = query.where(Consumption.provider_id == provider_id)
    if model_id:
        query = query.where(Consumption.model_id == model_id)
    if date_from:
        query = query.where(Consumption.created_at >= date_from)
    if date_to:
        query = query.where(Consumption.created_at <= date_to)
    query = query.group_by(group_col).order_by(group_col)
    result = await db.execute(query)
    return result.all()


async def check_quota(
    db: AsyncSession,
    target_type: str,
    target_id: UUID,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost: float = 0.0,
) -> dict:
    result = await db.execute(
        select(Quota).where(
            and_(Quota.target_type == target_type, Quota.target_id == target_id, Quota.is_active == True)
        )
    )
    quotas = result.scalars().all()
    for quota in quotas:
        period_start = _get_period_start(quota.period)
        usage_query = select(
            func.sum(Consumption.tokens_in + Consumption.tokens_out).label("total_tokens"),
            func.sum(Consumption.cost_in + Consumption.cost_out).label("total_cost"),
        ).where(Consumption.created_at >= period_start)

        if target_type == "user":
            usage_query = usage_query.where(Consumption.user_id == target_id)
        elif target_type == "agent":
            usage_query = usage_query.where(Consumption.agent_id == target_id)
        elif target_type == "provider":
            usage_query = usage_query.where(Consumption.provider_id == target_id)

        usage_result = await db.execute(usage_query)
        row = usage_result.one()

        current_value = 0
        if quota.quota_type == "token":
            current_value = (row.total_tokens or 0) + tokens_in + tokens_out
        elif quota.quota_type == "financial":
            current_value = (row.total_cost or 0) + cost

        if current_value > quota.limit_value:
            return {"allowed": False, "quota_id": str(quota.id), "current": current_value, "limit": quota.limit_value}
    return {"allowed": True}


def _get_period_start(period: str) -> datetime:
    now = datetime.utcnow()
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now
