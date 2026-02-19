"""
Agent Storage — Stockage MinIO cloisonné automatiquement.

Deux modes de cloisonnement:
  - Par utilisateur × agent : users/{user_id}/agents/{agent_slug}/
  - Par workspace × agent  : workspaces/{workspace_id}/agents/{agent_slug}/

Namespace MinIO:
    nova2-storage/
    ├── users/{user_id}/agents/{agent_slug}/
    │   ├── uploads/          ← fichiers uploadés par l'utilisateur
    │   ├── outputs/          ← fichiers générés par l'agent
    │   └── data/             ← données persistantes
    ├── workspaces/{workspace_id}/agents/{agent_slug}/
    │   ├── uploads/          ← fichiers partagés dans le workspace
    │   ├── project/          ← état du projet collaboratif
    │   └── exports/          ← fichiers exportés
    └── platform/
        ├── agents/           ← packages agents (exports)
        └── shared/           ← ressources partagées

L'agent ne connaît JAMAIS le chemin réel. Il écrit juste:
    await context.storage.put("outputs/report.pdf", data)

Le framework traduit automatiquement en:
    workspaces/{workspace_id}/agents/{agent_slug}/outputs/report.pdf
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from minio import Minio

logger = logging.getLogger(__name__)


class AgentStorageManager:
    """
    Gestionnaire de stockage MinIO pour les agents.

    Gère le bucket principal et fournit des instances scopées
    par user × agent via la méthode scoped().
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "nova2-storage",
        secure: bool = False,
    ):
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Crée le bucket s'il n'existe pas."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info(f"MinIO bucket created: {self._bucket}")

    def scoped(
        self,
        user_id: int,
        agent_slug: str,
        workspace_id: Optional[str] = None,
    ) -> ScopedAgentStorage:
        """
        Retourne une instance de stockage scopée.

        Si workspace_id est fourni, le stockage est partagé au niveau
        du workspace (collaboratif). Sinon, il est isolé par utilisateur.

        Args:
            user_id: ID de l'utilisateur
            agent_slug: Slug de l'agent
            workspace_id: ID du workspace (optionnel, pour le mode collaboratif)

        Returns:
            ScopedAgentStorage avec accès limité au namespace approprié
        """
        if workspace_id:
            prefix = f"workspaces/{workspace_id}/agents/{agent_slug}/"
        else:
            prefix = f"users/{user_id}/agents/{agent_slug}/"

        return ScopedAgentStorage(
            client=self._client,
            bucket=self._bucket,
            prefix=prefix,
        )

    def platform_storage(self) -> PlatformStorage:
        """
        Retourne une instance de stockage pour les données plateforme.

        Returns:
            PlatformStorage pour les exports, imports et ressources partagées
        """
        return PlatformStorage(client=self._client, bucket=self._bucket)


class ScopedAgentStorage:
    """
    Stockage MinIO scopé automatiquement.

    Toutes les opérations sont préfixées avec le namespace approprié:
    - users/{user_id}/agents/{agent_slug}/     (mode individuel)
    - workspaces/{workspace_id}/agents/{slug}/ (mode collaboratif)

    L'agent ne peut PAS accéder aux données hors de son scope.
    Les chemins avec '..' ou '/' en début sont rejetés.
    """

    def __init__(self, client: Minio, bucket: str, prefix: str):
        self._client = client
        self._bucket = bucket
        self._prefix = prefix

    def _resolve_key(self, key: str) -> str:
        """
        Résout le chemin complet depuis un chemin relatif.

        Sécurité: bloque les tentatives de path traversal.

        Args:
            key: Chemin relatif (ex: "outputs/report.pdf")

        Returns:
            Chemin complet MinIO

        Raises:
            ValueError: Si le chemin tente un path traversal
        """
        # Nettoyage
        clean_key = key.lstrip("/")

        # Sécurité: bloquer path traversal
        if ".." in clean_key:
            raise ValueError("Path traversal interdit")

        return f"{self._prefix}{clean_key}"

    async def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """
        Stocke un fichier.

        Args:
            key: Chemin relatif (ex: "outputs/report.pdf")
            data: Contenu du fichier
            content_type: Type MIME

        Returns:
            Chemin complet dans MinIO
        """
        full_key = self._resolve_key(key)
        self._client.put_object(
            self._bucket,
            full_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"Storage put: {full_key} ({len(data)} bytes)")
        return full_key

    async def get(self, key: str) -> Optional[bytes]:
        """
        Récupère un fichier.

        Args:
            key: Chemin relatif

        Returns:
            Contenu en bytes ou None si introuvable
        """
        full_key = self._resolve_key(key)
        try:
            response = self._client.get_object(self._bucket, full_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        """
        Supprime un fichier.

        Args:
            key: Chemin relatif

        Returns:
            True si supprimé
        """
        full_key = self._resolve_key(key)
        try:
            self._client.remove_object(self._bucket, full_key)
            logger.info(f"Storage delete: {full_key}")
            return True
        except Exception:
            return False

    async def list(self, prefix: str = "") -> list[str]:
        """
        Liste les fichiers avec un préfixe.

        Args:
            prefix: Sous-chemin (ex: "outputs/")

        Returns:
            Liste des chemins relatifs (sans le préfixe user/agent)
        """
        full_prefix = self._resolve_key(prefix)
        objects = self._client.list_objects(
            self._bucket, prefix=full_prefix, recursive=True
        )
        return [
            obj.object_name[len(self._prefix):]
            for obj in objects
            if not obj.is_dir
        ]

    async def exists(self, key: str) -> bool:
        """
        Vérifie si un fichier existe.

        Args:
            key: Chemin relatif

        Returns:
            True si le fichier existe
        """
        full_key = self._resolve_key(key)
        try:
            self._client.stat_object(self._bucket, full_key)
            return True
        except Exception:
            return False


class PlatformStorage:
    """
    Stockage MinIO pour les données plateforme (exports, imports, shared).

    Préfixe: platform/
    """

    def __init__(self, client: Minio, bucket: str):
        self._client = client
        self._bucket = bucket
        self._prefix = "platform/"

    async def put_export(self, filename: str, data: bytes) -> str:
        """Stocke un export d'agent."""
        key = f"{self._prefix}agents/exports/{filename}"
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type="application/zip",
        )
        return key

    async def get_export(self, filename: str) -> Optional[bytes]:
        """Récupère un export d'agent."""
        key = f"{self._prefix}agents/exports/{filename}"
        try:
            response = self._client.get_object(self._bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception:
            return None

    async def list_exports(self) -> list[str]:
        """Liste les exports disponibles."""
        prefix = f"{self._prefix}agents/exports/"
        objects = self._client.list_objects(self._bucket, prefix=prefix)
        return [obj.object_name.split("/")[-1] for obj in objects if not obj.is_dir]
