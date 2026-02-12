"""
Framework Schemas — Contrats Pydantic partagés par tout le framework.

Ces schemas définissent les types utilisés par:
- Les agents (manifest, messages, réponses)
- Les tools (metadata, résultats)
- Les connecteurs (metadata, actions, résultats)
- Le runtime (jobs, sessions)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class AgentLifecycle(str, Enum):
    """Cycle de vie d'un agent sur la plateforme."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class TriggerType(str, Enum):
    """Types de déclencheurs supportés."""

    USER_MESSAGE = "user_message"
    WEBHOOK = "webhook"
    CRON = "cron"
    EVENT = "event"
    FILE_UPLOAD = "file_upload"


class JobStatus(str, Enum):
    """Statut d'exécution d'un job agent."""

    PENDING = "pending"
    RUNNING = "running"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Rôle dans une conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolExecutionMode(str, Enum):
    """Mode d'exécution d'un tool."""

    SYNC = "sync"
    ASYNC = "async"


class ToolErrorCode(str, Enum):
    """Codes d'erreur standardisés pour les tools."""

    INVALID_PARAMS = "INVALID_PARAMS"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    CONNECTOR_UNAVAILABLE = "CONNECTOR_UNAVAILABLE"


class ConnectorErrorCode(str, Enum):
    """Codes d'erreur standardisés pour les connecteurs."""

    # Configuration
    INVALID_CONFIG = "INVALID_CONFIG"
    INVALID_ACTION = "INVALID_ACTION"
    INVALID_PARAMS = "INVALID_PARAMS"

    # Authentification
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Réseau / service
    CONNECTION_FAILED = "CONNECTION_FAILED"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

    # Internes
    NOT_CONNECTED = "NOT_CONNECTED"
    PROCESSING_ERROR = "PROCESSING_ERROR"


# =============================================================================
# Agent Manifest
# =============================================================================


class AgentDependencies(BaseModel):
    """Dépendances déclarées par un agent."""

    tools: list[str] = Field(default_factory=list, description="Slugs des tools requis")
    connectors: list[str] = Field(
        default_factory=list, description="Slugs des connecteurs requis"
    )


class AgentTrigger(BaseModel):
    """Définition d'un déclencheur d'agent."""

    type: TriggerType
    config: dict[str, Any] = Field(
        default_factory=dict, description="Config spécifique au trigger (ex: cron expression)"
    )


class AgentManifest(BaseModel):
    """
    Manifeste d'un agent — sa carte d'identité.

    Contenu du fichier manifest.json à la racine de chaque package agent.
    """

    name: str = Field(..., description="Nom d'affichage de l'agent")
    slug: str = Field(
        ..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", description="Identifiant unique (kebab-case)"
    )
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Version semver")
    description: str = Field(..., description="Description courte de l'agent")
    author: str = Field(default="", description="Auteur de l'agent")
    icon: str = Field(default="smart_toy", description="Nom d'icône Material Icons")
    category: str = Field(default="general", description="Catégorie de l'agent")
    tags: list[str] = Field(default_factory=list, description="Tags pour la recherche")
    dependencies: AgentDependencies = Field(default_factory=AgentDependencies)
    triggers: list[AgentTrigger] = Field(
        default_factory=lambda: [AgentTrigger(type=TriggerType.USER_MESSAGE)],
        description="Déclencheurs de l'agent",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Capacités requises (file_upload, file_download, streaming)",
    )
    min_platform_version: str = Field(default="1.0.0", description="Version min de la plateforme")


# =============================================================================
# Messages & Réponses
# =============================================================================


class FileAttachment(BaseModel):
    """Pièce jointe à un message."""

    filename: str
    content_type: str
    storage_key: str = Field(description="Clé dans le stockage MinIO")
    size_bytes: int = 0


class UserMessage(BaseModel):
    """Message envoyé par l'utilisateur à un agent."""

    content: str = Field(..., description="Contenu texte du message")
    attachments: list[FileAttachment] = Field(
        default_factory=list, description="Fichiers joints"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Métadonnées supplémentaires"
    )


class AgentResponseChunk(BaseModel):
    """Chunk de réponse pour le streaming."""

    content: str = ""
    is_final: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Réponse complète d'un agent."""

    content: str = Field(..., description="Contenu texte de la réponse")
    attachments: list[FileAttachment] = Field(
        default_factory=list, description="Fichiers générés"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Métadonnées (tokens, durée, etc.)"
    )


