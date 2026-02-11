"""
ElevenLabs — Connecteur pour l'API ElevenLabs (Text-to-Speech, voix IA).

Catégorie: ai
Auth: api_key

Actions:
    list_models  → Liste les modèles TTS disponibles
    list_voices  → Liste les voix disponibles (préconfigurées + clonées)
    text_to_speech → Convertit du texte en audio (MP3/PCM)
"""

from __future__ import annotations

import base64
from typing import Any

from app.framework.base import BaseConnector
from app.framework.schemas import (
    ConnectorAction,
    ConnectorErrorCode,
    ConnectorMetadata,
    ConnectorResult,
    ToolParameter,
)

ELEVENLABS_MODELS = [
    {"id": "eleven_multilingual_v2", "name": "Multilingual V2", "description": "Best quality, 29 languages, emotional range", "languages": 29},
    {"id": "eleven_turbo_v2_5", "name": "Turbo V2.5", "description": "Low latency, high quality, 32 languages", "languages": 32},
    {"id": "eleven_turbo_v2", "name": "Turbo V2", "description": "Low latency, English-optimized", "languages": 1},
    {"id": "eleven_monolingual_v1", "name": "Monolingual V1", "description": "English only, legacy model", "languages": 1},
    {"id": "eleven_flash_v2_5", "name": "Flash V2.5", "description": "Fastest, lowest latency", "languages": 32},
    {"id": "eleven_flash_v2", "name": "Flash V2", "description": "Fast English model", "languages": 1},
]

DEFAULT_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "accent": "American", "gender": "Female"},
    {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "accent": "American", "gender": "Female"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "accent": "American", "gender": "Female"},
    {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "accent": "American", "gender": "Male"},
    {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "accent": "American", "gender": "Female"},
    {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "accent": "American", "gender": "Male"},
    {"voice_id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "accent": "American", "gender": "Male"},
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "accent": "American", "gender": "Male"},
    {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "accent": "American", "gender": "Male"},
]


