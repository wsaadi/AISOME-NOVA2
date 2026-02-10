# AGENT_FRAMEWORK.md — Référence du Framework Agent AISOME NOVA2

> **Ce document est la LOI UNIQUE** pour tout développement d'agent.
> Il est lu par : les développeurs humains, Claude Code (vibe coding), et le générateur d'agents.
> Toute déviation est détectée et bloquée par le validateur.

---

## 1. Structure d'un agent

Chaque agent suit **exactement** cette arborescence :

```
backend/app/agents/{slug}/
├── manifest.json              # Identité, version, dépendances
├── agent.py                   # Logique métier (extends BaseAgent)
└── prompts/
    └── system.md              # System prompt de l'agent

frontend/src/agents/{slug}/
├── index.tsx                  # Interface React (implements AgentViewProps)
├── components/                # Composants custom (optionnel)
│   └── *.tsx
└── styles.ts                  # Styles custom (optionnel)
```

### Règles de nommage
- **slug** : kebab-case, alphanumérique + tirets (`mon-agent`, `analyseur-docs`)
- **Classe Python** : PascalCase + `Agent` (`MonAgentAgent`, `AnalyseurDocsAgent`)
- **Composant React** : PascalCase + `View` (`MonAgentView`, `AnalyseurDocsView`)

---

## 2. Backend — agent.py

### Classe de base obligatoire

```python
from __future__ import annotations
from typing import TYPE_CHECKING, AsyncIterator
from app.framework.base import BaseAgent
from app.framework.schemas import AgentManifest, AgentResponse, AgentResponseChunk, UserMessage

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext
```

### Méthodes obligatoires

| Méthode | Signature | Description |
|---------|-----------|-------------|
| `manifest` | `@property → AgentManifest` | Retourne les métadonnées de l'agent |
| `handle_message` | `async (UserMessage, AgentContext) → AgentResponse` | Traite un message utilisateur |

### Méthodes optionnelles

| Méthode | Signature | Description |
|---------|-----------|-------------|
| `handle_message_stream` | `async (UserMessage, AgentContext) → AsyncIterator[AgentResponseChunk]` | Version streaming |
| `on_session_start` | `async (AgentContext) → None` | Hook de début de session |
| `on_session_end` | `async (AgentContext) → None` | Hook de fin de session |

### Exemple minimal

```python
class MonAgent(BaseAgent):
    @property
    def manifest(self) -> AgentManifest:
        import json
        from pathlib import Path
        with open(Path(__file__).parent / "manifest.json") as f:
            return AgentManifest(**json.load(f))

    async def handle_message(self, message: UserMessage, context: AgentContext) -> AgentResponse:
        """Traite le message utilisateur."""
        response = await context.llm.chat(
            prompt=message.content,
            system_prompt="Tu es un assistant utile.",
        )
        return AgentResponse(content=response)
```

---

## 3. AgentContext — API disponible

Le `context` est le **SEUL** point d'accès aux services de la plateforme.

### context.llm — Appels LLM

```python
# Appel non-streamé
response: str = await context.llm.chat(
    prompt="Analyse ce texte",
    system_prompt="Tu es un analyste",    # optionnel
    temperature=0.7,                       # optionnel (0.0-1.0)
    max_tokens=4096,                       # optionnel
)

# Appel streamé (token par token)
async for token in context.llm.stream(prompt="Résume ce doc"):
    # token est une string
    yield AgentResponseChunk(content=token)
```

### context.tools — Exécution des tools

```python
# Lister les tools disponibles
tools: list[ToolMetadata] = await context.tools.list()

# Exécuter un tool
result: ToolResult = await context.tools.execute(
    "text-summarizer",           # slug du tool
    {"text": "...", "max_points": 5}  # paramètres (selon le schema du tool)
)
# result.success: bool
# result.data: dict
# result.error: str | None
```

### context.connectors — Exécution des connecteurs

```python
# Lister les connecteurs
connectors = await context.connectors.list()

# Exécuter une action
result: ConnectorResult = await context.connectors.execute(
    "salesforce",           # slug du connecteur
    "get_contacts",         # nom de l'action
    {"limit": 10}           # paramètres
)
```

### context.agents — Appels inter-agents (orchestration)

```python
# Appeler un autre agent
response: AgentResponse = await context.agents.execute(
    "redacteur",                    # slug de l'agent
    "Rédige un rapport sur...",     # message
    {"priority": "high"}            # metadata optionnelle
)
```

### context.storage — Stockage MinIO (cloisonné user × agent)

