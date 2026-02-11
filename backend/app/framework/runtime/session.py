"""
Session Manager — Gestion des sessions de conversation.

Chaque interaction utilisateur × agent crée une session.
Les sessions persistent les messages et l'état de la conversation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from app.framework.schemas import (
    MessageRole,
    SessionInfo,
    SessionMessage,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gestionnaire de sessions de conversation.

    Gère la création, la récupération et la persistance des sessions.
    Les sessions sont stockées en base (PostgreSQL) pour la persistance
    et en cache (Redis) pour la performance.
    """

    def __init__(self, db_session: Any, redis_client: Any = None):
        self._db = db_session
        self._redis = redis_client

    async def create_session(
        self, agent_slug: str, user_id: int, title: str = ""
    ) -> SessionInfo:
        """
        Crée une nouvelle session de conversation.

        Args:
            agent_slug: Slug de l'agent
            user_id: ID de l'utilisateur
            title: Titre optionnel de la session

        Returns:
            SessionInfo avec l'ID de la nouvelle session
        """
        session_id = str(uuid.uuid4())
        session = SessionInfo(
            session_id=session_id,
            agent_slug=agent_slug,
            user_id=user_id,
            title=title or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        )

        # Persister en base
        await self._persist_session(session)

        # Cache Redis
        if self._redis:
            await self._cache_session(session)

        logger.info(
            f"Session created: {session_id} for agent={agent_slug} user={user_id}"
        )
        return session

    async def create_session_with_id(
        self, session_id: str, agent_slug: str, user_id: int, title: str = ""
    ) -> SessionInfo:
        """
        Crée une session avec un ID prédéfini (fourni par le frontend).

        Args:
            session_id: ID de session imposé
            agent_slug: Slug de l'agent
            user_id: ID de l'utilisateur
            title: Titre optionnel

        Returns:
            SessionInfo créée
        """
        session = SessionInfo(
            session_id=session_id,
            agent_slug=agent_slug,
            user_id=user_id,
            title=title or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        )

        await self._persist_session(session)

        if self._redis:
            await self._cache_session(session)

        logger.info(
            f"Session created (custom id): {session_id} for agent={agent_slug} user={user_id}"
        )
        return session

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Récupère une session par son ID.

        Cherche d'abord en cache Redis, puis en base PostgreSQL.

        Args:
            session_id: ID de la session

        Returns:
            SessionInfo ou None si introuvable
        """
        # Essayer le cache d'abord
        if self._redis:
            cached = await self._get_cached_session(session_id)
            if cached:
                return cached

        # Sinon aller en base
        return await self._load_session(session_id)

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        attachments: list | None = None,
        metadata: dict | None = None,
    ) -> SessionMessage:
        """
        Ajoute un message à une session.

        Args:
            session_id: ID de la session
            role: Rôle (user, assistant, system)
            content: Contenu du message
            attachments: Pièces jointes optionnelles
            metadata: Métadonnées optionnelles

        Returns:
            SessionMessage créé
        """
        message = SessionMessage(
            role=role,
            content=content,
            attachments=attachments or [],
            metadata=metadata or {},
        )

        await self._persist_message(session_id, message)

        if self._redis:
            await self._cache_message(session_id, message)

        return message

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[SessionMessage]:
        """
        Récupère les messages d'une session.

        Args:
            session_id: ID de la session
            limit: Nombre max de messages (None = tous)

        Returns:
            Liste de SessionMessage ordonnés chronologiquement
        """
        # Essayer le cache d'abord
        if self._redis:
            cached = await self._get_cached_messages(session_id, limit)
            if cached is not None:
                return cached

        return await self._load_messages(session_id, limit)

    async def clear_messages(self, session_id: str) -> None:
        """
        Efface tous les messages d'une session.

        Args:
            session_id: ID de la session
        """
        await self._delete_messages(session_id)

        if self._redis:
            await self._invalidate_cache(session_id)

    async def list_sessions(
        self,
        agent_slug: str,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessionInfo]:
        """
        Liste les sessions d'un utilisateur pour un agent.

        Args:
            agent_slug: Slug de l'agent
            user_id: ID de l'utilisateur
            limit: Nombre max de résultats
            offset: Offset pour la pagination

        Returns:
            Liste de SessionInfo ordonnés par date décroissante
        """
        return await self._list_sessions_from_db(agent_slug, user_id, limit, offset)

    async def close_session(self, session_id: str) -> None:
        """
        Ferme une session (marque comme inactive).

        Args:
            session_id: ID de la session
        """
        await self._update_session_status(session_id, is_active=False)

        if self._redis:
            await self._invalidate_cache(session_id)

    # =========================================================================
    # Couche de persistance (PostgreSQL)
    # =========================================================================

    async def _persist_session(self, session: SessionInfo) -> None:
        """Persiste une session en base."""
        from sqlalchemy import text

        await self._db.execute(
            text(
                """
                INSERT INTO agent_sessions (session_id, agent_slug, user_id, title, is_active, created_at, updated_at)
                VALUES (:session_id, :agent_slug, :user_id, :title, :is_active, :created_at, :updated_at)
                """
            ),
            {
                "session_id": session.session_id,
                "agent_slug": session.agent_slug,
                "user_id": session.user_id,
                "title": session.title,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            },
        )
        await self._db.commit()

    async def _persist_message(self, session_id: str, message: SessionMessage) -> None:
        """Persiste un message en base."""
        import json

        from sqlalchemy import text

        await self._db.execute(
            text(
                """
                INSERT INTO agent_session_messages (session_id, role, content, attachments, metadata, timestamp)
                VALUES (:session_id, :role, :content, :attachments, :metadata, :timestamp)
                """
            ),
            {
                "session_id": session_id,
                "role": message.role.value,
                "content": message.content,
                "attachments": json.dumps(
                    [a.model_dump() for a in message.attachments]
                ),
                "metadata": json.dumps(message.metadata),
                "timestamp": message.timestamp,
            },
        )
        await self._db.commit()

    async def _load_session(self, session_id: str) -> Optional[SessionInfo]:
        """Charge une session depuis la base."""
        from sqlalchemy import text

        result = await self._db.execute(
            text("SELECT * FROM agent_sessions WHERE session_id = :sid"),
            {"sid": session_id},
        )
        row = result.fetchone()
        if not row:
            return None

        messages = await self._load_messages(session_id)
        return SessionInfo(
            session_id=row.session_id,
            agent_slug=row.agent_slug,
            user_id=row.user_id,
            title=row.title,
            messages=messages,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _load_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[SessionMessage]:
        """Charge les messages d'une session depuis la base."""
        import json

        from sqlalchemy import text

        query = "SELECT * FROM agent_session_messages WHERE session_id = :sid ORDER BY timestamp ASC"
        if limit:
            query += f" LIMIT {limit}"

        result = await self._db.execute(text(query), {"sid": session_id})
        rows = result.fetchall()

        return [
            SessionMessage(
                role=MessageRole(row.role),
                content=row.content,
                attachments=json.loads(row.attachments) if row.attachments else [],
                metadata=json.loads(row.metadata) if row.metadata else {},
                timestamp=row.timestamp,
            )
            for row in rows
        ]

    async def _delete_messages(self, session_id: str) -> None:
        """Supprime les messages d'une session en base."""
        from sqlalchemy import text

        await self._db.execute(
            text("DELETE FROM agent_session_messages WHERE session_id = :sid"),
            {"sid": session_id},
        )
        await self._db.commit()

    async def _list_sessions_from_db(
        self, agent_slug: str, user_id: int, limit: int, offset: int
    ) -> list[SessionInfo]:
        """Liste les sessions depuis la base."""
        from sqlalchemy import text

        result = await self._db.execute(
            text(
                """
                SELECT * FROM agent_sessions
                WHERE agent_slug = :slug AND user_id = :uid
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"slug": agent_slug, "uid": user_id, "limit": limit, "offset": offset},
        )
        return [
            SessionInfo(
                session_id=row.session_id,
                agent_slug=row.agent_slug,
                user_id=row.user_id,
                title=row.title,
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]

    async def _update_session_status(self, session_id: str, is_active: bool) -> None:
        """Met à jour le statut d'une session."""
        from sqlalchemy import text

        await self._db.execute(
            text(
                "UPDATE agent_sessions SET is_active = :active, updated_at = NOW() WHERE session_id = :sid"
            ),
            {"active": is_active, "sid": session_id},
        )
        await self._db.commit()

    # =========================================================================
    # Couche cache (Redis)
    # =========================================================================

    async def _cache_session(self, session: SessionInfo) -> None:
        """Met en cache une session dans Redis."""
        pass  # Implémenté quand Redis est intégré

    async def _get_cached_session(self, session_id: str) -> Optional[SessionInfo]:
        """Récupère une session depuis le cache Redis."""
        return None  # Implémenté quand Redis est intégré

    async def _cache_message(self, session_id: str, message: SessionMessage) -> None:
        """Met en cache un message dans Redis."""
        pass  # Implémenté quand Redis est intégré

    async def _get_cached_messages(
        self, session_id: str, limit: Optional[int]
    ) -> Optional[list[SessionMessage]]:
        """Récupère les messages depuis le cache Redis."""
        return None  # Implémenté quand Redis est intégré

    async def _invalidate_cache(self, session_id: str) -> None:
        """Invalide le cache d'une session."""
        pass  # Implémenté quand Redis est intégré
