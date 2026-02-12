"""
Perplexity — Connecteur pour l'API Perplexity (Sonar, recherche augmentée).

Catégorie: ai
Auth: api_key

Perplexity est spécialisé dans les réponses avec sources web (RAG natif).
L'API est compatible OpenAI.

Actions:
    list_models  → Liste les modèles Sonar disponibles
    chat         → Chat completion avec recherche web intégrée
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

PERPLEXITY_MODELS = [
    {"id": "sonar-pro", "name": "Sonar Pro", "context_window": 200000, "type": "search", "description": "Premier model, best for complex research"},
    {"id": "sonar", "name": "Sonar", "context_window": 128000, "type": "search", "description": "Lightweight, fast search model"},
    {"id": "sonar-reasoning-pro", "name": "Sonar Reasoning Pro", "context_window": 128000, "type": "reasoning", "description": "Advanced reasoning with search"},
    {"id": "sonar-reasoning", "name": "Sonar Reasoning", "context_window": 128000, "type": "reasoning", "description": "Reasoning with search"},
    {"id": "sonar-deep-research", "name": "Sonar Deep Research", "context_window": 128000, "type": "research", "description": "Multi-step deep research agent"},
]


class PerplexityConnector(BaseConnector):
    """Connecteur Perplexity — Recherche augmentée avec sources web."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="perplexity",
            name="Perplexity",
            description="API Perplexity — Sonar avec recherche web intégrée et citations",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="Perplexity API Key (pplx-...)"),
                ToolParameter(name="base_url", type="string",
                              default="https://api.perplexity.ai",
                              description="URL de base"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles Perplexity Sonar disponibles",
                    input_schema=[
                        ToolParameter(name="type", type="string",
                                      description="Filtrer: search, reasoning, research"),
                    ],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="chat",
                    description="Chat avec recherche web intégrée et citations",
                    input_schema=[
                        ToolParameter(name="model", type="string", required=True,
                                      description="ID du modèle (ex: sonar-pro, sonar)"),
                        ToolParameter(name="messages", type="array", required=True,
                                      description="Messages [{role, content}]"),
                        ToolParameter(name="temperature", type="number", default=0.2),
                        ToolParameter(name="max_tokens", type="integer", default=4096),
                        ToolParameter(name="system_prompt", type="string"),
                        ToolParameter(name="search_recency_filter", type="string",
                                      description="Filtre temporel: month, week, day, hour"),
                        ToolParameter(name="return_citations", type="boolean", default=True,
                                      description="Retourner les sources/citations"),
                    ],
                    output_schema=[
                        ToolParameter(name="content", type="string"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="citations", type="array",
                                      description="URLs des sources citées"),
                        ToolParameter(name="usage", type="object"),
                        ToolParameter(name="finish_reason", type="string"),
                    ],
                ),
            ],
            tags=["ai", "perplexity", "sonar", "search", "rag", "citations", "research"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client Perplexity via le SDK OpenAI (API compatible)."""
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url") or "https://api.perplexity.ai",
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "chat":
            return await self._chat(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client Perplexity."""
        if hasattr(self, "_client") and self._client:
            await self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Vérifie l'accès à l'API Perplexity."""
        try:
            await self._client.chat.completions.create(
                model="sonar",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        model_type = params.get("type")
        models = PERPLEXITY_MODELS
        if model_type:
            models = [m for m in models if m["type"] == model_type]
        return self.success({"models": models, "count": len(models)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        import openai

        model = params.get("model", "sonar")
        messages = list(params.get("messages", []))
        temperature = params.get("temperature", 0.2)
        max_tokens = params.get("max_tokens", 4096)

        system_prompt = params.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        if not messages:
            return self.error("messages requis", ConnectorErrorCode.INVALID_PARAMS)

        # Perplexity-specific extra params via extra_body
        extra_body: dict[str, Any] = {}
        if params.get("search_recency_filter"):
            extra_body["search_recency_filter"] = params["search_recency_filter"]
        if params.get("return_citations", True):
            extra_body["return_citations"] = True

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body or None,
            )
            choice = response.choices[0]

            # Citations are in the raw response (Perplexity extension)
            citations = getattr(response, "citations", [])

            return self.success({
                "content": choice.message.content or "",
                "model": response.model,
                "citations": citations,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else {},
                "finish_reason": choice.finish_reason or "",
            })
        except openai.AuthenticationError:
            return self.error("API key Perplexity invalide", ConnectorErrorCode.AUTH_FAILED)
        except openai.RateLimitError:
            return self.error("Rate limit Perplexity", ConnectorErrorCode.RATE_LIMITED)
        except openai.APIStatusError as e:
            return self.error(
                f"Perplexity API {e.status_code}: {e.message}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except Exception as e:
            return self.error(f"Perplexity error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
