# TOOL FRAMEWORK — Guide de conception et développement des Tools

> Ce document est la référence unique pour créer des tools sur la plateforme AISOME-NOVA2.
> Il est utilisé aussi bien par les développeurs humains que par Claude Code en vibe coding.

---

## Table des matières

1. [Principes fondamentaux](#1-principes-fondamentaux)
2. [Architecture](#2-architecture)
3. [Créer un tool — Quick Start](#3-créer-un-tool--quick-start)
4. [Structure d'un tool](#4-structure-dun-tool)
5. [BaseTool — Contrat complet](#5-basetool--contrat-complet)
6. [ToolMetadata — Carte d'identité](#6-toolmetadata--carte-didentité)
7. [ToolContext — Services disponibles](#7-toolcontext--services-disponibles)
8. [ToolResult — Réponse standardisée](#8-toolresult--réponse-standardisée)
9. [Modes d'exécution (sync / async)](#9-modes-dexécution-sync--async)
10. [Gestion des erreurs](#10-gestion-des-erreurs)
11. [Gestion des fichiers (MinIO)](#11-gestion-des-fichiers-minio)
12. [Utilisation des connecteurs](#12-utilisation-des-connecteurs)
13. [Utilisation du LLM](#13-utilisation-du-llm)
14. [Health check](#14-health-check)
15. [Tests unitaires](#15-tests-unitaires)
16. [API REST](#16-api-rest)
17. [Sécurité — Règles absolues](#17-sécurité--règles-absolues)
18. [Catégories](#18-catégories)
19. [Générateur de tool (CLI)](#19-générateur-de-tool-cli)
20. [Checklist de validation](#20-checklist-de-validation)
21. [Exemples complets](#21-exemples-complets)

---

## 1. Principes fondamentaux

| Principe | Règle |
|---|---|
| **Tool = logique pure** | Transforme, calcule, traite. Jamais d'appel réseau direct. |
| **Connecteur = seule porte vers l'extérieur** | Tout appel externe passe par `context.connectors.execute()` |
| **Zéro secret dans un tool** | Pas d'API key, pas de token. Les secrets vivent dans les connecteurs. |
| **Fichiers via MinIO** | Input = `storage_key`, Output = `storage_key`. Jamais de filesystem direct. |
| **Auto-descriptif** | Chaque tool porte toutes ses metadata : schema I/O, exemples, catégorie, mode |
| **Auto-découvert** | Poser un fichier `.py` dans `tools/` = le tool existe. Supprimer = il disparaît. |
| **Pas d'appel inter-tools** | C'est l'agent qui orchestre les séquences, pas les tools entre eux |
| **Quotas/rate limits = plateforme** | Le tool ne gère pas ses propres limites |

---

## 2. Architecture

```
Agent
  │
  ├── context.tools.execute("text-summarizer", {text: "..."})
  │       │
  │       ▼
  │   ToolRegistry (auto-discovery)
  │       │
  │       ├── validate_params()      ← Validation schema
  │       ├── asyncio.wait_for()     ← Timeout management
  │       └── tool.execute()         ← Logique métier
  │             │
  │             ├── context.llm.chat()              ← Service LLM plateforme
  │             ├── context.connectors.execute()     ← Connecteurs externes
  │             ├── context.storage.get/put()         ← MinIO
  │             └── context.progress(50, "msg")       ← Progression (async)
  │
  └── ToolResult {success, data, error, error_code}
```

**Séparation Tool vs Connecteur :**

| | **Tool** | **Connecteur** |
|---|---|---|
| Rôle | Transformer, calculer, traiter | Se connecter au monde extérieur |
| Exemples | Résumer, convertir PDF, parser CSV | Google API, Slack, PostgreSQL, SMTP |
| Secrets | Aucun | Oui (API keys, OAuth tokens) |
| Réseau | Jamais d'appel externe direct | Seul à sortir vers l'extérieur |
| Testable | 100% mockable, zéro dépendance | Nécessite config/credentials |

---

## 3. Créer un tool — Quick Start

### Option A : Générateur CLI (recommandé)

```bash
python -m app.framework.tools.generator text-summarizer "Text Summarizer" "Résume un texte" text
```

Génère automatiquement :
- `backend/app/framework/tools/text_summarizer.py` — Code du tool
- `backend/tests/tools/test_text_summarizer.py` — Tests unitaires

### Option B : Créer manuellement

1. Créer `backend/app/framework/tools/mon_tool.py`
2. Implémenter une classe qui étend `BaseTool`
3. Redémarrer → auto-discovery → le tool apparaît dans le catalogue

### Option C : Vibe coding avec Claude Code

Donner ce prompt à Claude Code :

> "Crée un tool `text-summarizer` catégorie `text`, mode `sync`.
> Input: un texte (string, required) et max_points (integer, default 5).
> Output: summary (string) et points (array).
> Le tool utilise context.llm.chat() pour résumer.
> Réfère-toi à TOOL_FRAMEWORK.md pour la structure."

---

## 4. Structure d'un tool

Un tool = **un seul fichier Python** dans `backend/app/framework/tools/`.

```
backend/app/framework/tools/
├── registry.py              # Registre (NE PAS MODIFIER)
├── generator.py             # Générateur CLI (NE PAS MODIFIER)
├── __init__.py
├── text_summarizer.py       # ← 1 fichier = 1 tool
├── pdf_to_text.py
├── csv_parser.py
└── ...
```

Convention de nommage :
- **Slug** : `kebab-case` → `text-summarizer`
- **Fichier** : `snake_case` → `text_summarizer.py`
- **Classe** : `PascalCase` → `TextSummarizer`

---

## 5. BaseTool — Contrat complet

```python
from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolMetadata, ToolResult, ToolParameter, ToolExample,
    ToolExecutionMode, ToolErrorCode, HealthCheckResult,
)

class MonTool(BaseTool):

    # ┌─────────────────────────────────────────┐
    # │ OBLIGATOIRE : metadata                   │
    # └─────────────────────────────────────────┘
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="mon-tool",
            name="Mon Tool",
            description="Description courte",
            version="1.0.0",
            category="text",                          # text|file|data|ai|media|general
            execution_mode=ToolExecutionMode.SYNC,     # SYNC|ASYNC
            timeout_seconds=30,                        # 30 (sync) ou 300 (async)
            input_schema=[...],                        # Paramètres d'entrée
            output_schema=[...],                       # Structure du résultat
            examples=[...],                            # Exemples I/O
            required_connectors=[],                    # Connecteurs nécessaires
            tags=["text", "nlp"],                      # Tags recherche
        )

    # ┌─────────────────────────────────────────┐
    # │ OBLIGATOIRE : execute                    │
    # └─────────────────────────────────────────┘
    async def execute(self, params, context) -> ToolResult:
        # Logique métier ici
        return self.success({"result": "..."})

    # ┌─────────────────────────────────────────┐
    # │ OPTIONNEL : validate_params              │
    # └─────────────────────────────────────────┘
    async def validate_params(self, params) -> list[str]:
        errors = await super().validate_params(params)  # Garder la validation de base
        # Ajouter validations custom
        if params.get("max_points", 5) > 20:
            errors.append("max_points ne peut pas dépasser 20")
        return errors

    # ┌─────────────────────────────────────────┐
    # │ OPTIONNEL : health_check                 │
    # └─────────────────────────────────────────┘
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(healthy=True, message="OK")
```

### Helpers intégrés

```python
# Succès
return self.success({"key": "value"})

# Erreur standardisée
return self.error("Message humain", ToolErrorCode.INVALID_PARAMS)
return self.error("Fichier non trouvé", ToolErrorCode.FILE_NOT_FOUND)
```

---

## 6. ToolMetadata — Carte d'identité

| Champ | Type | Requis | Description |
|---|---|---|---|
| `slug` | string | oui | Identifiant unique kebab-case |
| `name` | string | oui | Nom d'affichage |
| `description` | string | oui | Description courte |
| `version` | string | non | Version semver (défaut "1.0.0") |
| `category` | string | non | Catégorie (défaut "general") |
| `execution_mode` | enum | non | `SYNC` ou `ASYNC` (défaut SYNC) |
| `timeout_seconds` | int | non | Timeout en secondes (défaut 30) |
| `input_schema` | list | non | Paramètres d'entrée |
| `output_schema` | list | non | Structure du résultat |
| `examples` | list | non | Exemples I/O |
| `required_connectors` | list | non | Slugs des connecteurs requis |
| `tags` | list | non | Tags pour la recherche |

### input_schema / output_schema

```python
ToolParameter(
    name="text",               # Nom du paramètre
    type="string",             # string|integer|number|boolean|array|object
    description="Le texte",    # Description pour la doc
    required=True,             # Requis ou optionnel
    default=None,              # Valeur par défaut (si optionnel)
)
```

### examples

```python
ToolExample(
    description="Résumé d'un article",
    input={"text": "Long article...", "max_points": 3},
    output={"summary": "...", "points": ["Point 1", "Point 2", "Point 3"]},
)
```

---

## 7. ToolContext — Services disponibles

Le `context` est le **seul point d'accès** aux services de la plateforme.
Un tool ne doit JAMAIS importer ou accéder directement à quoi que ce soit d'autre.

```python
async def execute(self, params, context) -> ToolResult:
    # ┌─ LLM (service plateforme) ──────────────────┐
    response = await context.llm.chat(
        prompt="Résume ce texte: ...",
        system_prompt="Tu es un assistant de résumé",  # optionnel
        temperature=0.3,                                # optionnel
        max_tokens=2048,                                # optionnel
    )

    # ┌─ Connecteurs (accès au monde extérieur) ────┐
    result = await context.connectors.execute(
        connector_slug="google-translate",
        action="translate",
        params={"text": "Bonjour", "target_lang": "en"},
    )

    # ┌─ Stockage MinIO (fichiers) ─────────────────┐
    data = await context.storage.get("input/file.pdf")      # Lire
    await context.storage.put("output/result.txt", data, "text/plain")  # Écrire
    files = await context.storage.list("output/")            # Lister
    exists = await context.storage.exists("input/file.pdf")  # Vérifier
    await context.storage.delete("temp/file.tmp")            # Supprimer

    # ┌─ Progression (async tools uniquement) ──────┐
    context.progress(25, "Parsing du document...")
    context.progress(50, "Analyse en cours...")
    context.progress(75, "Génération du résultat...")

    # ┌─ Logger ────────────────────────────────────┐
    context.logger.info("Traitement terminé")
    context.logger.warning("Fichier volumineux")

    return self.success({"result": response})
```

### Ce que le context NE fournit PAS (et c'est voulu)

- Pas d'accès aux autres tools (`context.tools` n'existe pas dans ToolContext)
- Pas d'accès aux autres agents
- Pas d'accès à la mémoire de conversation
- Pas d'accès à la base de données
- Pas d'accès au filesystem
- Pas d'accès réseau direct

---

## 8. ToolResult — Réponse standardisée

```python
# Succès
ToolResult(
    success=True,
    data={"summary": "...", "points": [...]},
)

# Erreur
ToolResult(
    success=False,
    error="Le fichier est trop volumineux (max 10MB)",
    error_code=ToolErrorCode.FILE_TOO_LARGE,
    data={"max_size_mb": 10, "actual_size_mb": 15},
)
```

### Helpers (recommandé)

```python
# Au lieu de construire ToolResult manuellement :
return self.success({"key": "value"})
return self.error("Message", ToolErrorCode.INVALID_PARAMS)
```

---

## 9. Modes d'exécution (sync / async)

| Mode | Timeout | Progression | Exécution | Use case |
|---|---|---|---|---|
| **SYNC** | 30s (défaut) | Non | Direct (`await`) | text-summarizer, csv-parser |
| **ASYNC** | 300s (configurable) | Oui (`context.progress`) | Celery task + Redis pub/sub | pdf-converter, video-transcriber |

### Tool SYNC (le plus courant)

```python
@property
def metadata(self):
    return ToolMetadata(
        slug="text-summarizer",
        execution_mode=ToolExecutionMode.SYNC,
        timeout_seconds=30,
        ...
    )

async def execute(self, params, context):
    result = await context.llm.chat(f"Résume: {params['text']}")
    return self.success({"summary": result})
```

### Tool ASYNC (long-running)

```python
@property
def metadata(self):
    return ToolMetadata(
        slug="video-transcriber",
        execution_mode=ToolExecutionMode.ASYNC,
        timeout_seconds=600,
        ...
    )

async def execute(self, params, context):
    video_data = await context.storage.get(params["storage_key"])
    context.progress(10, "Vidéo chargée")

    # Traitement long...
    context.progress(50, "Transcription en cours...")

    # Résultat
    await context.storage.put("output/transcript.txt", result, "text/plain")
    context.progress(100, "Terminé")

    return self.success({"storage_key": "output/transcript.txt"})
```

Le framework gère automatiquement le timeout. Si le tool dépasse `timeout_seconds`,
le framework retourne `ToolResult(success=False, error_code=ToolErrorCode.TIMEOUT)`.

---

## 10. Gestion des erreurs

### Codes d'erreur standardisés

| Code | Quand l'utiliser |
|---|---|
| `INVALID_PARAMS` | Paramètre invalide, manquant, ou type incorrect |
| `TIMEOUT` | Dépassement du timeout (géré par le framework) |
| `RATE_LIMITED` | Trop de requêtes (géré par la plateforme) |
| `EXTERNAL_API_ERROR` | Erreur d'un connecteur externe |
| `PERMISSION_DENIED` | L'utilisateur n'a pas les droits |
| `FILE_NOT_FOUND` | Fichier introuvable dans MinIO |
| `FILE_TOO_LARGE` | Fichier trop volumineux |
| `PROCESSING_ERROR` | Erreur métier dans la logique du tool |
| `CONNECTOR_UNAVAILABLE` | Connecteur requis non disponible |

### Pattern recommandé

```python
async def execute(self, params, context):
    text = params.get("text", "")

    if len(text) > 100_000:
        return self.error(
            "Le texte dépasse 100 000 caractères",
            ToolErrorCode.FILE_TOO_LARGE,
            data={"max_chars": 100_000, "actual_chars": len(text)},
        )

    # Appel connecteur
    result = await context.connectors.execute("google-translate", "translate", {
        "text": text, "target_lang": params["target_lang"]
    })

    if not result.success:
        return self.error(
            f"Erreur de traduction: {result.error}",
            ToolErrorCode.EXTERNAL_API_ERROR,
        )

    return self.success({"translated_text": result.data["translated"]})
```

### Règle importante

- Les erreurs **attendues** → retourner `self.error(...)` (pas d'exception)
- Les erreurs **inattendues** → laisser l'exception remonter. Le framework la catche et retourne `PROCESSING_ERROR`

---

## 11. Gestion des fichiers (MinIO)

### Pattern : fichier en entrée

L'agent passe une `storage_key`, le tool lit depuis MinIO :

```python
async def execute(self, params, context):
    file_data = await context.storage.get(params["storage_key"])
    if file_data is None:
        return self.error(
            f"Fichier introuvable: {params['storage_key']}",
            ToolErrorCode.FILE_NOT_FOUND,
        )
    # Traiter file_data (bytes)...
```

### Pattern : fichier en sortie

Le tool écrit dans MinIO et retourne la `storage_key` :

```python
async def execute(self, params, context):
    # ... traitement ...
    output_key = f"outputs/result_{params['format']}.txt"
    await context.storage.put(output_key, result_bytes, "text/plain")
    return self.success({"storage_key": output_key})
```

### Pattern : fichier en entrée ET sortie

```python
async def execute(self, params, context):
    # Lire
    pdf_data = await context.storage.get(params["input_key"])
    if pdf_data is None:
        return self.error("PDF introuvable", ToolErrorCode.FILE_NOT_FOUND)

    # Transformer
    text = extract_text_from_pdf(pdf_data)

    # Écrire
    output_key = params["input_key"].replace(".pdf", ".txt")
    await context.storage.put(output_key, text.encode(), "text/plain")

    return self.success({
        "storage_key": output_key,
        "char_count": len(text),
    })
```

---

## 12. Utilisation des connecteurs

Un tool qui a besoin de données externes **passe toujours par un connecteur**.

### Déclarer la dépendance

```python
@property
def metadata(self):
    return ToolMetadata(
        slug="translate-text",
        required_connectors=["google-translate"],  # ← Déclaration
        ...
    )
```

### Utiliser le connecteur

```python
async def execute(self, params, context):
    result = await context.connectors.execute(
        connector_slug="google-translate",
        action="translate",
        params={"text": params["text"], "target_lang": params["target_lang"]},
    )

    if not result.success:
        return self.error(
            f"Traduction échouée: {result.error}",
            ToolErrorCode.EXTERNAL_API_ERROR,
        )

    return self.success({"translated": result.data["translated_text"]})
```

### Health check avec connecteur

```python
async def health_check(self):
    # Vérifier que le connecteur est disponible
    connectors = await context.connectors.list()
    slugs = [c["slug"] for c in connectors]

    details = {}
    healthy = True
    for required in self.metadata.required_connectors:
        available = required in slugs
        details[required] = "ok" if available else "missing"
        if not available:
            healthy = False

    return HealthCheckResult(
        healthy=healthy,
        message="OK" if healthy else "Connecteur(s) manquant(s)",
        details=details,
    )
```

---

## 13. Utilisation du LLM

Le LLM est un **service plateforme** (pas un connecteur). Le tool y accède via `context.llm`.

```python
async def execute(self, params, context):
    # Appel simple
    response = await context.llm.chat(
        prompt=f"Résume ce texte en {params['max_points']} points:\n{params['text']}",
        system_prompt="Tu es un expert en synthèse de documents.",
        temperature=0.3,
    )

    return self.success({"summary": response})
```

Le tool ne choisit **pas** le modèle. C'est la plateforme qui le configure.

---

## 14. Health check

Chaque tool peut exposer un health check pour vérifier son état.

```python
async def health_check(self) -> HealthCheckResult:
    # Tool simple sans dépendance
    return HealthCheckResult(healthy=True, message="OK")

    # Tool avec connecteur requis
    return HealthCheckResult(
        healthy=True,
        message="OK",
        details={"google-translate": "available"},
    )

    # Tool en erreur
    return HealthCheckResult(
        healthy=False,
        message="Connecteur google-translate non disponible",
        details={"google-translate": "missing"},
    )
```

L'API expose :
- `GET /api/tools/health` → santé de tous les tools
- `GET /api/tools/{slug}/health` → santé d'un tool spécifique

---

## 15. Tests unitaires

### Base : ToolTestCase

```python
import pytest
from app.framework.testing import ToolTestCase, MockToolContext
from app.framework.schemas import ConnectorResult, ToolResult
from app.framework.tools.text_summarizer import TextSummarizer


class TestTextSummarizer(ToolTestCase):
    tool_class = TextSummarizer

    # --- Metadata ---

    def test_metadata(self):
        meta = self.tool.metadata
        assert meta.slug == "text-summarizer"
        assert meta.category == "text"
        assert len(meta.input_schema) > 0
        assert len(meta.examples) > 0

    # --- Validation ---

    @pytest.mark.asyncio
    async def test_valid_params(self):
        await self.assert_validates_params(
            {"text": "Hello", "max_points": 3},
            expected_errors=0,
        )

    @pytest.mark.asyncio
    async def test_missing_required(self):
        await self.assert_validates_params({}, expected_errors=1)

    @pytest.mark.asyncio
    async def test_wrong_type(self):
        await self.assert_validates_params({"text": 123}, expected_errors=1)

    # --- Exécution ---

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        ctx = self.create_context(llm_responses=["Point 1. Point 2."])
        result = await self.tool.execute({"text": "Long text..."}, ctx)
        self.assert_success(result)
        self.assert_data_has(result, "summary")
        self.assert_llm_called(ctx, times=1)

    @pytest.mark.asyncio
    async def test_with_connector(self):
        ctx = self.create_context(
            connector_results={
                "google-translate.translate": ConnectorResult(
                    success=True, data={"translated": "Hello"}
                )
            }
        )
        result = await self.tool.execute(
            {"text": "Bonjour", "target_lang": "en"}, ctx
        )
        self.assert_connector_called(ctx, "google-translate", "translate")

    @pytest.mark.asyncio
    async def test_file_operations(self):
        ctx = self.create_context(
            storage_data={"input/doc.pdf": b"PDF content here"}
        )
        result = await self.tool.execute({"storage_key": "input/doc.pdf"}, ctx)
        self.assert_storage_get(ctx, "input/doc.pdf")

    # --- Health ---

    @pytest.mark.asyncio
    async def test_health_check(self):
        await self.assert_health_ok()
```

### Assertions disponibles

| Assertion | Description |
|---|---|
| `assert_success(result)` | Le résultat est un succès |
| `assert_error(result, error_code)` | Le résultat est une erreur avec ce code |
| `assert_data_has(result, "key1", "key2")` | Le résultat contient ces clés |
| `assert_llm_called(ctx, times=N)` | Le LLM a été appelé N fois |
| `assert_connector_called(ctx, slug, action, times=N)` | Un connecteur a été appelé |
| `assert_storage_put(ctx, key)` | Un fichier a été écrit |
| `assert_storage_get(ctx, key)` | Un fichier a été lu |
| `assert_progress_reached(ctx, min_percent)` | La progression a atteint X% |
| `assert_health_ok()` | Le health check passe |
| `assert_validates_params(params, expected_errors=N)` | Validation des paramètres |

---

## 16. API REST

### Catalogue

```
GET /api/tools
GET /api/tools?category=text
```

Réponse :
```json
[
  {
    "slug": "text-summarizer",
    "name": "Text Summarizer",
    "description": "Résume un texte en points clés",
    "version": "1.0.0",
    "category": "text",
    "execution_mode": "sync",
    "timeout_seconds": 30,
    "input_schema": [...],
    "output_schema": [...],
    "examples": [...],
    "required_connectors": [],
    "tags": ["text", "nlp"]
  }
]
```

### Détail d'un tool

```
GET /api/tools/{slug}
```

### Catégories

```
GET /api/tools/categories
```

Réponse : `["ai", "data", "file", "text"]`

### Exécution

```
POST /api/tools/{slug}/execute
Content-Type: application/json

{
  "params": {
    "text": "Long texte à résumer...",
    "max_points": 5
  }
}
```

Réponse succès :
```json
{
  "success": true,
  "data": {"summary": "...", "points": [...]},
  "error": null,
  "error_code": null
}
```

Réponse erreur :
```json
{
  "detail": {
    "error": "Paramètre requis manquant: text",
    "error_code": "INVALID_PARAMS"
  }
}
```

### Health check

```
GET /api/tools/health

{
  "text-summarizer": {"healthy": true, "message": "OK", "details": {}},
  "translate-text": {"healthy": false, "message": "...", "details": {...}}
}
```

```
GET /api/tools/{slug}/health

{"healthy": true, "message": "OK", "details": {}}
```

---

## 17. Sécurité — Règles absolues

### Imports INTERDITS (vérifiés par le validateur AST)

```python
# INTERDIT — accès système
import os
import subprocess
import sys
import shutil
import pathlib

# INTERDIT — accès réseau direct
import requests
import httpx
import urllib
import socket
import aiohttp

# INTERDIT — exécution dynamique
eval("code")
exec("code")
compile("code")
__import__("module")
```

### Builtins INTERDITS

```python
open("file")          # → utiliser context.storage
exec("code")          # Jamais
eval("code")          # Jamais
```

### Pattern de credentials INTERDITS

```python
api_key = "sk-..."       # INTERDIT
token = "ghp_..."        # INTERDIT
password = "secret123"   # INTERDIT
```

### Ce qui est AUTORISÉ

```python
# Imports standard sûrs
import json
import re
import math
import datetime
import hashlib
import base64
import csv
import io
import textwrap
from typing import Any, Optional
from collections import defaultdict

# Imports framework
from app.framework.base import BaseTool
from app.framework.schemas import ToolMetadata, ToolResult, ...
```

---

## 18. Catégories

| Catégorie | Description | Exemples |
|---|---|---|
| `text` | Traitement de texte et NLP | Résumé, traduction, extraction, sentiment |
| `file` | Conversion et manipulation de fichiers | PDF→texte, OCR, compression, merge |
| `data` | Traitement de données structurées | CSV parsing, JSON transform, filtrage |
| `ai` | Opérations IA avancées | Embedding, classification, clustering |
| `media` | Audio, vidéo, image | Transcription, resize, format conversion |
| `general` | Autres | Utilitaires divers |

---

## 19. Générateur de tool (CLI)

```bash
# Syntaxe
python -m app.framework.tools.generator <slug> <name> [description] [category] [mode]

# Exemples
python -m app.framework.tools.generator text-summarizer "Text Summarizer"
python -m app.framework.tools.generator pdf-to-text "PDF to Text" "Extrait le texte d'un PDF" file
python -m app.framework.tools.generator video-transcriber "Video Transcriber" "Transcrit une vidéo" media async
```

Arguments :
| Arg | Requis | Description |
|---|---|---|
| `slug` | oui | Identifiant kebab-case |
| `name` | oui | Nom d'affichage |
| `description` | non | Description courte |
| `category` | non | text, file, data, ai, media, general (défaut: general) |
| `mode` | non | sync, async (défaut: sync) |

---

## 20. Checklist de validation

Avant de livrer un tool, vérifier :

- [ ] La classe étend `BaseTool`
- [ ] `metadata` retourne un `ToolMetadata` complet (slug, name, description, schema I/O, exemples)
- [ ] `execute()` retourne toujours un `ToolResult` (jamais d'exception pour les erreurs attendues)
- [ ] Les erreurs utilisent `self.error()` avec un `ToolErrorCode` approprié
- [ ] Les succès utilisent `self.success()`
- [ ] Pas d'import interdit (os, subprocess, requests, httpx, socket...)
- [ ] Pas de `open()`, `exec()`, `eval()`
- [ ] Pas de secret en dur
- [ ] Les appels externes passent par `context.connectors.execute()`
- [ ] Les fichiers passent par `context.storage`
- [ ] Le LLM passe par `context.llm.chat()`
- [ ] Les connecteurs requis sont déclarés dans `required_connectors`
- [ ] La catégorie est correcte
- [ ] Le mode d'exécution est correct (sync/async)
- [ ] Le timeout est réaliste
- [ ] Au moins un `ToolExample` est défini
- [ ] Les tests unitaires passent
- [ ] Le health_check est implémenté si le tool a des dépendances

---

## 21. Exemples complets

### Exemple 1 : Tool SYNC simple (logique pure)

```python
"""
Word Counter — Compte les mots, phrases et caractères d'un texte.

Catégorie: text
Mode: sync
"""
from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolExample, ToolExecutionMode, ToolMetadata,
    ToolParameter, ToolResult, ToolErrorCode,
)


class WordCounter(BaseTool):

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="word-counter",
            name="Word Counter",
            description="Compte les mots, phrases et caractères d'un texte",
            category="text",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=10,
            input_schema=[
                ToolParameter(name="text", type="string", required=True,
                              description="Texte à analyser"),
            ],
            output_schema=[
                ToolParameter(name="words", type="integer"),
                ToolParameter(name="sentences", type="integer"),
                ToolParameter(name="characters", type="integer"),
            ],
            examples=[
                ToolExample(
                    description="Comptage simple",
                    input={"text": "Bonjour le monde. Comment ça va?"},
                    output={"words": 6, "sentences": 2, "characters": 31},
                ),
            ],
            tags=["text", "comptage", "statistiques"],
        )

    async def execute(self, params, context) -> ToolResult:
        text = params["text"]

        if not text.strip():
            return self.error("Le texte est vide", ToolErrorCode.INVALID_PARAMS)

        words = len(text.split())
        sentences = text.count(".") + text.count("!") + text.count("?")
        characters = len(text)

        return self.success({
            "words": words,
            "sentences": max(sentences, 1),
            "characters": characters,
        })
```

### Exemple 2 : Tool SYNC avec LLM

```python
"""
Text Summarizer — Résume un texte en points clés via LLM.

Catégorie: text
Mode: sync
"""
from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolExample, ToolExecutionMode, ToolMetadata,
    ToolParameter, ToolResult, ToolErrorCode,
)


class TextSummarizer(BaseTool):

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="text-summarizer",
            name="Text Summarizer",
            description="Résume un texte long en points clés",
            category="text",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=30,
            input_schema=[
                ToolParameter(name="text", type="string", required=True,
                              description="Texte à résumer"),
                ToolParameter(name="max_points", type="integer", default=5,
                              description="Nombre max de points"),
                ToolParameter(name="language", type="string", default="fr",
                              description="Langue du résumé"),
            ],
            output_schema=[
                ToolParameter(name="summary", type="string"),
                ToolParameter(name="points", type="array"),
            ],
            examples=[
                ToolExample(
                    description="Résumé en 3 points",
                    input={"text": "Article long...", "max_points": 3},
                    output={"summary": "...", "points": ["...", "...", "..."]},
                ),
            ],
            tags=["text", "résumé", "nlp"],
        )

    async def execute(self, params, context) -> ToolResult:
        text = params["text"]
        max_points = params.get("max_points", 5)
        language = params.get("language", "fr")

        if len(text) < 50:
            return self.error(
                "Le texte est trop court pour être résumé (min 50 caractères)",
                ToolErrorCode.INVALID_PARAMS,
            )

        prompt = (
            f"Résume le texte suivant en {max_points} points clés maximum.\n"
            f"Langue de sortie: {language}\n"
            f"Format: une ligne par point, préfixé par '- '\n\n"
            f"Texte:\n{text}"
        )

        response = await context.llm.chat(
            prompt=prompt,
            system_prompt="Tu es un expert en synthèse de documents. Sois concis et précis.",
            temperature=0.3,
        )

        points = [
            line.lstrip("- ").strip()
            for line in response.strip().split("\n")
            if line.strip().startswith("- ")
        ]

        return self.success({
            "summary": response,
            "points": points[:max_points],
        })
```

### Exemple 3 : Tool avec connecteur

```python
"""
Translate Text — Traduit un texte via le connecteur Google Translate.

Catégorie: text
Mode: sync
"""
from app.framework.base import BaseTool
from app.framework.schemas import (
    HealthCheckResult, ToolExample, ToolExecutionMode,
    ToolMetadata, ToolParameter, ToolResult, ToolErrorCode,
)


class TranslateText(BaseTool):

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="translate-text",
            name="Translate Text",
            description="Traduit un texte vers une langue cible",
            category="text",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=15,
            input_schema=[
                ToolParameter(name="text", type="string", required=True),
                ToolParameter(name="target_lang", type="string", required=True,
                              description="Code langue cible (en, fr, es, de...)"),
                ToolParameter(name="source_lang", type="string", default="auto",
                              description="Code langue source (auto-detect par défaut)"),
            ],
            output_schema=[
                ToolParameter(name="translated_text", type="string"),
                ToolParameter(name="detected_lang", type="string"),
            ],
            required_connectors=["google-translate"],
            examples=[
                ToolExample(
                    description="Français → Anglais",
                    input={"text": "Bonjour le monde", "target_lang": "en"},
                    output={"translated_text": "Hello world", "detected_lang": "fr"},
                ),
            ],
            tags=["text", "traduction", "i18n"],
        )

    async def execute(self, params, context) -> ToolResult:
        result = await context.connectors.execute(
            "google-translate", "translate",
            {
                "text": params["text"],
                "target_lang": params["target_lang"],
                "source_lang": params.get("source_lang", "auto"),
            },
        )

        if not result.success:
            return self.error(
                f"Traduction échouée: {result.error}",
                ToolErrorCode.EXTERNAL_API_ERROR,
            )

        return self.success({
            "translated_text": result.data.get("translated_text", ""),
            "detected_lang": result.data.get("detected_lang", "unknown"),
        })

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            healthy=True,
            message="OK",
            details={"required_connector": "google-translate"},
        )
```

### Exemple 4 : Tool ASYNC avec fichier et progression

```python
"""
PDF to Text — Extrait le texte d'un document PDF depuis MinIO.

Catégorie: file
Mode: async
"""
from app.framework.base import BaseTool
from app.framework.schemas import (
    ToolExample, ToolExecutionMode, ToolMetadata,
    ToolParameter, ToolResult, ToolErrorCode,
)


class PdfToText(BaseTool):

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="pdf-to-text",
            name="PDF to Text",
            description="Extrait le texte brut d'un document PDF",
            category="file",
            execution_mode=ToolExecutionMode.ASYNC,
            timeout_seconds=120,
            input_schema=[
                ToolParameter(name="storage_key", type="string", required=True,
                              description="Clé MinIO du fichier PDF"),
            ],
            output_schema=[
                ToolParameter(name="text", type="string",
                              description="Texte extrait"),
                ToolParameter(name="pages", type="integer",
                              description="Nombre de pages"),
                ToolParameter(name="output_key", type="string",
                              description="Clé MinIO du fichier texte généré"),
            ],
            examples=[
                ToolExample(
                    description="Extraction d'un PDF",
                    input={"storage_key": "uploads/document.pdf"},
                    output={
                        "text": "Contenu extrait...",
                        "pages": 5,
                        "output_key": "outputs/document.txt",
                    },
                ),
            ],
            tags=["file", "pdf", "extraction"],
        )

    async def execute(self, params, context) -> ToolResult:
        storage_key = params["storage_key"]

        # 1. Lire le PDF depuis MinIO
        context.progress(10, "Lecture du fichier PDF...")
        pdf_data = await context.storage.get(storage_key)
        if pdf_data is None:
            return self.error(
                f"Fichier introuvable: {storage_key}",
                ToolErrorCode.FILE_NOT_FOUND,
            )

        # 2. Extraire le texte
        context.progress(30, "Extraction du texte...")
        # TODO: utiliser une lib comme PyPDF2, pdfplumber, etc.
        # Pour l'exemple, on simule:
        text = pdf_data.decode("utf-8", errors="replace")
        pages = max(1, len(text) // 3000)

        context.progress(70, "Sauvegarde du résultat...")

        # 3. Sauvegarder le résultat
        output_key = storage_key.rsplit(".", 1)[0] + ".txt"
        await context.storage.put(output_key, text.encode("utf-8"), "text/plain")

        context.progress(100, "Terminé")

        return self.success({
            "text": text[:1000],  # Aperçu
            "pages": pages,
            "output_key": output_key,
        })
```