class ElevenlabsConnector(BaseConnector):
    """Connecteur ElevenLabs — Text-to-Speech et voix IA."""

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="elevenlabs",
            name="ElevenLabs",
            description="API ElevenLabs — Text-to-Speech, voix IA multilingues",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True,
                              description="ElevenLabs API Key"),
                ToolParameter(name="base_url", type="string",
                              default="https://api.elevenlabs.io",
                              description="URL de base"),
            ],
            actions=[
                ConnectorAction(
                    name="list_models",
                    description="Liste les modèles TTS ElevenLabs",
                    input_schema=[],
                    output_schema=[
                        ToolParameter(name="models", type="array"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="list_voices",
                    description="Liste les voix disponibles (préconfigurées + custom)",
                    input_schema=[
                        ToolParameter(name="fetch_remote", type="boolean", default=False,
                                      description="Récupérer les voix depuis l'API (sinon liste locale)"),
                    ],
                    output_schema=[
                        ToolParameter(name="voices", type="array",
                                      description="[{voice_id, name, accent, gender}]"),
                        ToolParameter(name="count", type="integer"),
                    ],
                ),
                ConnectorAction(
                    name="text_to_speech",
                    description="Convertit du texte en audio",
                    input_schema=[
                        ToolParameter(name="text", type="string", required=True,
                                      description="Texte à convertir en audio"),
                        ToolParameter(name="voice_id", type="string",
                                      default="21m00Tcm4TlvDq8ikWAM",
                                      description="ID de la voix (défaut: Rachel)"),
                        ToolParameter(name="model_id", type="string",
                                      default="eleven_multilingual_v2",
                                      description="Modèle TTS"),
                        ToolParameter(name="stability", type="number", default=0.5,
                                      description="Stabilité de la voix (0.0-1.0)"),
                        ToolParameter(name="similarity_boost", type="number", default=0.75,
                                      description="Fidélité à la voix originale (0.0-1.0)"),
                        ToolParameter(name="output_format", type="string", default="mp3_44100_128",
                                      description="Format: mp3_44100_128, mp3_22050_32, pcm_16000, pcm_44100"),
                    ],
                    output_schema=[
                        ToolParameter(name="audio_base64", type="string",
                                      description="Audio encodé en base64"),
                        ToolParameter(name="content_type", type="string"),
                        ToolParameter(name="size_bytes", type="integer"),
                        ToolParameter(name="model_id", type="string"),
                        ToolParameter(name="voice_id", type="string"),
                    ],
                ),
            ],
            tags=["ai", "elevenlabs", "tts", "voice", "audio", "speech"],
        )

    async def connect(self, config: dict[str, Any]) -> None:
        """Initialise le client HTTP ElevenLabs."""
        import httpx

        self._base_url = config.get("base_url", "https://api.elevenlabs.io")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "xi-api-key": config["api_key"],
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if action == "list_models":
            return await self._list_models(params)
        elif action == "list_voices":
            return await self._list_voices(params)
        elif action == "text_to_speech":
            return await self._text_to_speech(params)
        return self.error(f"Action inconnue: {action}", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        """Ferme le client HTTP."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Vérifie l'accès à l'API ElevenLabs."""
        try:
            resp = await self._client.get("/v1/user")
            return resp.status_code == 200
        except Exception:
            return False

    async def _list_models(self, params: dict[str, Any]) -> ConnectorResult:
        return self.success({"models": ELEVENLABS_MODELS, "count": len(ELEVENLABS_MODELS)})

    async def _list_voices(self, params: dict[str, Any]) -> ConnectorResult:
        fetch_remote = params.get("fetch_remote", False)

        if not fetch_remote:
            return self.success({"voices": DEFAULT_VOICES, "count": len(DEFAULT_VOICES)})

        # Récupérer les voix depuis l'API
        try:
            resp = await self._client.get("/v1/voices")
            if resp.status_code != 200:
                return self.error(
                    f"ElevenLabs voices API {resp.status_code}",
                    ConnectorErrorCode.EXTERNAL_API_ERROR,
                )

            data = resp.json()
            voices = [
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "category": v.get("category", ""),
                    "labels": v.get("labels", {}),
                }
                for v in data.get("voices", [])
            ]
            return self.success({"voices": voices, "count": len(voices)})
        except Exception as e:
            return self.error(f"List voices error: {e}", ConnectorErrorCode.PROCESSING_ERROR)

    async def _text_to_speech(self, params: dict[str, Any]) -> ConnectorResult:
        text = params.get("text", "")
        voice_id = params.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        model_id = params.get("model_id", "eleven_multilingual_v2")
        stability = params.get("stability", 0.5)
        similarity_boost = params.get("similarity_boost", 0.75)
        output_format = params.get("output_format", "mp3_44100_128")

        if not text:
            return self.error("text requis", ConnectorErrorCode.INVALID_PARAMS)

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }

        try:
            url = f"/v1/text-to-speech/{voice_id}"
            resp = await self._client.post(
                url,
                json=payload,
                params={"output_format": output_format},
                headers={"Accept": "audio/mpeg"},
            )

            if resp.status_code == 401:
                return self.error("API key ElevenLabs invalide", ConnectorErrorCode.AUTH_FAILED)
            if resp.status_code == 429:
                return self.error("Rate limit ElevenLabs", ConnectorErrorCode.RATE_LIMITED)
            if resp.status_code != 200:
                return self.error(
                    f"ElevenLabs TTS {resp.status_code}: {resp.text[:300]}",
                    ConnectorErrorCode.EXTERNAL_API_ERROR,
                )

            audio_bytes = resp.content
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            content_type = "audio/mpeg" if "mp3" in output_format else "audio/wav"

            return self.success({
                "audio_base64": audio_b64,
                "content_type": content_type,
                "size_bytes": len(audio_bytes),
                "model_id": model_id,
                "voice_id": voice_id,
            })
        except Exception as e:
            return self.error(f"TTS error: {e}", ConnectorErrorCode.PROCESSING_ERROR)
