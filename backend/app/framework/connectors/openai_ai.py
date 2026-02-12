"""
OpenAI — Connecteur pour l'API OpenAI (GPT-4o, o1, o3, embeddings).

Catégorie: ai
Auth: api_key

Actions:
    list_models       → Liste les modèles disponibles
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

OPENAI_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000, "type": "chat", "description": "Most capable flagship model"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context_window": 128000, "type": "chat", "description": "Fast and affordable"},
    {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "context_window": 128000, "type": "chat", "description": "Previous flagship with vision"},
    {"id": "o1", "name": "o1", "context_window": 200000, "type": "reasoning", "description": "Advanced reasoning model"},
    {"id": "o1-mini", "name": "o1 Mini", "context_window": 128000, "type": "reasoning", "description": "Fast reasoning model"},
    {"id": "o3-mini", "name": "o3 Mini", "context_window": 200000, "type": "reasoning", "description": "Latest reasoning model"},
    {"id": "gpt-4.1", "name": "GPT-4.1", "context_window": 1047576, "type": "chat", "description": "Coding and instruction following"},
    {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "context_window": 1047576, "type": "chat", "description": "Fast GPT-4.1"},
    {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "context_window": 1047576, "type": "chat", "description": "Fastest, most affordable"},
    {"id": "text-embedding-3-large", "name": "Embedding 3 Large", "context_window": 8191, "type": "embedding", "description": "Best embedding model"},
    {"id": "text-embedding-3-small", "name": "Embedding 3 Small", "context_window": 8191, "type": "embedding", "description": "Efficient embedding model"},
]


class OpenaiConnector(BaseConnector):
    """Connecteur OpenAI — Chat completions, reasoning et embeddings."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="openai",
            name="OpenAI",
            description="API OpenAI — GPT-4o, o1, o3, embeddings",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="OpenAI API Key (sk-...)"),
                ToolParameter(name="base_url", type="string",
                              default="https://api.openai.com/v1",
                              description="URL de base (pour proxies ou Azure)"),
                ToolParameter(name="organization", type="string",
                              description="Organization ID (optionnel)"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles OpenAI disponibles",
                    input_schema=[
                        ToolParameter(name="type", type="string",
                                      description="Filtrer par type: chat, reasoning, embedding"),
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
                                      description="ID du modèle (ex: gpt-4o, o1, gpt-4.1)"),
                        ToolParameter(name="messages", type="array", required=True,
                                      description="Messages [{role, content}]"),
                        ToolParameter(name="temperature", type="number", default=0.7),
                        ToolParameter(name="max_tokens", type="integer", default=4096),
                        ToolParameter(name="system_prompt", type="string",
                                      description="System prompt (ajouté en premier message)"),
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
                    description="Génère des embeddings vectoriels",
                    input_schema=[
                        ToolParameter(name="model", type="string",
                                      default="text-embedding-3-small",
                                      description="Modèle d'embedding"),
                        ToolParameter(name="input", type="string", required=True,
                                      description="Texte à vectoriser (ou liste de textes)"),
                    ],
                    output_schema=[
                        ToolParameter(name="embeddings", type="array"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="usage", type="object"),
                    ],
                ),
            ],
            tags=["ai", "openai", "gpt", "llm", "chat", "embeddings", "reasoning"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client OpenAI via le SDK officiel."""
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=config["api_key"],
            organization=config.get("organization"),
            base_url=config.get("base_url") or "https://api.openai.com/v1",
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
        """Ferme le client OpenAI."""
        if hasattr(self, "_client") and self._client:
            await self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Vérifie que l'API key est valide."""
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        model_type = params.get("type")
        models = OPENAI_MODELS
        if model_type:
            models = [m for m in models if m["type"] == model_type]
        return self.success({"models": models, "count": len(models)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        import openai

        model = params.get("model", "gpt-4o")
        messages = list(params.get("messages", []))
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)

        system_prompt = params.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        if not messages:
            return self.error("messages requis", ConnectorErrorCode.INVALID_PARAMS)

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            return self.success({
                "content": choice.message.content or "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else {},
                "finish_reason": choice.finish_reason or "",
            })
        except openai.AuthenticationError:
            return self.error("API key invalide", ConnectorErrorCode.AUTH_FAILED)
        except openai.RateLimitError:
            return self.error("Rate limit OpenAI", ConnectorErrorCode.RATE_LIMITED)
        except openai.APIStatusError as e:
            return self.error(
                f"OpenAI API {e.status_code}: {e.message}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except Exception as e:
            return self.error(f"OpenAI error: {e}", ConnectorErrorCode.PROCESSING_ERROR)

    async def _create_embeddings(self, params: dict[str, Any]) -> ConnectorResult:
        import openai

        model = params.get("model", "text-embedding-3-small")
        input_text = params.get("input", "")

        if not input_text:
            return self.error("input requis", ConnectorErrorCode.INVALID_PARAMS)

        try:
            response = await self._client.embeddings.create(
                model=model,
                input=input_text,
            )
            return self.success({
                "embeddings": [item.embedding for item in response.data],
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else {},
            })
        except openai.APIStatusError as e:
            return self.error(
                f"OpenAI Embeddings {e.status_code}: {e.message}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except Exception as e:
            return self.error(f"Embeddings error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
