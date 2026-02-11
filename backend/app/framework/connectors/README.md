# Connectors — Catalogue & Documentation

> Auto-discovered connectors integrating external services (AI APIs, SaaS, etc.).
> Each connector is a Python class extending `BaseConnector` and is automatically registered at startup.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/connectors` | Full catalog with actions and schemas |
| `GET` | `/api/connectors/categories` | Available categories |
| `GET` | `/api/connectors/{slug}` | Connector detail (config schema, actions) |
| `GET` | `/api/connectors/{slug}/actions` | Available actions for a connector |
| `GET` | `/api/connectors/{slug}/health` | Health check for a specific connector |
| `GET` | `/api/connectors/health` | Health check for all connected connectors |
| `POST` | `/api/connectors/{slug}/connect` | Initialize connection (credentials from Vault) |
| `POST` | `/api/connectors/{slug}/disconnect` | Close connection |
| `POST` | `/api/connectors/{slug}/execute` | Execute an action |

**Swagger UI**: Available at `/docs` when the backend is running.

## Built-in Connectors

### AI Category

| Slug | Name | File | Auth | Actions | Description |
|------|------|------|------|---------|-------------|
| `anthropic` | Anthropic | `anthropic_ai.py` | `api_key` | `list_models`, `chat` | Claude Opus 4, Sonnet 4, Haiku |
| `openai` | OpenAI | `openai_ai.py` | `api_key` | `list_models`, `chat`, `create_embeddings` | GPT-4o, o1, o3, embeddings |
| `gemini` | Google Gemini | `gemini_ai.py` | `api_key` | `list_models`, `chat`, `create_embeddings` | Gemini 2.5 Pro, 2.0 Flash, 1.5 Pro |
| `mistral-ai` | Mistral AI | `mistral_ai.py` | `api_key` | `list_models`, `chat`, `create_embeddings` | Large, Small, Codestral, Pixtral |
| `perplexity` | Perplexity | `perplexity_ai.py` | `api_key` | `list_models`, `chat` | Sonar with native web search & citations |
| `nvidia-nim` | NVIDIA NIM | `nvidia_nim.py` | `api_key` | `list_models`, `chat` | Llama, Mixtral, Nemotron, DeepSeek, Qwen |
| `elevenlabs` | ElevenLabs | `elevenlabs.py` | `api_key` | `list_models`, `list_voices`, `text_to_speech` | Text-to-Speech, multilingual AI voices |

## Connector Architecture

Each connector follows this lifecycle:

```
1. Framework retrieves credentials from Vault
2. connector.connect(config)      — Called once per session
3. connector.execute(action, params)  — Called N times
4. connector.disconnect()         — Called at session end
```

### Class Structure

```python
class MyConnector(BaseConnector):
    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            slug="my-connector",
            name="My Connector",
            description="What it connects to",
            version="1.0.0",
            category="ai",
            auth_type="api_key",
            config_schema=[
                ToolParameter(name="api_key", type="string", required=True),
            ],
            actions=[
                ConnectorAction(
                    name="my_action",
                    description="What it does",
                    input_schema=[...],
                    output_schema=[...],
                ),
            ],
        )

    async def connect(self, config: dict) -> None:
        self._client = httpx.AsyncClient(headers={"Authorization": f"Bearer {config['api_key']}"})

    async def execute(self, action: str, params: dict) -> ConnectorResult:
        if action == "my_action":
            return self.success({"result": "..."})
        return self.error("Unknown action", ConnectorErrorCode.INVALID_ACTION)

    async def disconnect(self) -> None:
        await self._client.aclose()
```

## Common Actions

### AI Connectors

All AI connectors support these standard actions:

| Action | Description | Key Params |
|--------|-------------|------------|
| `list_models` | List available models | — |
| `chat` | Send messages to the model | `model`, `messages`, `temperature`, `max_tokens` |
| `create_embeddings` | Generate text embeddings (where supported) | `model`, `input` |

### Chat Action — Input Schema

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | yes | Model ID (e.g., `claude-sonnet-4-20250514`) |
| `messages` | array | yes | Messages `[{role, content}]` |
| `system_prompt` | string | no | System prompt |
| `temperature` | number | no | Temperature (0.0 - 1.0, default 0.7) |
| `max_tokens` | integer | no | Max output tokens (default 4096) |

### Chat Action — Output Schema

| Param | Type | Description |
|-------|------|-------------|
| `content` | string | Generated text |
| `model` | string | Model used |
| `usage` | object | `{input_tokens, output_tokens}` |
| `stop_reason` | string | Why generation stopped |

## Execution Example

```bash
# List all connectors
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/connectors

# Get connector detail
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/connectors/anthropic

# List actions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/connectors/anthropic/actions

# Connect (credentials from Vault)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/connectors/anthropic/connect

# Execute an action
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"action":"chat","params":{"model":"claude-sonnet-4-20250514","messages":[{"role":"user","content":"Hello"}]}}' \
     http://localhost:8000/api/connectors/anthropic/execute
```

## Credential Management

Connector credentials are stored in **HashiCorp Vault** and never exposed to the frontend.

- API keys are stored via `POST /api/llm/providers/{id}/api-key`
- The framework automatically retrieves credentials from Vault during `connect()`
- Connectors never handle raw credentials — they receive pre-fetched config

## Validation

Connector files are validated at load time by `ConnectorValidator`:
- AST analysis for security compliance
- Required method checks (`connect`, `execute`, `metadata`)
- Auth type validation
- Action schema completeness

## Adding a New Connector

1. Create a file in this directory: `my_connector.py`
2. Implement a class extending `BaseConnector`
3. Restart the backend — auto-discovery handles the rest

Or use the CLI generator:
```bash
python -m app.framework.connectors.generator my-connector "My Connector" "Description" category api_key
```

See [CONNECTOR_FRAMEWORK.md](../../../../CONNECTOR_FRAMEWORK.md) for the complete guide.
