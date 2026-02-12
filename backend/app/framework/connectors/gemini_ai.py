"""
Google Gemini — Connecteur pour l'API Gemini (2.5 Pro, 2.0 Flash, 1.5 Pro).

Catégorie: ai
Auth: api_key

Actions:
    list_models       → Liste les modèles Gemini disponibles
    chat              → Génération de contenu avec choix du modèle
    create_embeddings → Génère des embeddings vectoriels
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

GEMINI_MODELS = [
    {"id": "gemini-2.5-pro-preview-05-06", "name": "Gemini 2.5 Pro", "context_window": 1048576, "type": "chat", "description": "Most capable, thinking model"},
    {"id": "gemini-2.5-flash-preview-05-20", "name": "Gemini 2.5 Flash", "context_window": 1048576, "type": "chat", "description": "Fast thinking model"},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "context_window": 1048576, "type": "chat", "description": "Fast, versatile workhorse"},
    {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "context_window": 1048576, "type": "chat", "description": "Cost-efficient, low latency"},
    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "context_window": 2097152, "type": "chat", "description": "2M context window"},
    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "context_window": 1048576, "type": "chat", "description": "Previous gen, fast"},
    {"id": "text-embedding-004", "name": "Text Embedding 004", "context_window": 2048, "type": "embedding", "description": "Text embeddings"},
]


class GeminiConnector(BaseConnector):
    """Connecteur Google Gemini — generateContent API."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="gemini",
            name="Google Gemini",
            description="API Google Gemini — 2.5 Pro, 2.0 Flash, 1.5 Pro, embeddings",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="Google AI API Key"),
                ToolParameter(name="base_url", type="string",
                              default="https://generativelanguage.googleapis.com",
                              description="URL de base"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles Gemini disponibles",
                    input_schema=[
                        ToolParameter(name="type", type="string",
                                      description="Filtrer: chat, embedding"),
                    ],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="chat",
                    description="Génération de contenu avec choix du modèle",
                    input_schema=[
                        ToolParameter(name="model", type="string", required=True,
                                      description="ID du modèle (ex: gemini-2.0-flash)"),
                        ToolParameter(name="messages", type="array", required=True,
                                      description="Messages [{role, content}] (role: user ou model)"),
                        ToolParameter(name="system_prompt", type="string",
                                      description="System instruction"),
                        ToolParameter(name="temperature", type="number", default=0.7),
                        ToolParameter(name="max_tokens", type="integer", default=4096),
                    ],
                    output_schema=[
                        ToolParameter(name="content", type="string"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="usage", type="object",
                                      description="{prompt_tokens, completion_tokens, total_tokens}"),
                        ToolParameter(name="finish_reason", type="string"),
                    ],
                ),
                ConnectorAction(
                    name="create_embeddings",
                    description="Génère des embeddings via Gemini",
                    input_schema=[
                        ToolParameter(name="model", type="string",
                                      default="text-embedding-004"),
                        ToolParameter(name="input", type="string", required=True,
                                      description="Texte à vectoriser"),
                    ],
                    output_schema=[
                        ToolParameter(name="embeddings", type="array"),
                    ],
                ),
            ],
            tags=["ai", "google", "gemini", "llm", "chat", "embeddings"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client Gemini via le SDK officiel google-genai."""
        from google import genai

        self._client = genai.Client(api_key=config["api_key"])

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "chat":
            return await self._chat(params)
        elif action == "create_embeddings":
            return await self._create_embeddings(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Pas de connexion persistante à fermer."""
        self._client = None

    async def health_check(self) -> bool:
        """Vérifie l'accès à l'API Gemini."""
        try:
            await self._client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents="hi",
                config={"max_output_tokens": 1},
            )
            return True
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        model_type = params.get("type")
        models = GEMINI_MODELS
        if model_type:
            models = [m for m in models if m["type"] == model_type]
        return self.success({"models": models, "count": len(models)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        from google.genai import types

        model = params.get("model", "gemini-2.0-flash")
        messages = params.get("messages", [])
        system_prompt = params.get("system_prompt", "")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)

        if not messages:
            return self.error("messages requis", ConnectorErrorCode.INVALID_PARAMS)

        # Convertir messages au format Gemini (assistant → model)
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.get("content", ""))],
                )
            )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            content = response.text or ""
            usage_meta = response.usage_metadata
            usage = {}
            if usage_meta:
                usage = {
                    "prompt_tokens": usage_meta.prompt_token_count or 0,
                    "completion_tokens": usage_meta.candidates_token_count or 0,
                    "total_tokens": usage_meta.total_token_count or 0,
                }

            finish_reason = ""
            if response.candidates:
                finish_reason = str(response.candidates[0].finish_reason or "")

            return self.success({
                "content": content,
                "model": model,
                "usage": usage,
                "finish_reason": finish_reason,
            })
        except Exception as e:
            err_str = str(e).lower()
            if "403" in err_str or "permission" in err_str:
                return self.error("API key Gemini invalide", ConnectorErrorCode.AUTH_FAILED)
            if "429" in err_str or "resource_exhausted" in err_str:
                return self.error("Rate limit Gemini", ConnectorErrorCode.RATE_LIMITED)
            return self.error(f"Gemini error: {e}", ConnectorErrorCode.PROCESSING_ERROR)

    async def _create_embeddings(self, params: dict[str, Any]) -> ConnectorResult:
        model = params.get("model", "text-embedding-004")
        input_text = params.get("input", "")

        if not input_text:
            return self.error("input requis", ConnectorErrorCode.INVALID_PARAMS)

        try:
            response = await self._client.aio.models.embed_content(
                model=model,
                contents=input_text,
            )
            return self.success({"embeddings": [response.embeddings[0].values]})
        except Exception as e:
            return self.error(f"Embeddings error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