# =============================================================================
# Tools
# =============================================================================


class ToolParameter(BaseModel):
    """Paramètre d'un tool."""

    name: str
    type: str = Field(description="Type JSON Schema (string, integer, number, boolean, array, object)")
    description: str = ""
    required: bool = False
    default: Any = None


class ToolExample(BaseModel):
    """Exemple d'utilisation d'un tool."""

    description: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class ToolMetadata(BaseModel):
    """
    Métadonnées auto-descriptives d'un tool.

    Chaque tool expose ses métadonnées pour le registre et la doc auto-générée.
    """

    slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str
    description: str
    version: str = "1.0.0"
    category: str = Field(default="general", description="Catégorie du tool (text, file, data, ai, media, general)")
    execution_mode: ToolExecutionMode = Field(
        default=ToolExecutionMode.SYNC,
        description="Mode d'exécution: sync (direct, 30s) ou async (Celery, progress)",
    )
    timeout_seconds: int = Field(default=30, description="Timeout en secondes (30 sync, 300 async)")
    input_schema: list[ToolParameter] = Field(default_factory=list)
    output_schema: list[ToolParameter] = Field(default_factory=list)
    examples: list[ToolExample] = Field(default_factory=list)
    required_connectors: list[str] = Field(
        default_factory=list,
        description="Slugs des connecteurs requis par ce tool",
    )
    tags: list[str] = Field(default_factory=list, description="Tags pour la recherche")


class ToolResult(BaseModel):
    """Résultat d'exécution d'un tool."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[ToolErrorCode] = Field(
        default=None, description="Code d'erreur standardisé pour le frontend"
    )


class HealthCheckResult(BaseModel):
    """Résultat d'un health check de tool ou connecteur."""

    healthy: bool
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Connectors
# =============================================================================


class ConnectorAction(BaseModel):
    """Action disponible sur un connecteur."""

    name: str = Field(description="Nom de l'action (ex: get_contacts)")
    description: str = ""
    input_schema: list[ToolParameter] = Field(default_factory=list)
    output_schema: list[ToolParameter] = Field(default_factory=list)


class ConnectorMetadata(BaseModel):
    """
    Métadonnées auto-descriptives d'un connecteur.

    Chaque connecteur expose ses métadonnées pour le registre et la doc auto-générée.
    """

    slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str
    description: str
    version: str = "1.0.0"
    category: str = Field(
        default="general",
        description="Catégorie (saas, messaging, storage, database, ai, devops, analytics, finance, general)",
    )
    auth_type: str = Field(
        default="none", description="Type d'auth (none, api_key, oauth2, basic, custom)"
    )
    config_schema: list[ToolParameter] = Field(
        default_factory=list, description="Paramètres de configuration du connecteur"
    )
    actions: list[ConnectorAction] = Field(
        default_factory=list, description="Actions disponibles"
    )
    tags: list[str] = Field(default_factory=list, description="Tags pour la recherche")


class ConnectorResult(BaseModel):
    """Résultat d'exécution d'une action connecteur."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[ConnectorErrorCode] = Field(
        default=None, description="Code d'erreur standardisé"
    )


# =============================================================================
# Jobs & Sessions
# =============================================================================


class JobInfo(BaseModel):
    """Information sur un job d'exécution agent."""

    job_id: str
    agent_slug: str
    user_id: Any
    session_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    progress_message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[AgentResponse] = None
    error: Optional[str] = None


class SessionMessage(BaseModel):
    """Message dans une session de conversation."""

    role: MessageRole
    content: str
    attachments: list[FileAttachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionInfo(BaseModel):
    """Information sur une session de conversation."""

    session_id: str
    agent_slug: str
    user_id: Any
    title: str = ""
    messages: list[SessionMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


# =============================================================================
# Export / Import
# =============================================================================


class AgentPackageInfo(BaseModel):
    """
    Métadonnées du package d'export d'un agent.

    Le ZIP contient:
        manifest.json
        backend/
            agent.py
            prompts/
                system.md
        frontend/
            index.tsx
            components/
            styles.ts
    """

    format_version: str = Field(default="aisome-agent-v1", description="Version du format de package")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    platform_version: str = Field(default="1.0.0")
    manifest: AgentManifest