```python
# Stocker un fichier
await context.storage.put("outputs/report.pdf", pdf_bytes, "application/pdf")

# Récupérer un fichier
data: bytes = await context.storage.get("outputs/report.pdf")

# Lister les fichiers
files: list[str] = await context.storage.list("outputs/")

# Vérifier l'existence
exists: bool = await context.storage.exists("outputs/report.pdf")

# Supprimer
deleted: bool = await context.storage.delete("outputs/report.pdf")
```

> **Note** : Le chemin réel est `users/{user_id}/agents/{agent_slug}/outputs/report.pdf`.
> L'agent ne connaît pas et ne peut pas modifier ce préfixe.

### context.memory — Historique de conversation

```python
# Récupérer l'historique
messages: list[SessionMessage] = await context.memory.get_history(limit=10)

# Effacer l'historique
await context.memory.clear()
```

### context.set_progress — Progression

```python
context.set_progress(50, "Analyse en cours, page 3/6...")
```

---

## 4. manifest.json — Carte d'identité

```json
{
  "name": "Mon Agent",
  "slug": "mon-agent",
  "version": "1.0.0",
  "description": "Description courte de l'agent",
  "author": "dev@company.com",
  "icon": "smart_toy",
  "category": "general",
  "tags": ["analyse", "documents"],
  "dependencies": {
    "tools": ["text-summarizer", "json-extractor"],
    "connectors": ["salesforce"]
  },
  "triggers": [
    {"type": "user_message", "config": {}}
  ],
  "capabilities": ["streaming", "file_upload"],
  "min_platform_version": "1.0.0"
}
```

### Champs obligatoires
- `name`, `slug`, `version`, `description`

### Triggers supportés
- `user_message` — Message de l'utilisateur (défaut)
- `webhook` — Appel HTTP externe
- `cron` — Planification (config: `{"expression": "0 8 * * MON"}`)
- `event` — Événement plateforme (config: `{"event": "file_uploaded"}`)

---

## 5. Frontend — index.tsx

### Interface obligatoire

```tsx
import React from 'react';
import { AgentViewProps } from 'framework/types';

const MonAgentView: React.FC<AgentViewProps> = ({ agent, sessionId, userId }) => {
  // ...
};

export default MonAgentView;
```

### Props reçues (AgentViewProps)

| Prop | Type | Description |
|------|------|-------------|
| `agent` | `AgentManifest` | Métadonnées de l'agent |
| `sessionId` | `string` | ID de la session courante |
| `userId` | `number` | ID de l'utilisateur |

### Imports autorisés

```tsx
// ✅ AUTORISÉ — Composants framework
import { ChatPanel, FileUpload, ActionButton, DataTable, MarkdownView, SettingsPanel } from 'framework/components';

// ✅ AUTORISÉ — Hooks framework
import { useAgent, useAgentStorage, useWebSocket } from 'framework/hooks';

// ✅ AUTORISÉ — Types framework
import { ChatMessage, AgentResponse, AgentManifest } from 'framework/types';

// ✅ AUTORISÉ — React standard
import React, { useState, useEffect, useCallback } from 'react';

// ❌ INTERDIT — Libs externes directes
import { Button } from '@mui/material';      // NON
import axios from 'axios';                    // NON
import { LineChart } from 'recharts';         // NON
```

### Composants disponibles

| Composant | Description |
|-----------|-------------|
| `<ChatPanel>` | Interface de chat complète (messages, input, streaming) |
| `<FileUpload>` | Upload de fichiers avec progression |
| `<ActionButton>` | Bouton d'action avec loader |
| `<DataTable>` | Tableau de données configurable |
| `<MarkdownView>` | Rendu Markdown |
| `<SettingsPanel>` | Panneau de paramètres (sliders, selects, toggles) |

### Hooks disponibles

| Hook | Description |
|------|-------------|
| `useAgent(slug, sessionId)` | Envoi de messages, historique, streaming, état |
| `useAgentStorage(slug)` | Upload, download, listing de fichiers |
| `useWebSocket({ token, onMessage })` | Connexion WebSocket pour le temps réel |

---

## 6. Règles de sécurité

### Imports interdits dans agent.py

```
os, subprocess, shutil, pathlib, requests, httpx, urllib,
socket, sqlite3, psycopg2, asyncpg, sqlalchemy, redis, celery, boto3, minio
```

### Appels interdits

```
open(), exec(), eval(), compile(), __import__(), globals(), locals()
```

### Règles

1. **Tout accès passe par le context** — pas d'appels directs
2. **Pas de credentials en dur** — les secrets sont dans Vault
3. **Pas d'accès filesystem** — utiliser `context.storage`
4. **Pas d'appels HTTP** — utiliser `context.tools` ou `context.connectors`
5. **Pas de path traversal** — le framework bloque `..` dans les chemins storage

