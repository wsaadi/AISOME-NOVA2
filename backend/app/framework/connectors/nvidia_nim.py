"""
NVIDIA NIM — Connecteur pour NVIDIA NIM (Llama, Mixtral, Nemotron, etc.).

Catégorie: ai
Auth: api_key

NVIDIA NIM expose des modèles open-source optimisés sur GPU NVIDIA
via une API compatible OpenAI.

Actions:
    list_models  → Liste les modèles NIM disponibles
    chat         → Chat completion avec choix du modèle
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

NVIDIA_NIM_MODELS = [
    {"id": "meta/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "context_window": 128000, "type": "chat", "description": "Meta Llama 3.3, 70B instruct"},
    {"id": "meta/llama-3.1-405b-instruct", "name": "Llama 3.1 405B", "context_window": 128000, "type": "chat", "description": "Largest open model, 405B parameters"},
    {"id": "meta/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "context_window": 128000, "type": "chat", "description": "Strong open model, 70B parameters"},
    {"id": "meta/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "context_window": 128000, "type": "chat", "description": "Fast compact model, 8B parameters"},
    {"id": "mistralai/mixtral-8x22b-instruct-v0.1", "name": "Mixtral 8x22B", "context_window": 65536, "type": "chat", "description": "Mistral MoE model on NIM"},
    {"id": "mistralai/mistral-large-2-instruct", "name": "Mistral Large 2", "context_window": 128000, "type": "chat", "description": "Mistral Large on NIM"},
    {"id": "google/gemma-2-27b-it", "name": "Gemma 2 27B", "context_window": 8192, "type": "chat", "description": "Google Gemma 2 on NIM"},
    {"id": "nvidia/nemotron-4-340b-instruct", "name": "Nemotron 340B", "context_window": 4096, "type": "chat", "description": "NVIDIA's own large model"},
    {"id": "deepseek-ai/deepseek-r1", "name": "DeepSeek R1", "context_window": 65536, "type": "reasoning", "description": "DeepSeek reasoning model on NIM"},
    {"id": "qwen/qwen2.5-72b-instruct", "name": "Qwen 2.5 72B", "context_window": 128000, "type": "chat", "description": "Alibaba Qwen 2.5 on NIM"},
    {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "name": "Nemotron-Llama 70B", "context_window": 128000, "type": "chat", "description": "NVIDIA fine-tuned Llama"},
]


class NvidiaNimConnector(BaseConnector):
    """Connecteur NVIDIA NIM — Modèles open-source optimisés GPU via API OpenAI-compatible."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="nvidia-nim",
            name="NVIDIA NIM",
            description="API NVIDIA NIM — Llama, Mixtral, Nemotron, DeepSeek, Qwen optimisés GPU",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="NVIDIA API Key (nvapi-...)"),
                ToolParameter(name="base_url", type="string",
                              default="https://integrate.api.nvidia.com/v1",
                              description="URL de base NIM"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles NIM disponibles",
                    input_schema=[
                        ToolParameter(name="type", type="string",
                                      description="Filtrer: chat, reasoning"),
                    ],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="chat",
                    description="Chat completion via NIM (API OpenAI-compatible)",
                    input_schema=[
                        ToolParameter(name="model", type="string", required=True,
                                      description="ID du modèle (ex: meta/llama-3.3-70b-instruct)"),
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
            ],
            tags=["ai", "nvidia", "nim", "llama", "open-source", "gpu", "llm"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client NVIDIA NIM via le SDK OpenAI (API compatible)."""
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url") or "https://integrate.api.nvidia.com/v1",
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "chat":
            return await self._chat(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client NVIDIA NIM."""
        if hasattr(self, "_client") and self._client:
            await self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Vérifie l'accès à NVIDIA NIM."""
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        model_type = params.get("type")
        models = NVIDIA_NIM_MODELS
        if model_type:
            models = [m for m in models if m["type"] == model_type]
        return self.success({"models": models, "count": len(models)})

    async def _chat(self, params: dict[str, Any]) -> ConnectorResult:
        import openai

        model = params.get("model", "meta/llama-3.3-70b-instruct")
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
            return self.error("API key NVIDIA invalide", ConnectorErrorCode.AUTH_FAILED)
        except openai.RateLimitError:
            return self.error("Rate limit NVIDIA NIM", ConnectorErrorCode.RATE_LIMITED)
        except openai.APIStatusError as e:
            return self.error(
                f"NVIDIA NIM {e.status_code}: {e.message}",
                ConnectorErrorCode.EXTERNAL_API_ERROR,
            )
        except Exception as e:
            return self.error(f"NVIDIA NIM error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
