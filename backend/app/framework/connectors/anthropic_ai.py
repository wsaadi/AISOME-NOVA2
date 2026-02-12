"""
Anthropic — Connecteur pour l'API Anthropic (Claude Opus, Sonnet, Haiku).

Catégorie: ai
Auth: api_key

Actions:
    list_models  → Liste les modèles Claude disponibles
    chat         → Messages API avec choix du modèle
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

ANTHROPIC_MODELS = [
    {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "context_window": 200000, "max_output": 32000, "description": "Most capable, complex tasks"},
    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "context_window": 200000, "max_output": 16000, "description": "Best balance of speed and intelligence"},
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "context_window": 200000, "max_output": 8192, "description": "Previous generation, fast and capable"},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "context_window": 200000, "max_output": 8192, "description": "Fastest, most affordable"},
]


class AnthropicConnector(BaseConnector):
    """Connecteur Anthropic — Claude Messages API."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="anthropic",
            name="Anthropic",
            description="API Anthropic — Claude Opus 4, Sonnet 4, Haiku",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="Anthropic API Key (sk-ant-...)"),
                ToolParameter(name="base_url", type="string",
                              default="https://api.anthropic.com",
                              description="URL de base"),
                ToolParameter(name="anthropic_version", type="string",
                              default="2023-06-01",
                              description="Version de l'API Anthropic"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles Claude disponibles",
                    input_schema=[],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="chat",
                    description="Messages API avec choix du modèle",
                    input_schema=[
                        ToolParameter(name="model", type="string", required=True,
                                      description="ID du modèle (ex: claude-sonnet-4-20250514)"),
                        ToolParameter(name="messages", type="array", required=True,
                                      description="Messages [{role, content}]"),
                        ToolParameter(name="system_prompt", type="string",
                                      description="System prompt"),
                        ToolParameter(name="temperature", type="number", default=0.7),
                        ToolParameter(name="max_tokens", type="integer", default=4096),
                    ],
                    output_schema=[
                        ToolParameter(name="content", type="string"),
                        ToolParameter(name="model", type="string"),
                        ToolParameter(name="usage", type="object",
                                      description="{input_tokens, output_tokens}"),
                        ToolParameter(name="stop_reason", type="string"),
                    ],
                ),
            ],
            tags=["ai", "anthropic", "claude", "llm", "chat"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client Anthropic via le SDK officiel."""
        import anthropic

        self._client = anthropic.AsyncAnthropic(
            api_key=config["api_key"],
            base_url=config.get("base_url") or "https://api.anthropic.com",
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "chat":
            return await self._chat(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client Anthropic."""
        if hasattr(self, "_client") and self._client:
            await self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Vérifie que l'API key est valide via un appel minimal."""
        try:
            await self._client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        return self.success({"models": ANTHROPIC_MODELS, "count": len(ANTHROPIC_MODELS)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        import anthropic

        model = params.get("model", "claude-sonnet-4-20250514")
        messages = params.get("messages", [])
        system_prompt = params.get("system_prompt", "")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 4096)

        if not messages:
            return self.error("messages requis", ConnectorErrorCode.INVALID_PARAMS)

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            message = await self._client.messages.create(**kwargs)

            content = "\n".join(
                b.text for b in message.content if b.type == "text"
            )
            return self.success({
                "content": content,
                "model": message.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "stop_reason": message.stop_reason or "",
            })
        except anthropic.AuthenticationError:
            return self.error("API key Anthropic invalide", ConnectorErrorCode.AUTH_FAILED)
        except anthropic.RateLimitError:
            return self.error("Rate limit Anthropic", ConnectorErrorCode.RATE_LIMITED)
        except anthropic.APIStatusError as e:
            return self.error(
                f"Anthropic API {e.status_code}: {e.message}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except Exception as e:
            return self.error(f"Anthropic error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
