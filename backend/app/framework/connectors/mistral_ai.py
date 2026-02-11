"""
Mistral AI — Connecteur pour l'API Mistral (Large, Small, Codestral, Pixtral, embeddings).

Catégorie: ai
Auth: api_key

Actions:
    list_models       → Liste les modèles Mistral disponibles
    chat              → Chat completion avec choix du modèle
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

MISTRAL_MODELS = [
    {"id": "mistral-large-latest", "name": "Mistral Large", "context_window": 128000, "type": "chat", "description": "Flagship model, top-tier reasoning"},
    {"id": "mistral-small-latest", "name": "Mistral Small", "context_window": 128000, "type": "chat", "description": "Fast and cost-effective"},
    {"id": "codestral-latest", "name": "Codestral", "context_window": 256000, "type": "code", "description": "Specialized for code generation"},
    {"id": "open-mistral-nemo", "name": "Mistral Nemo", "context_window": 128000, "type": "chat", "description": "Open-weight, 12B parameters"},
    {"id": "pixtral-large-latest", "name": "Pixtral Large", "context_window": 128000, "type": "vision", "description": "Multimodal with vision"},
    {"id": "pixtral-12b-2409", "name": "Pixtral 12B", "context_window": 128000, "type": "vision", "description": "Compact multimodal"},
    {"id": "mistral-embed", "name": "Mistral Embed", "context_window": 8192, "type": "embedding", "description": "Text embeddings model"},
]


class MistralConnector(BaseConnector):
    """Connecteur Mistral AI — Chat, code et embeddings."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="mistral-ai",
            name="Mistral AI",
            description="API Mistral — Large, Small, Codestral, Pixtral, embeddings",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="Mistral API Key"),
                ToolParameter(name="base_url", type="string",
                              default="https://api.mistral.ai/v1",
                              description="URL de base"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles Mistral disponibles",
                    input_schema=[
                        ToolParameter(name="type", type="string",
                                      description="Filtrer: chat, code, vision, embedding"),
                    ],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="chat",
                    description="Chat completion avec choix du modèle",
                    input_schema=[
                        ToolParameter(name="model", type="string", required=True,
                                      description="ID du modèle (ex: mistral-large-latest)"),
                        ToolParameter(name="messages", type="array", required=True,
                                      description="Messages [{role, content}]"),
                        ToolParameter(name="temperature", type="number", default=0.7),
                        ToolParameter(name="max_tokens", type="integer", default=4096),
                        ToolParameter(name="system_prompt", type="string"),
                    ],
                    output_schema=[
                        ToolParameter(name="content", type="string"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="usage", type="object"),
                        ToolParameter(name="finish_reason", type="string"),
                    ],
                ),
                ConnectorAction(
                    name="create_embeddings",
                    description="Génère des embeddings vectoriels",
                    input_schema=[
                        ToolParameter(name="model", type="string", default="mistral-embed"),
                        ToolParameter(name="input", type="string", required=True,
                                      description="Texte à vectoriser"),
                    ],
                    output_schema=[
                        ToolParameter(name="embeddings", type="array"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="usage", type="object"),
                    ],
                ),
            ],
            tags=["ai", "mistral", "llm", "chat", "code", "embeddings", "vision"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client HTTP Mistral."""
        import httpx

        self._base_url = config.get("base_url", "https://api.mistral.ai/v1")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "chat":
            return await self._chat(params)
        elif action == "create_embeddings":
            return await self._create_embeddings(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client HTTP."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Vérifie l'accès à l'API Mistral."""
        try:
            resp = await self._client.get("/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        model_type = params.get("type")
        models = MISTRAL_MODELS
        if model_type:
            models = [m for m in models if m["type"] == model_type]
        return self.success({"models": models, "count": len(models)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        model = params.get("model", "mistral-large-latest")
        messages = list(params.get("messages", []))
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)

        system_prompt = params.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        if not messages:
            return self.error("messages requis", ConnectorErrorCode.INVALID_PARAMS)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = await self._client.post("/chat/completions", json=payload)
            if resp.status_code == 401:
                return self.error("API key Mistral invalide", ConnectorErrorCode.AUTH_FAILED)
            if resp.status_code == 429:
                return self.error("Rate limit Mistral", ConnectorErrorCode.RATE_LIMITED)
            if resp.status_code != 200:
                return self.error(
                    f"Mistral API {resp.status_code}: {resp.text[:300]}",
                    ConnectorErrorCode.EXTERNAL_API_ERROR,
                )

            data = resp.json()
            choice = data["choices"][0]
            return self.success({
                "content": choice["message"]["content"],
                "model": data.get("model", model),
                "usage": data.get("usage", {}),
                "finish_reason": choice.get("finish_reason", ""),
            })
        except Exception as e:
            return self.error(f"Mistral error: {e}", ConnectorErrorCode.PROCESSING_ERROR)

    async def _create_embeddings(self, params: dict[str, Any]) -> ConnectorResult:
        model = params.get("model", "mistral-embed")
        input_text = params.get("input", "")

        if not input_text:
            return self.error("input requis", ConnectorErrorCode.INVALID_PARAMS)

        payload = {"model": model, "input": [input_text]}

        try:
            resp = await self._client.post("/embeddings", json=payload)
            if resp.status_code != 200:
                return self.error(
                    f"Mistral Embeddings {resp.status_code}: {resp.text[:300]}",
                    ConnectorErrorCode.EXTERNAL_API_ERROR,
                )

            data = resp.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return self.success({
                "embeddings": embeddings,
                "model": data.get("model", model),
                "usage": data.get("usage", {}),
            })
        except Exception as e:
            return self.error(f"Embeddings error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
