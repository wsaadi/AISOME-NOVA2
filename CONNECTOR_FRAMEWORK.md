# CONNECTOR FRAMEWORK — Guide de conception et développement des Connecteurs

> Ce document est la référence unique pour créer des connecteurs sur la plateforme AISOME-NOVA2.
> Il est utilisé aussi bien par les développeurs humains que par Claude Code en vibe coding.

---

## Table des matières

1. [Principes fondamentaux](#1-principes-fondamentaux)
2. [Architecture](#2-architecture)
3. [Tool vs Connecteur — La frontière](#3-tool-vs-connecteur--la-frontière)
4. [Créer un connecteur — Quick Start](#4-créer-un-connecteur--quick-start)
5. [Structure d'un connecteur](#5-structure-dun-connecteur)
6. [BaseConnector — Contrat complet](#6-baseconnector--contrat-complet)
7. [ConnectorMetadata — Carte d'identité](#7-connectormetadata--carte-didentité)
8. [ConnectorAction — Contrat d'action](#8-connectoraction--contrat-daction)
9. [ConnectorResult — Réponse standardisée](#9-connectorresult--réponse-standardisée)
10. [Types d'authentification](#10-types-dauthentification)
11. [Gestion des credentials (Vault)](#11-gestion-des-credentials-vault)
12. [Cycle de vie d'une connexion](#12-cycle-de-vie-dune-connexion)
13. [Gestion des erreurs](#13-gestion-des-erreurs)
14. [Résilience (retry, circuit breaker, timeout)](#14-résilience-retry-circuit-breaker-timeout)
15. [Health check](#15-health-check)
16. [Catégories](#16-catégories)
17. [Sécurité — Règles absolues](#17-sécurité--règles-absolues)
18. [Validateur de connecteur](#18-validateur-de-connecteur)
19. [Tests unitaires](#19-tests-unitaires)
20. [API REST](#20-api-rest)
21. [Générateur de connecteur (CLI)](#21-générateur-de-connecteur-cli)
22. [Checklist de validation](#22-checklist-de-validation)
23. [Exemples complets](#23-exemples-complets)

---

## 1. Principes fondamentaux

| Principe | Règle |
|---|---|
| **Connecteur = seule porte vers l'extérieur** | Tout appel à un service externe passe par un connecteur. RIEN d'autre dans la plateforme ne fait d'appel réseau sortant (sauf LLMService). |
| **Secrets dans Vault uniquement** | Jamais de credentials en dur. Le framework récupère les secrets depuis Vault et les injecte dans `connect()`. |
| **Auto-descriptif** | Chaque connecteur porte toutes ses metadata : actions, schemas I/O, type d'auth, config requise. |
| **Auto-découvert** | Poser un fichier `.py` dans `connectors/` = le connecteur existe. Supprimer = il disparaît. |
| **Action-based** | Un connecteur expose des actions nommées (`get_contacts`, `send_email`), chacune avec son propre schema I/O. |
| **Connexion gérée par le framework** | `connect()` et `disconnect()` sont appelés par le framework, jamais par l'agent ou le tool directement. |
| **Isolation des erreurs** | Une erreur dans un connecteur ne crash pas l'agent. Le résultat est toujours un `ConnectorResult`. |
| **Pas de logique métier** | Un connecteur transporte des données. Il ne transforme pas, ne calcule pas. C'est le rôle du tool. |

---

## 2. Architecture

```
Agent / Tool
  │
  ├── context.connectors.execute("salesforce", "get_contacts", {limit: 10})
  │       │
  │       ▼
  │   ConnectorRegistry (auto-discovery)
  │       │
  │       ├── validate_action()           ← L'action existe-t-elle ?
  │       ├── is_connected()              ← Le connecteur est-il connecté ?
  │       └── connector.execute()         ← Appel au service externe
  │             │
  │             ├── httpx.AsyncClient      ← HTTP sortant (seul autorisé ici)
  │             ├── SDK natif              ← SDK du service (boto3, google-cloud, etc.)
  │             └── Protocoles directs     ← SMTP, IMAP, WebSocket, gRPC...
  │
  └── ConnectorResult {success, data, error, error_code}

Lifecycle:
  ┌──────────────────────────────────────────────────────────────────┐
  │ Session Agent                                                    │
  │                                                                  │
  │  1. Framework récupère config depuis Vault                       │
  │  2. connector.connect(config) — une seule fois                   │
  │  3. connector.execute(action, params) — N fois                   │
  │  4. connector.disconnect() — en fin de session                   │
  └──────────────────────────────────────────────────────────────────┘
```

### Flux de données complet

```
Vault (secrets)
  │
  ▼
ConnectorRegistry.connect(slug, config)
  │
  ▼
BaseConnector.connect(config)      ← Initialise le client HTTP/SDK
  │
  ▼
BaseConnector.execute(action, params)  ← Appels répétés
  │
  ├── Service externe (API REST, GraphQL, SOAP, gRPC...)
  │
  ▼
ConnectorResult {success, data, error, error_code}
  │
  ▼
Tool / Agent reçoit le résultat
```

---

## 3. Tool vs Connecteur — La frontière

C'est **LA** question architecturale centrale. Voici la règle de décision :

| Critère | **Tool** | **Connecteur** |
|---|---|---|
| **Rôle** | Transformer, calculer, traiter des données | Se connecter à un service externe |
| **Réseau** | JAMAIS d'appel externe direct | Seul composant autorisé à sortir |
| **Secrets** | AUCUN | API keys, OAuth tokens (via Vault) |
| **Exemples** | Parser CSV, générer PDF, résumer texte | Salesforce API, Google Drive, Slack, SMTP |
| **Testabilité** | 100% mockable, zéro dépendance | Nécessite credentials ou mock HTTP |
| **Dépendance réseau** | Non | Oui |
| **Stateful** | Non (exécution atomique) | Oui (connexion persistante en session) |
| **Imports autorisés** | Libs de traitement (docx, csv, etc.) | Libs réseau (httpx, boto3, google-cloud) |

### Règle d'or

> **Si ça nécessite un réseau, un secret, ou une authentification → c'est un connecteur.**
> **Si ça transforme des données en mémoire → c'est un tool.**

### Collaboration Tool ↔ Connecteur

Un tool peut déléguer l'accès externe à un connecteur via `context.connectors.execute()` :

```python
# Dans un tool : récupérer des données externes via un connecteur
async def execute(self, params, context):
    # 1. Récupérer via connecteur
    result = await context.connectors.execute(
        "salesforce", "get_contacts", {"limit": 50}
    )
    if not result.success:
        return self.error(result.error, ToolErrorCode.EXTERNAL_API_ERROR)

    # 2. Transformer (rôle du tool)
    contacts = result.data["contacts"]
    csv_output = self._contacts_to_csv(contacts)

    # 3. Stocker le résultat
    await context.storage.put("outputs/contacts.csv", csv_output, "text/csv")
    return self.success({"storage_key": "outputs/contacts.csv", "count": len(contacts)})
```

---

## 4. Créer un connecteur — Quick Start

### Méthode 1 : Créer le fichier manuellement

```bash
# Créer le fichier
touch backend/app/framework/connectors/slack.py

# Coder le connecteur (voir structure ci-dessous)

# C'est tout. Le registre le découvre automatiquement au démarrage.
```

### Méthode 2 : Générateur CLI (recommandé)

```bash
python -m app.framework.connectors.generator slack "Slack" "Intégration Slack pour envoyer/lire des messages" messaging api_key

# Génère :
#   backend/app/framework/connectors/slack.py      (template)
#   backend/tests/connectors/test_slack.py          (tests unitaires)
```

### Méthode 3 : Copier un connecteur existant

Copier un connecteur du même type d'auth et adapter.

---

## 5. Structure d'un connecteur

### Fichier unique

```
backend/app/framework/connectors/
├── registry.py           ← Framework (NE PAS MODIFIER)
├── generator.py          ← CLI de génération (NE PAS MODIFIER)
├── __init__.py
├── slack.py              ← Un connecteur = un fichier
├── salesforce.py
├── google_drive.py
├── smtp_email.py
└── postgresql.py
```

### Template minimal

```python
"""
Slack — Connecteur pour l'API Slack (envoyer/lire des messages, channels).

Catégorie: messaging
Auth: api_key

Actions:
    send_message     → Envoie un message dans un channel
    list_channels    → Liste les channels disponibles
    get_messages     → Récupère les messages d'un channel
"""

from __future__ import annotations
from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)


class SlackConnector(BaseConnector):
    """Connecteur Slack via Bot Token API."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="slack",
            name="Slack",
            description="Envoyer et lire des messages Slack",
            version="1.0.0",
            category="messaging",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="bot_token", type="string", required=True,
                              description="Slack Bot User OAuth Token (xoxb-...)"),
                ToolParameter(name="default_channel", type="string",
                              description="Channel par défaut"),
            ],
            actions=[
                ConnectorAction(
                    name="send_message",
                    description="Envoie un message dans un channel Slack",
                    input_schema=[
                        ToolParameter(name="channel", type="string", required=True),
                        ToolParameter(name="text", type="string", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="ts", type="string", description="Timestamp du message"),
                        ToolParameter(name="channel", type="string"),
                    ],
                ),
                ConnectorAction(
                    name="list_channels",
                    description="Liste les channels Slack accessibles",
                    input_schema=[
                        ToolParameter(name="limit", type="integer", default=100),
                    ],
                    output_schema=[
                        ToolParameter(name="channels", type="array"),
                    ],
                ),
            ],
            tags=["messaging", "slack", "chat", "notifications"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client HTTP avec le Bot Token."""
        import httpx
        self._token = config["bot_token"]
        self._default_channel = config.get("default_channel", "")
        self._client = httpx.AsyncClient(
            base_url="https://slack.com/api",
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30.0,
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "send_message":
            return await self._send_message(params)
        elif action == "list_channels":
            return await self._list_channels(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client HTTP."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Vérifie que le token est valide."""
        resp = await self._client.post("auth.test")
        return resp.json().get("ok", False)

    # --- Actions privées ---

    async def _send_message(self, params: dict[str, Any]) -> ConnectorResult:
        channel = params.get("channel", self._default_channel)
        text = params.get("text", "")
        resp = await self._client.post("chat.postMessage", json={
            "channel": channel, "text": text,
        })
        data = resp.json()
        if not data.get("ok"):
            return self.error(
                f"Slack API error: {data.get('error', 'unknown')}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        return self.success({"ts": data["ts"], "channel": data["channel"]})

    async def _list_channels(self, params: dict[str, Any]) -> ConnectorResult:
        limit = params.get("limit", 100)
        resp = await self._client.get("conversations.list", params={"limit": limit})
        data = resp.json()
        if not data.get("ok"):
            return self.error(
                f"Slack API error: {data.get('error', 'unknown')}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        channels = [
            {"id": ch["id"], "name": ch["name"], "topic": ch.get("topic", {}).get("value", "")}
            for ch in data.get("channels", [])
        ]
        return self.success({"channels": channels, "count": len(channels)})
```

---

## 6. BaseConnector — Contrat complet

```python
class BaseConnector(ABC):
    """Classe abstraite de base pour tous les connecteurs."""

    # --- OBLIGATOIRE ---

    @property
    @abstractmethod
    def metadata(self) -> ConnectorMetadata:
        """Retourne les métadonnées auto-descriptives."""
        ...

    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> None:
        """
        Initialise la connexion au service externe.

        Appelé UNE SEULE FOIS par session, par le framework.
        Les credentials viennent de Vault, injectées dans `config`.

        Args:
            config: Configuration (URL, tokens, paramètres...)
        """
        ...

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        """
        Exécute une action sur le service externe.

        Appelé N FOIS pendant la session.

        Args:
            action: Nom de l'action (doit être dans metadata.actions)
            params: Paramètres de l'action (validés contre le schema)

        Returns:
            ConnectorResult {success, data, error, error_code}
        """
        ...

    # --- OPTIONNEL (override possible) ---

    async def disconnect(self) -> None:
        """Ferme proprement la connexion. Appelé par le framework en fin de session."""
        pass

    async def health_check(self) -> bool:
        """Vérifie que le service externe est accessible. True = OK."""
        return True

    # --- HELPERS FOURNIS PAR LA CLASSE DE BASE ---

    def get_available_actions(self) -> list[str]:
        """Retourne les noms d'actions disponibles."""
        return [action.name for action in self.metadata.actions]

    def validate_action(self, action: str) -> bool:
        """Vérifie qu'une action existe dans les actions déclarées."""
        return action in self.get_available_actions()

    def success(self, data: dict) -> ConnectorResult:
        """Helper : retourne un résultat de succès."""
        return ConnectorResult(success=True, data=data)

    def error(self, message: str, code: ConnectorErrorCode = None) -> ConnectorResult:
        """Helper : retourne un résultat d'erreur."""
        return ConnectorResult(success=False, error=message, error_code=code)
```

### Méthodes obligatoires vs optionnelles

| Méthode | Obligatoire | Appelée par |
|---|---|---|
| `metadata` | Oui | Registre au chargement |
| `connect(config)` | Oui | Framework au premier usage dans la session |
| `execute(action, params)` | Oui | Tools/Agents via `context.connectors.execute()` |
| `disconnect()` | Non | Framework en fin de session |
| `health_check()` | Non | API `/api/connectors/health` |

---

## 7. ConnectorMetadata — Carte d'identité

```python
class ConnectorMetadata(BaseModel):
    # --- Identité ---
    slug: str               # kebab-case unique (ex: "salesforce", "google-drive")
    name: str               # Nom d'affichage (ex: "Salesforce CRM")
    description: str        # Description courte
    version: str = "1.0.0"  # Semver

    # --- Classification ---
    category: str = "general"   # Catégorie (voir §16)
    tags: list[str] = []        # Tags de recherche

    # --- Authentification ---
    auth_type: str = "none"     # none | api_key | oauth2 | basic | custom

    # --- Configuration ---
    config_schema: list[ToolParameter] = []  # Paramètres de connexion

    # --- Actions ---
    actions: list[ConnectorAction] = []      # Actions exposées
```

### Règles de nommage

| Champ | Règle | Exemples |
|---|---|---|
| `slug` | kebab-case, 3-40 chars, unique | `slack`, `google-drive`, `salesforce-crm` |
| `name` | Titre capitalisé, nom officiel du service | `Slack`, `Google Drive`, `Salesforce CRM` |
| `version` | Semver strict | `1.0.0`, `2.1.3` |
| `auth_type` | Enum stricte | `none`, `api_key`, `oauth2`, `basic`, `custom` |
| `category` | Enum (voir §16) | `saas`, `database`, `messaging`, `storage` |

---

## 8. ConnectorAction — Contrat d'action

Chaque action est un mini-contrat avec ses propres schemas I/O :

```python
class ConnectorAction(BaseModel):
    name: str                                    # Identifiant unique (snake_case)
    description: str = ""                        # Description de l'action
    input_schema: list[ToolParameter] = []       # Paramètres d'entrée
    output_schema: list[ToolParameter] = []      # Structure de sortie
```

### Conventions de nommage des actions

| Pattern | Signification | Exemples |
|---|---|---|
| `get_*` | Récupérer une ressource | `get_contacts`, `get_file`, `get_user` |
| `list_*` | Lister des ressources | `list_channels`, `list_files`, `list_emails` |
| `create_*` | Créer une ressource | `create_lead`, `create_folder`, `create_ticket` |
| `update_*` | Modifier une ressource | `update_contact`, `update_status` |
| `delete_*` | Supprimer une ressource | `delete_file`, `delete_message` |
| `send_*` | Envoyer (message, email, notif) | `send_message`, `send_email`, `send_notification` |
| `search_*` | Rechercher | `search_contacts`, `search_files` |
| `execute_*` | Exécuter (requête, query) | `execute_query`, `execute_command` |

### Exemple complet d'actions

```python
actions=[
    ConnectorAction(
        name="get_contacts",
        description="Récupère les contacts depuis Salesforce",
        input_schema=[
            ToolParameter(name="limit", type="integer", default=50,
                          description="Nombre max de contacts"),
            ToolParameter(name="query", type="string",
                          description="Filtre SOQL optionnel"),
        ],
        output_schema=[
            ToolParameter(name="contacts", type="array",
                          description="Liste des contacts"),
            ToolParameter(name="total_count", type="integer"),
            ToolParameter(name="has_more", type="boolean"),
        ],
    ),
    ConnectorAction(
        name="create_lead",
        description="Crée un nouveau lead dans Salesforce",
        input_schema=[
            ToolParameter(name="first_name", type="string", required=True),
            ToolParameter(name="last_name", type="string", required=True),
            ToolParameter(name="email", type="string", required=True),
            ToolParameter(name="company", type="string"),
        ],
        output_schema=[
            ToolParameter(name="lead_id", type="string"),
            ToolParameter(name="created", type="boolean"),
        ],
    ),
]
```

---

## 9. ConnectorResult — Réponse standardisée

```python
class ConnectorResult(BaseModel):
    success: bool = True
    data: dict[str, Any] = {}
    error: Optional[str] = None
    error_code: Optional[ConnectorErrorCode] = None
```

### ConnectorErrorCode — Codes d'erreur standardisés

```python
class ConnectorErrorCode(str, Enum):
    # Erreurs de configuration
    INVALID_CONFIG       = "INVALID_CONFIG"        # Config manquante/invalide
    INVALID_ACTION       = "INVALID_ACTION"         # Action inexistante
    INVALID_PARAMS       = "INVALID_PARAMS"         # Paramètres invalides

    # Erreurs d'authentification
    AUTH_FAILED          = "AUTH_FAILED"             # Credentials invalides
    TOKEN_EXPIRED        = "TOKEN_EXPIRED"           # Token expiré (OAuth2)
    PERMISSION_DENIED    = "PERMISSION_DENIED"       # Pas les droits

    # Erreurs réseau / service
    CONNECTION_FAILED    = "CONNECTION_FAILED"       # Impossible de se connecter
    TIMEOUT              = "TIMEOUT"                 # Timeout réseau
    RATE_LIMITED         = "RATE_LIMITED"             # Rate limit du service externe
    EXTERNAL_API_ERROR   = "EXTERNAL_API_ERROR"      # Erreur API du service

    # Erreurs internes
    NOT_CONNECTED        = "NOT_CONNECTED"           # connect() pas encore appelé
    PROCESSING_ERROR     = "PROCESSING_ERROR"        # Erreur interne au connecteur
```

### Utilisation des helpers

```python
# Succès
return self.success({"contacts": contacts, "count": len(contacts)})

# Erreur
return self.error("Rate limit exceeded, retry after 60s", ConnectorErrorCode.RATE_LIMITED)
return self.error("Invalid API key", ConnectorErrorCode.AUTH_FAILED)
return self.error(f"HTTP {resp.status_code}: {resp.text}", ConnectorErrorCode.EXTERNAL_API_ERROR)
```

---

## 10. Types d'authentification

### `none` — Pas d'authentification

APIs publiques, services internes sans auth.

```python
auth_type="none"
config_schema=[]  # Pas de config nécessaire
```

### `api_key` — Clé d'API simple

Le cas le plus courant. Une clé secrète envoyée dans un header ou query param.

```python
auth_type="api_key"
config_schema=[
    ToolParameter(name="api_key", type="string", required=True,
                  description="Clé d'API du service"),
    ToolParameter(name="base_url", type="string",
                  description="URL de base (pour instances self-hosted)"),
]
```

```python
async def connect(self, config):
    import httpx
    self._client = httpx.AsyncClient(
        base_url=config.get("base_url", "https://api.service.com"),
        headers={"X-API-Key": config["api_key"]},
        timeout=30.0,
    )
```

### `oauth2` — OAuth 2.0

Pour les services nécessitant un flow OAuth (Google, Microsoft, Salesforce...).

```python
auth_type="oauth2"
config_schema=[
    ToolParameter(name="client_id", type="string", required=True),
    ToolParameter(name="client_secret", type="string", required=True),
    ToolParameter(name="refresh_token", type="string", required=True),
    ToolParameter(name="token_url", type="string", required=True,
                  description="URL de rafraîchissement du token"),
    ToolParameter(name="scopes", type="string",
                  description="Scopes OAuth séparés par espaces"),
]
```

```python
async def connect(self, config):
    import httpx
    self._config = config
    self._client = httpx.AsyncClient(timeout=30.0)
    await self._refresh_access_token()

async def _refresh_access_token(self):
    """Rafraîchit le access token via le refresh token."""
    resp = await self._client.post(self._config["token_url"], data={
        "grant_type": "refresh_token",
        "client_id": self._config["client_id"],
        "client_secret": self._config["client_secret"],
        "refresh_token": self._config["refresh_token"],
    })
    data = resp.json()
    self._access_token = data["access_token"]
    self._client.headers["Authorization"] = f"Bearer {self._access_token}"
```

### `basic` — HTTP Basic Auth

```python
auth_type="basic"
config_schema=[
    ToolParameter(name="username", type="string", required=True),
    ToolParameter(name="password", type="string", required=True),
    ToolParameter(name="base_url", type="string", required=True),
]
```

```python
async def connect(self, config):
    import httpx
    self._client = httpx.AsyncClient(
        base_url=config["base_url"],
        auth=(config["username"], config["password"]),
        timeout=30.0,
    )
```

### `custom` — Authentification personnalisée

Pour les protocoles non-standard (certificats TLS, HMAC signatures, etc.).

```python
auth_type="custom"
config_schema=[
    # Définir les paramètres spécifiques
]
```

---

## 11. Gestion des credentials (Vault)

### Principe

Les credentials ne transitent **jamais** dans le code d'un connecteur. Le framework :

1. Récupère la config depuis **HashiCorp Vault**
2. L'injecte dans `connect(config)` du connecteur
3. Le connecteur utilise `config["api_key"]` etc. sans jamais connaître Vault

### Structure Vault

```
nova2/                                    ← Mount point KV v2
├── llm-providers/                        ← Providers LLM (existant)
│   ├── openai/       {api_key: "sk-..."}
│   └── anthropic/    {api_key: "sk-ant-..."}
│
└── connectors/                           ← Connecteurs (nouveau)
    ├── slack/        {bot_token: "xoxb-...", default_channel: "#general"}
    ├── salesforce/   {client_id: "...", client_secret: "...", refresh_token: "..."}
    ├── google-drive/ {client_id: "...", client_secret: "...", refresh_token: "..."}
    └── smtp-email/   {host: "smtp.gmail.com", username: "...", password: "..."}
```

### API VaultService étendue

```python
class VaultService:
    # Existant (LLM providers)
    def store_api_key(provider_slug, api_key) -> bool
    def get_api_key(provider_slug) -> Optional[str]

    # Nouveau (Connecteurs)
    def store_connector_config(connector_slug: str, config: dict) -> bool
    def get_connector_config(connector_slug: str) -> Optional[dict]
    def delete_connector_config(connector_slug: str) -> bool
    def has_connector_config(connector_slug: str) -> bool
```

### Flux d'initialisation

```
1. Agent démarre une session
2. Agent appelle context.connectors.execute("slack", "send_message", {...})
3. Framework détecte: "slack" pas encore connecté
4. Framework → Vault: get_connector_config("slack")
5. Framework → connector.connect(config_from_vault)
6. Framework → connector.execute("send_message", params)
7. Retour ConnectorResult à l'agent
```

### Configuration admin (UI)

L'admin configure les credentials via l'interface NOVA2 :

```
POST /api/admin/connectors/{slug}/config
{
    "bot_token": "xoxb-...",
    "default_channel": "#general"
}
→ Stocké dans Vault, jamais en DB
```

---

## 12. Cycle de vie d'une connexion

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  REGISTERED ──▶ CONNECTING ──▶ CONNECTED ──▶ DISCONNECTING  │
│       │              │              │              │         │
│       │              ▼              │              ▼         │
│       │           ERROR             │         DISCONNECTED   │
│       │              │              │                        │
│       └──────────────┴──────────────┘                        │
│                                                              │
│  • REGISTERED : Fichier .py découvert, metadata chargée      │
│  • CONNECTING : connect(config) en cours                     │
│  • CONNECTED  : Prêt à execute()                             │
│  • ERROR      : connect() a échoué                           │
│  • DISCONNECTING : disconnect() en cours                     │
│  • DISCONNECTED  : Connexion fermée proprement               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Règles du cycle de vie

| Règle | Détail |
|---|---|
| **connect() une seule fois** | Par session agent. Le framework ne rappelle pas connect() si déjà connecté. |
| **execute() N fois** | Autant d'appels que nécessaire pendant la session. |
| **disconnect() automatique** | Le framework appelle disconnect() en fin de session ou si l'agent crash. |
| **Lazy connection** | connect() est appelé au premier execute(), pas au démarrage de la session. |
| **Reconnect on error** | Si execute() échoue avec CONNECTION_FAILED, le framework peut retenter connect(). |

---

## 13. Gestion des erreurs

### Règle : ne jamais lever d'exception

Un connecteur ne **raise** jamais. Il retourne toujours un `ConnectorResult` :

```python
async def _send_message(self, params):
    try:
        resp = await self._client.post("chat.postMessage", json=params)
        data = resp.json()

        if resp.status_code == 429:
            return self.error("Rate limited", ConnectorErrorCode.RATE_LIMITED)

        if resp.status_code == 401:
            return self.error("Token expired", ConnectorErrorCode.TOKEN_EXPIRED)

        if not data.get("ok"):
            return self.error(
                f"Slack error: {data.get('error')}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )

        return self.success({"ts": data["ts"], "channel": data["channel"]})

    except httpx.TimeoutException:
        return self.error("Timeout calling Slack API", ConnectorErrorCode.TIMEOUT)
    except httpx.ConnectError:
        return self.error("Cannot reach Slack API", ConnectorErrorCode.CONNECTION_FAILED)
    except Exception as e:
        return self.error(f"Unexpected error: {str(e)}", ConnectorErrorCode.PROCESSING_ERROR)
```

### Mapping HTTP → ConnectorErrorCode

| HTTP Status | ConnectorErrorCode |
|---|---|
| 400 | `INVALID_PARAMS` |
| 401 | `AUTH_FAILED` |
| 403 | `PERMISSION_DENIED` |
| 404 | `EXTERNAL_API_ERROR` (ressource not found) |
| 429 | `RATE_LIMITED` |
| 500+ | `EXTERNAL_API_ERROR` |
| Timeout | `TIMEOUT` |
| Connection refused | `CONNECTION_FAILED` |

---

## 14. Résilience (retry, circuit breaker, timeout)

### Timeout

Le framework encapsule chaque appel execute() dans un timeout :

```python
# Framework (pipeline.py) — PAS dans le connecteur
import asyncio
result = await asyncio.wait_for(
    connector.execute(action, params),
    timeout=60.0  # 60s par défaut pour les connecteurs
)
```

Le connecteur peut aussi avoir ses propres timeouts internes (HTTP client timeout), qui doivent être **inférieurs** au timeout framework.

### Retry (dans le connecteur)

Le connecteur gère ses propres retries pour les erreurs transientes :

```python
async def _call_with_retry(self, method, url, **kwargs):
    """Appel HTTP avec retry exponentiel."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = await self._client.request(method, url, **kwargs)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                await asyncio.sleep(retry_after)
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise httpx.TimeoutException("Max retries exceeded")
```

### Circuit Breaker (optionnel, dans le connecteur)

Pour les connecteurs appelés très fréquemment :

```python
def __init__(self):
    self._failure_count = 0
    self._circuit_open = False
    self._last_failure_time = 0

async def execute(self, action, params):
    if self._circuit_open:
        # Vérifier si assez de temps s'est écoulé pour re-tenter
        if time.time() - self._last_failure_time < 30:  # 30s cooldown
            return self.error("Circuit breaker open", ConnectorErrorCode.CONNECTION_FAILED)
        self._circuit_open = False

    result = await self._do_execute(action, params)

    if not result.success and result.error_code in (
        ConnectorErrorCode.CONNECTION_FAILED,
        ConnectorErrorCode.TIMEOUT,
    ):
        self._failure_count += 1
        if self._failure_count >= 5:
            self._circuit_open = True
            self._last_failure_time = time.time()
    else:
        self._failure_count = 0

    return result
```

---

## 15. Health check

### Dans le connecteur

```python
async def health_check(self) -> bool:
    """Vérifie que le service externe est accessible et les credentials valides."""
    try:
        resp = await self._client.get("api/healthz")
        return resp.status_code == 200
    except Exception:
        return False
```

### Via l'API

```
GET /api/connectors/health
→ {"slack": true, "salesforce": false, "google-drive": true}

GET /api/connectors/{slug}/health
→ {"healthy": true, "message": "OK", "details": {"latency_ms": 142}}
```

---

## 16. Catégories

| Catégorie | Description | Exemples |
|---|---|---|
| `saas` | Applications SaaS tierces | Salesforce, HubSpot, Jira, Notion |
| `messaging` | Communication et messagerie | Slack, Teams, Discord, SMTP, Twilio |
| `storage` | Stockage cloud et fichiers | Google Drive, OneDrive, S3, Dropbox |
| `database` | Bases de données externes | PostgreSQL, MySQL, MongoDB, Elasticsearch |
| `ai` | Services IA externes | OpenAI, Hugging Face, Google AI |
| `devops` | CI/CD et infrastructure | GitHub, GitLab, Jenkins, Docker |
| `analytics` | Analytics et monitoring | Google Analytics, Mixpanel, Datadog |
| `finance` | Services financiers | Stripe, PayPal, QuickBooks |
| `general` | Autres intégrations | Webhooks, APIs REST génériques |

---

## 17. Sécurité — Règles absolues

### Ce qu'un connecteur PEUT faire

| Autorisé | Pourquoi |
|---|---|
| `import httpx` | C'est sa raison d'être : appeler l'extérieur |
| `import boto3`, SDK cloud | Idem |
| Stocker un client HTTP en `self._client` | Connexion persistante en session |
| Lire `config["api_key"]` | Injecté par Vault via le framework |

### Ce qu'un connecteur NE PEUT PAS faire

| Interdit | Pourquoi |
|---|---|
| Credentials en dur | `api_key = "sk-..."` → REJETÉ par le validateur |
| `import os`, `subprocess` | Pas d'accès système |
| `open()`, `pathlib` | Pas d'accès filesystem |
| Modifier `self.metadata` au runtime | Metadata immutable après chargement |
| Appeler d'autres connecteurs | Isolation — un connecteur = un service |
| Importer des models SQLAlchemy | Pas d'accès DB directe |
| Logger des credentials | Le framework détecte et bloque |

### Validation AST spécifique connecteurs

```python
CONNECTOR_FORBIDDEN_IMPORTS = {
    "os", "subprocess", "shutil", "pathlib",
    "sqlite3", "psycopg2", "asyncpg",     # Pas de DB directe
    "sqlalchemy",                           # Pas d'ORM
    "redis", "celery",                      # Pas d'infra directe
    "minio",                                # Pas de MinIO direct
}

# NOTER : httpx, requests, boto3 sont AUTORISÉS dans les connecteurs
CONNECTOR_ALLOWED_NETWORK = {
    "httpx", "requests", "aiohttp",         # HTTP clients
    "boto3", "botocore",                    # AWS SDK
    "google.cloud", "google.oauth2",        # Google Cloud
    "slack_sdk",                            # Slack SDK
    "twilio",                               # Twilio
}

CONNECTOR_FORBIDDEN_BUILTINS = {
    "open", "exec", "eval", "compile",
    "__import__", "globals", "locals",
}
```

---

## 18. Validateur de connecteur

Le validateur vérifie au chargement :

```python
class ConnectorValidator:
    """Valide un fichier connecteur avant enregistrement."""

    def validate(self, py_file: Path) -> ValidationResult:
        # 1. Parse l'AST
        # 2. Vérifie qu'une classe étend BaseConnector
        # 3. Vérifie metadata, connect(), execute() sont implémentés
        # 4. Vérifie les imports interdits (CONNECTOR_FORBIDDEN_IMPORTS)
        # 5. Vérifie les builtins interdits (open, exec, eval)
        # 6. Détecte les credentials en dur
        # 7. Vérifie les conventions de nommage
        # 8. Vérifie que disconnect() ferme proprement les ressources
```

### Erreurs détectées

| Code | Description |
|---|---|
| `NO_BASE_CONNECTOR` | Aucune classe n'étend BaseConnector |
| `NO_METADATA` | Propriété metadata manquante |
| `NO_CONNECT` | Méthode connect() manquante |
| `NO_EXECUTE` | Méthode execute() manquante |
| `FORBIDDEN_IMPORT` | Import interdit détecté |
| `FORBIDDEN_CALL` | Appel builtin interdit (open, exec...) |
| `HARDCODED_CREDENTIALS` | Credentials en dur détectés |
| `INVALID_SLUG` | Slug non conforme (doit être kebab-case) |
| `NO_ACTIONS` | Aucune action déclarée dans metadata |
| `MISSING_CONFIG_SCHEMA` | auth_type != "none" mais config_schema vide |

---

## 19. Tests unitaires

### MockConnectorClient

Pour tester un connecteur sans service externe réel :

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.framework.connectors.slack import SlackConnector
from app.framework.schemas import ConnectorResult


class TestSlackConnector:
    """Tests pour le connecteur Slack."""

    @pytest.fixture
    async def connector(self):
        """Crée un connecteur connecté avec un client mocké."""
        connector = SlackConnector()
        connector._client = AsyncMock()
        connector._token = "xoxb-test-token"
        connector._default_channel = "#test"
        return connector

    async def test_metadata(self):
        """Vérifie les métadonnées."""
        connector = SlackConnector()
        meta = connector.metadata
        assert meta.slug == "slack"
        assert meta.auth_type == "api_key"
        assert len(meta.actions) >= 2
        assert "send_message" in connector.get_available_actions()

    async def test_send_message_success(self, connector):
        """Test envoi de message réussi."""
        connector._client.post.return_value = MagicMock(
            json=lambda: {"ok": True, "ts": "123.456", "channel": "C123"}
        )

        result = await connector.execute("send_message", {
            "channel": "#general",
            "text": "Hello!",
        })

        assert result.success
        assert result.data["ts"] == "123.456"

    async def test_send_message_rate_limited(self, connector):
        """Test rate limiting."""
        connector._client.post.return_value = MagicMock(
            status_code=429,
            json=lambda: {"ok": False, "error": "rate_limited"},
        )

        result = await connector.execute("send_message", {
            "channel": "#general",
            "text": "Hello!",
        })

        assert not result.success
        assert result.error_code == ConnectorErrorCode.RATE_LIMITED

    async def test_invalid_action(self, connector):
        """Test action invalide."""
        result = await connector.execute("nonexistent_action", {})
        assert not result.success

    async def test_health_check(self, connector):
        """Test health check."""
        connector._client.post.return_value = MagicMock(
            json=lambda: {"ok": True}
        )
        assert await connector.health_check()

    async def test_disconnect(self, connector):
        """Test déconnexion propre."""
        await connector.disconnect()
        connector._client.aclose.assert_called_once()
```

### Lancer les tests

```bash
# Un connecteur
pytest tests/connectors/test_slack.py -v

# Tous les connecteurs
pytest tests/connectors/ -v

# Avec couverture
pytest tests/connectors/ --cov=app.framework.connectors -v
```

---

## 20. API REST

### Endpoints

```
GET    /api/connectors                      ← Catalogue complet
GET    /api/connectors/health               ← Santé de tous les connecteurs
GET    /api/connectors/{slug}               ← Détail + schema complet
GET    /api/connectors/{slug}/actions       ← Actions disponibles
POST   /api/connectors/{slug}/connect       ← Initialiser la connexion (admin)
POST   /api/connectors/{slug}/execute       ← Exécuter une action
POST   /api/connectors/{slug}/disconnect    ← Fermer la connexion
GET    /api/connectors/{slug}/health        ← Santé d'un connecteur

# Admin — gestion des credentials
POST   /api/admin/connectors/{slug}/config  ← Stocker config dans Vault
GET    /api/admin/connectors/{slug}/config  ← Vérifier si config existe (pas le contenu!)
DELETE /api/admin/connectors/{slug}/config  ← Supprimer config
```

### Exemple : Exécuter une action

```
POST /api/connectors/slack/execute
Authorization: Bearer <jwt>
Content-Type: application/json

{
    "action": "send_message",
    "params": {
        "channel": "#general",
        "text": "Hello from NOVA2!"
    }
}

→ 200 OK
{
    "success": true,
    "data": {
        "ts": "1234567890.123456",
        "channel": "C123ABC"
    }
}
```

### Exemple : Catalogue

```
GET /api/connectors

→ 200 OK
[
    {
        "slug": "slack",
        "name": "Slack",
        "description": "Envoyer et lire des messages Slack",
        "version": "1.0.0",
        "category": "messaging",
        "auth_type": "api_key",
        "is_connected": true,
        "is_configured": true,
        "actions": [
            {"name": "send_message", "description": "..."},
            {"name": "list_channels", "description": "..."}
        ]
    }
]
```

---

## 21. Générateur de connecteur (CLI)

```bash
python -m app.framework.connectors.generator <slug> <name> [description] [category] [auth_type]

# Exemples
python -m app.framework.connectors.generator slack "Slack" "Messaging Slack" messaging api_key
python -m app.framework.connectors.generator salesforce "Salesforce CRM" "CRM Salesforce" saas oauth2
python -m app.framework.connectors.generator smtp-email "SMTP Email" "Envoi d'emails SMTP" messaging basic
```

Génère :
- `backend/app/framework/connectors/{slug}.py` — Template connecteur complet
- `backend/tests/connectors/test_{slug}.py` — Tests unitaires template

---

## 22. Checklist de validation

Avant de soumettre un connecteur, vérifier :

### Structure
- [ ] Un seul fichier `.py` dans `connectors/`
- [ ] Une classe qui étend `BaseConnector`
- [ ] `metadata` property retourne `ConnectorMetadata`
- [ ] `connect(config)` async implémenté
- [ ] `execute(action, params)` async implémenté
- [ ] `disconnect()` ferme les ressources (si applicable)

### Metadata
- [ ] `slug` en kebab-case, unique
- [ ] `auth_type` correspond à la réalité
- [ ] `config_schema` décrit TOUS les paramètres de connexion
- [ ] Au moins 1 action dans `actions`
- [ ] Chaque action a `input_schema` et `output_schema`
- [ ] `category` parmi les valeurs autorisées
- [ ] `tags` non vide

### Sécurité
- [ ] Zéro credential en dur
- [ ] Zéro import interdit (os, subprocess, open...)
- [ ] Les erreurs sont catchées (pas de raise non-géré)
- [ ] Les credentials ne sont pas loggées
- [ ] disconnect() nettoie les ressources

### Qualité
- [ ] Docstring sur la classe
- [ ] Docstring sur le module (en-tête du fichier)
- [ ] Chaque action privée est documentée
- [ ] Les erreurs utilisent `ConnectorErrorCode`
- [ ] Health check implémenté

### Tests
- [ ] Tests pour chaque action (success + error)
- [ ] Test de health check
- [ ] Test de disconnect
- [ ] Test d'action invalide
- [ ] Mock HTTP client (pas d'appel réel)

---

## 23. Exemples complets

### Exemple 1 : API Key simple (REST API)

```python
"""
GitHub — Connecteur pour l'API GitHub (repos, issues, PRs).

Catégorie: devops
Auth: api_key

Actions:
    list_repos        → Liste les repos de l'utilisateur
    get_repo          → Détail d'un repo
    create_issue      → Crée une issue
    list_issues       → Liste les issues d'un repo
"""

from __future__ import annotations
from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)


class GithubConnector(BaseConnector):
    """Connecteur GitHub via Personal Access Token."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="github",
            name="GitHub",
            description="Intégration GitHub pour repos, issues et PRs",
            version="1.0.0",
            category="devops",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="token", type="string", required=True,
                              description="GitHub Personal Access Token"),
                ToolParameter(name="api_url", type="string",
                              default="https://api.github.com",
                              description="URL API (pour GitHub Enterprise)"),
            ],
            actions=[
                ConnectorAction(
                    name="list_repos",
                    description="Liste les repos de l'utilisateur authentifié",
                    input_schema=[
                        ToolParameter(name="per_page", type="integer", default=30),
                        ToolParameter(name="sort", type="string", default="updated"),
                    ],
                    output_schema=[
                        ToolParameter(name="repos", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="create_issue",
                    description="Crée une issue dans un repo",
                    input_schema=[
                        ToolParameter(name="owner", type="string", required=True),
                        ToolParameter(name="repo", type="string", required=True),
                        ToolParameter(name="title", type="string", required=True),
                        ToolParameter(name="body", type="string"),
                        ToolParameter(name="labels", type="array"),
                    ],
                    output_schema=[
                        ToolParameter(name="issue_number", type="integer"),
                        ToolParameter(name="url", type="string"),
                    ],
                ),
            ],
            tags=["devops", "github", "git", "repos", "issues"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        import httpx
        self._client = httpx.AsyncClient(
            base_url=config.get("api_url", "https://api.github.com"),
            headers={
                "Authorization": f"Bearer {config['token']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_repos":
            return await self._list_repos(params)
        elif action == "create_issue":
            return await self._create_issue(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/user")
            return resp.status_code == 200
        except Exception:
            return False

    async def _list_repos(self, params: dict[str, Any]) -> ConnectorResult:
        try:
            resp = await self._client.get("/user/repos", params={
                "per_page": params.get("per_page", 30),
                "sort": params.get("sort", "updated"),
            })
            if resp.status_code != 200:
                return self._handle_error(resp)
            repos = [
                {"name": r["name"], "full_name": r["full_name"],
                 "description": r.get("description", ""), "private": r["private"],
                 "url": r["html_url"], "stars": r["stargazers_count"]}
                for r in resp.json()
            ]
            return self.success({"repos": repos, "count": len(repos)})
        except Exception as e:
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)

    async def _create_issue(self, params: dict[str, Any]) -> ConnectorResult:
        owner = params.get("owner", "")
        repo = params.get("repo", "")
        try:
            resp = await self._client.post(f"/repos/{owner}/{repo}/issues", json={
                "title": params["title"],
                "body": params.get("body", ""),
                "labels": params.get("labels", []),
            })
            if resp.status_code != 201:
                return self._handle_error(resp)
            data = resp.json()
            return self.success({"issue_number": data["number"], "url": data["html_url"]})
        except Exception as e:
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)

    def _handle_error(self, resp) -> ConnectorResult:
        """Mappe les erreurs HTTP vers ConnectorErrorCode."""
        code_map = {
            401: ConnectorErrorCode.AUTH_FAILED,
            403: ConnectorErrorCode.PERMISSION_DENIED,
            404: ConnectorErrorCode.EXTERNAL_API_ERROR,
            429: ConnectorErrorCode.RATE_LIMITED,
        }
        error_code = code_map.get(resp.status_code, ConnectorErrorCode.EXTERNAL_API_ERROR)
        return self.error(f"GitHub API {resp.status_code}: {resp.text[:200]}", error_code)
```

### Exemple 2 : OAuth2 (Google Drive)

```python
"""
Google Drive — Connecteur pour Google Drive (fichiers, dossiers, partage).

Catégorie: storage
Auth: oauth2

Actions:
    list_files      → Liste les fichiers
    upload_file     → Upload un fichier
    download_file   → Télécharge un fichier
    create_folder   → Crée un dossier
"""

from __future__ import annotations
from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)


class GoogleDriveConnector(BaseConnector):
    """Connecteur Google Drive via OAuth2."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="google-drive",
            name="Google Drive",
            description="Gestion de fichiers Google Drive",
            version="1.0.0",
            category="storage",
            auth_type="oauth2",
            config_schema=[
                ToolParameter(name="client_id", type="string", required=True),
                ToolParameter(name="client_secret", type="string", required=True),
                ToolParameter(name="refresh_token", type="string", required=True),
            ],
            actions=[
                ConnectorAction(
                    name="list_files",
                    description="Liste les fichiers Google Drive",
                    input_schema=[
                        ToolParameter(name="query", type="string",
                                      description="Requête de recherche Drive"),
                        ToolParameter(name="page_size", type="integer", default=20),
                    ],
                    output_schema=[
                        ToolParameter(name="files", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="download_file",
                    description="Télécharge le contenu d'un fichier",
                    input_schema=[
                        ToolParameter(name="file_id", type="string", required=True),
                    ],
                    output_schema=[
                        ToolParameter(name="content", type="string",
                                      description="Contenu base64"),
                        ToolParameter(name="mime_type", type="string"),
                        ToolParameter(name="name", type="string"),
                    ],
                ),
            ],
            tags=["storage", "google", "drive", "files", "cloud"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        import httpx
        self._config = config
        self._client = httpx.AsyncClient(
            base_url="https://www.googleapis.com",
            timeout=60.0,
        )
        await self._refresh_access_token()

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_files":
            return await self._list_files(params)
        elif action == "download_file":
            return await self._download_file(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "/drive/v3/about",
                params={"fields": "user"},
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def _refresh_access_token(self):
        """Rafraîchit le access token via OAuth2 refresh token."""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data={
                "grant_type": "refresh_token",
                "client_id": self._config["client_id"],
                "client_secret": self._config["client_secret"],
                "refresh_token": self._config["refresh_token"],
            })
            if resp.status_code != 200:
                raise ConnectionError(f"OAuth2 token refresh failed: {resp.text}")
            data = resp.json()
            self._access_token = data["access_token"]

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _list_files(self, params: dict[str, Any]) -> ConnectorResult:
        try:
            query_params = {"pageSize": params.get("page_size", 20), "fields": "files(id,name,mimeType,size)"}
            if params.get("query"):
                query_params["q"] = params["query"]

            resp = await self._client.get(
                "/drive/v3/files",
                params=query_params,
                headers=self._auth_headers(),
            )

            if resp.status_code == 401:
                await self._refresh_access_token()
                resp = await self._client.get("/drive/v3/files", params=query_params, headers=self._auth_headers())

            if resp.status_code != 200:
                return self.error(f"Drive API error: {resp.text[:200]}", ConnectorErrorCode.EXTERNAL_API_ERROR)

            files = resp.json().get("files", [])
            return self.success({"files": files, "count": len(files)})
        except Exception as e:
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)

    async def _download_file(self, params: dict[str, Any]) -> ConnectorResult:
        import base64
        file_id = params["file_id"]
        try:
            # Metadata
            meta_resp = await self._client.get(
                f"/drive/v3/files/{file_id}",
                params={"fields": "name,mimeType"},
                headers=self._auth_headers(),
            )
            if meta_resp.status_code != 200:
                return self.error("File not found", ConnectorErrorCode.EXTERNAL_API_ERROR)

            meta = meta_resp.json()

            # Content
            content_resp = await self._client.get(
                f"/drive/v3/files/{file_id}",
                params={"alt": "media"},
                headers=self._auth_headers(),
            )
            if content_resp.status_code != 200:
                return self.error("Download failed", ConnectorErrorCode.EXTERNAL_API_ERROR)

            encoded = base64.b64encode(content_resp.content).decode("utf-8")
            return self.success({
                "content": encoded,
                "mime_type": meta.get("mimeType", ""),
                "name": meta.get("name", ""),
            })
        except Exception as e:
            return self.error(str(e), ConnectorErrorCode.PROCESSING_ERROR)
```

### Exemple 3 : Basic Auth (SMTP Email)

```python
"""
SMTP Email — Connecteur pour l'envoi d'emails via SMTP.

Catégorie: messaging
Auth: basic

Actions:
    send_email  → Envoie un email
"""

from __future__ import annotations
from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)


class SmtpEmailConnector(BaseConnector):
    """Connecteur SMTP pour l'envoi d'emails."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="smtp-email",
            name="SMTP Email",
            description="Envoi d'emails via SMTP (Gmail, Outlook, custom)",
            version="1.0.0",
            category="messaging",
            auth_type="basic",
            config_schema=[
                ToolParameter(name="host", type="string", required=True,
                              description="Serveur SMTP (ex: smtp.gmail.com)"),
                ToolParameter(name="port", type="integer", required=True,
                              description="Port SMTP (587 pour TLS, 465 pour SSL)"),
                ToolParameter(name="username", type="string", required=True),
                ToolParameter(name="password", type="string", required=True,
                              description="Mot de passe ou App Password"),
                ToolParameter(name="from_email", type="string", required=True,
                              description="Adresse email d'expédition"),
                ToolParameter(name="use_tls", type="boolean", default=True),
            ],
            actions=[
                ConnectorAction(
                    name="send_email",
                    description="Envoie un email",
                    input_schema=[
                        ToolParameter(name="to", type="string", required=True,
                                      description="Destinataire(s) séparés par ,"),
                        ToolParameter(name="subject", type="string", required=True),
                        ToolParameter(name="body", type="string", required=True),
                        ToolParameter(name="html", type="boolean", default=False,
                                      description="Si true, body est du HTML"),
                        ToolParameter(name="cc", type="string"),
                        ToolParameter(name="bcc", type="string"),
                    ],
                    output_schema=[
                        ToolParameter(name="sent", type="boolean"),
                        ToolParameter(name="message_id", type="string"),
                    ],
                ),
            ],
            tags=["messaging", "email", "smtp", "notifications"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Stocke la config SMTP (la connexion est créée à chaque envoi)."""
        self._config = config

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "send_email":
            return await self._send_email(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def health_check(self) -> bool:
        """Teste la connexion SMTP."""
        import smtplib
        try:
            with smtplib.SMTP(self._config["host"], self._config["port"], timeout=10) as server:
                if self._config.get("use_tls", True):
                    server.starttls()
                server.login(self._config["username"], self._config["password"])
            return True
        except Exception:
            return False

    async def _send_email(self, params: dict[str, Any]) -> ConnectorResult:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            msg = MIMEMultipart()
            msg["From"] = self._config["from_email"]
            msg["To"] = params["to"]
            msg["Subject"] = params["subject"]

            if params.get("cc"):
                msg["Cc"] = params["cc"]

            content_type = "html" if params.get("html") else "plain"
            msg.attach(MIMEText(params["body"], content_type, "utf-8"))

            with smtplib.SMTP(self._config["host"], self._config["port"], timeout=30) as server:
                if self._config.get("use_tls", True):
                    server.starttls()
                server.login(self._config["username"], self._config["password"])

                recipients = [params["to"]]
                if params.get("cc"):
                    recipients.extend(params["cc"].split(","))
                if params.get("bcc"):
                    recipients.extend(params["bcc"].split(","))

                server.send_message(msg, to_addrs=recipients)

            return self.success({
                "sent": True,
                "message_id": msg.get("Message-ID", ""),
            })

        except smtplib.SMTPAuthenticationError:
            return self.error("SMTP auth failed", ConnectorErrorCode.AUTH_FAILED)
        except smtplib.SMTPException as e:
            return self.error(f"SMTP error: {e}", ConnectorErrorCode.EXTERNAL_API_ERROR)
        except Exception as e:
            return self.error(f"Email send failed: {e}", ConnectorErrorCode.PROCESSING_ERROR)
```

---

## Résumé des différences avec TOOL_FRAMEWORK

| Aspect | Tool | Connecteur |
|---|---|---|
| Classe de base | `BaseTool` | `BaseConnector` |
| Méthode principale | `execute(params, context)` | `execute(action, params)` |
| Contexte | Reçoit `ToolContext` | Reçoit `config` dans `connect()` |
| Résultat | `ToolResult` | `ConnectorResult` |
| Erreurs | `ToolErrorCode` | `ConnectorErrorCode` |
| Lifecycle | Stateless (un appel) | Stateful (connect → execute × N → disconnect) |
| Secrets | AUCUN | Via Vault → `connect(config)` |
| Réseau | INTERDIT | OBLIGATOIRE (c'est sa raison d'être) |
| Auto-discovery | `tools/*.py` | `connectors/*.py` |
| Imports réseau | INTERDITS | AUTORISÉS (httpx, boto3, SDKs...) |
| Catégories | text, file, data, ai, media | saas, messaging, storage, database, devops, analytics |

---

> **Ce document est la vérité unique pour les connecteurs. Tout code qui le contredit est un bug.**