---

## 7. Pipeline d'exécution (intouchable)

Chaque appel à un agent passe par ce pipeline que l'agent ne contrôle pas :

```
1. Validation input       ← message non vide, taille < 100K
2. Vérification permissions ← RBAC
3. Vérification quotas     ← tokens/coûts
4. Modération input        ← GLiNER PII detection
5. handle_message()        ← CODE DE L'AGENT
6. Modération output       ← GLiNER
7. Log consommation        ← tokens in/out, coûts
8. Réponse                 ← retour au frontend
```

---

## 8. Export / Import

### Format d'export : ZIP

```
mon-agent.zip
├── manifest.json
├── backend/
│   ├── agent.py
│   └── prompts/
│       └── system.md
└── frontend/
    ├── index.tsx
    ├── components/
    │   └── *.tsx
    └── styles.ts
```

### Import
Le ZIP est validé par le validateur avant déploiement.
Les dépendances (tools/connectors) doivent exister sur la plateforme cible.

---

## 9. Validateur

Avant tout déploiement :

```bash
python -m app.framework.validator backend/app/agents/mon-agent/
```

### Vérifications
- ✓ manifest.json valide (schéma JSON respecté)
- ✓ agent.py étend BaseAgent
- ✓ handle_message() implémenté
- ✓ Docstrings présentes
- ✓ Dépendances existent dans les registres
- ✓ prompts/system.md présent et non vide
- ✓ Pas d'imports interdits
- ✓ Pas de credentials en dur
- ✓ Pas d'appels interdits (eval, exec, open...)

---

## 10. Créer un nouvel agent

### Via le générateur (recommandé)

```bash
python -m app.framework.generator mon-agent "Mon Agent" "Description de l'agent"
```

### Via Claude Code (vibe coding)

> "Crée un agent qui analyse des documents PDF et en extrait les points clés.
> Suis les conventions de AGENT_FRAMEWORK.md."

### Manuellement

1. Créer les dossiers `backend/app/agents/{slug}/` et `frontend/src/agents/{slug}/`
2. Écrire `manifest.json` (voir section 4)
3. Écrire `agent.py` (voir section 2)
4. Écrire `prompts/system.md`
5. Écrire `frontend/index.tsx` (voir section 5)
6. Valider : `python -m app.framework.validator backend/app/agents/{slug}/`

---

## 11. Testing

```python
import pytest
from app.framework.testing import AgentTestCase
from app.framework.schemas import UserMessage, ToolResult

class TestMonAgent(AgentTestCase):
    agent_class = MonAgent

    @pytest.mark.asyncio
    async def test_basic_response(self):
        ctx = self.create_context(llm_responses=["Voici le résumé..."])
        response = await self.agent.handle_message(
            UserMessage(content="Résume ce document"), ctx
        )
        assert "résumé" in response.content.lower()
        self.assert_llm_called(ctx, times=1)

    @pytest.mark.asyncio
    async def test_uses_tool(self):
        ctx = self.create_context(
            tool_results={"text-summarizer": ToolResult(success=True, data={"summary": "..."})}
        )
        await self.agent.handle_message(UserMessage(content="Résume"), ctx)
        self.assert_tool_called(ctx, "text-summarizer")
```

### Helpers disponibles
- `self.create_context(llm_responses, tool_results, connector_results, agent_results, history)`
- `self.create_message(content, metadata)`
- `self.assert_llm_called(ctx, times)`
- `self.assert_tool_called(ctx, slug, times)`
- `self.assert_connector_called(ctx, slug, action, times)`
- `self.assert_storage_put(ctx, key)`

---

## 12. Cycle de vie d'un agent

```
draft → active → deprecated → disabled → archived
```

| État | Description |
|------|-------------|
| `draft` | En développement, non visible dans le catalogue |
| `active` | Disponible pour les utilisateurs |
| `deprecated` | Encore utilisable, mais un successeur existe |
| `disabled` | Désactivé par l'admin, inaccessible |
| `archived` | Archivé, conservé mais invisible |

---

## 13. Checklist de conformité

Avant de soumettre un agent :

- [ ] `manifest.json` complet et valide
- [ ] `agent.py` étend `BaseAgent`
- [ ] `handle_message()` implémenté avec docstring
- [ ] `prompts/system.md` rédigé
- [ ] `frontend/index.tsx` exporte un composant par défaut
- [ ] Aucun import interdit
- [ ] Aucun credential en dur
- [ ] Tout accès passe par le `context`
- [ ] Tests unitaires écrits et passent
- [ ] Validateur passe sans erreur
