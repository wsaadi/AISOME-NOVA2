"""
WebSocket Manager — Gestion des connexions WebSocket pour le temps réel.

Architecture:
    Redis Pub/Sub ← Workers Celery publient progression/streaming
    Redis Pub/Sub → WebSocket Manager → Clients WebSocket (frontend)

Channels Redis:
    job:{job_id}    — Progression d'un job (status, %, message)
    stream:{job_id} — Chunks de streaming (tokens LLM en temps réel)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestionnaire de connexions WebSocket.

    Gère les connexions actives et le dispatch des messages
    depuis Redis pub/sub vers les bons clients.
    """

    def __init__(self):
        # user_id → list[WebSocket]
        self._connections: dict[int, list[WebSocket]] = {}
        # job_id → user_id (pour router les messages)
        self._job_subscriptions: dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Accepte une connexion WebSocket.

        Args:
            websocket: Connexion WebSocket
            user_id: ID de l'utilisateur
        """
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}")

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Déconnecte un client WebSocket.

        Args:
            websocket: Connexion WebSocket
            user_id: ID de l'utilisateur
        """
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws != websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}")

    def subscribe_job(self, job_id: str, user_id: int) -> None:
        """
        Abonne un utilisateur aux mises à jour d'un job.

        Args:
            job_id: ID du job
            user_id: ID de l'utilisateur
        """
        self._job_subscriptions[job_id] = user_id

    def unsubscribe_job(self, job_id: str) -> None:
        """
        Désabonne d'un job.

        Args:
            job_id: ID du job
        """
        self._job_subscriptions.pop(job_id, None)

    async def send_to_user(self, user_id: int, message: dict[str, Any]) -> None:
        """
        Envoie un message à tous les WebSocket d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            message: Message à envoyer (sera sérialisé en JSON)
        """
        if user_id not in self._connections:
            return

        disconnected = []
        for ws in self._connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Nettoyer les connexions mortes
        for ws in disconnected:
            self.disconnect(ws, user_id)

    async def broadcast_job_update(self, job_id: str, data: dict[str, Any]) -> None:
        """
        Envoie une mise à jour de job à l'utilisateur abonné.

        Args:
            job_id: ID du job
            data: Données de la mise à jour
        """
        user_id = self._job_subscriptions.get(job_id)
        if user_id is not None:
            await self.send_to_user(
                user_id,
                {"type": "job_update", "job_id": job_id, **data},
            )

    async def broadcast_stream_chunk(
        self, job_id: str, content: str, is_final: bool = False
    ) -> None:
        """
        Envoie un chunk de streaming à l'utilisateur abonné.

        Args:
            job_id: ID du job
            content: Contenu du chunk
            is_final: True si dernier chunk
        """
        user_id = self._job_subscriptions.get(job_id)
        if user_id is not None:
            await self.send_to_user(
                user_id,
                {
                    "type": "stream_chunk",
                    "job_id": job_id,
                    "content": content,
                    "is_final": is_final,
                },
            )


# Instance globale
ws_manager = ConnectionManager()


async def redis_subscriber(redis_client: Any) -> None:
    """
    Écoute Redis pub/sub et dispatche les messages vers les WebSocket.

    Tourne en boucle infinie comme background task de FastAPI.

    Args:
        redis_client: Client Redis async
    """
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("job:*", "stream:*")

    logger.info("Redis subscriber started")

    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue

            try:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()

                data = json.loads(message["data"])

                if channel.startswith("job:"):
                    job_id = channel.split(":", 1)[1]
                    await ws_manager.broadcast_job_update(job_id, data)

                elif channel.startswith("stream:"):
                    job_id = channel.split(":", 1)[1]
                    await ws_manager.broadcast_stream_chunk(
                        job_id,
                        data.get("content", ""),
                        data.get("is_final", False),
                    )

            except Exception as e:
                logger.error(f"Redis subscriber error: {e}")

    except asyncio.CancelledError:
        await pubsub.unsubscribe()
        logger.info("Redis subscriber stopped")
