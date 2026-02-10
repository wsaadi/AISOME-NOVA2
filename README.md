# AISOME-NOVA2 - AI Agentic Platform

Enterprise-grade platform for building, managing, and monitoring AI agents with full RBAC, consumption tracking, and multi-provider LLM integration.

## Features

- **Secure Authentication** - JWT-based auth with access/refresh tokens, enterprise-grade security
- **User Management & RBAC** - Fine-grained role-based access control with configurable permissions
- **LLM Configuration** - Multi-provider support with API keys securely stored in HashiCorp Vault
- **Consumption Tracking** - Token in/out tracking per user, agent, provider with interactive charts (line, bar, pie, donut, area)
- **Quotas** - Configurable usage quotas by user/role/agent/provider, in tokens or financial terms, per day/week/month/year
- **Cost Management** - Editable pricing grids for token costs per model per provider
- **Moderation** - GLiNER2-based content moderation with PII detection, anonymization, and configurable rules
- **Agent System** - Standardized agent architecture with export/import for cross-platform portability
- **Agent Catalog** - Role-based agent visibility and management (duplicate, rename, delete, export, import)
- **Accessibility** - Full accessibility support: high contrast, large text, color blind modes, screen reader optimization, dyslexia font
- **Internationalization** - Full i18n in English, French, and Spanish
- **Themes** - Light and dark themes with accessibility overlays
- **Update System** - Built-in software update mechanism with backup and rollback

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 18 + TypeScript + MUI v5 + Recharts |
| Backend | Python + FastAPI + SQLAlchemy (async) |
| Database | PostgreSQL 16 |
| Secrets | HashiCorp Vault (OSS) |
| Storage | MinIO (S3-compatible) |
| Migrations | Alembic |
| Infra | Docker Compose |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env as needed

# 2. Start everything
bash scripts/init.sh

# Or manually:
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

The platform will be available at:
- **Frontend**: http://localhost:3000
- **Backend API / Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **Vault UI**: http://localhost:8200

### Default Admin Credentials

- **Email**: admin@nova2.local
- **Password**: Admin123!

## Project Structure

```
AISOME-NOVA2/
├── docker-compose.yml          # All services orchestration
├── .env.example                # Environment variables template
├── scripts/
│   ├── init.sh                 # First-time setup
│   └── update.sh               # Platform update script
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # Database migrations
│   └── app/
│       ├── main.py             # FastAPI application
│       ├── config.py           # Settings (Pydantic)
│       ├── database.py         # Async SQLAlchemy engine
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic request/response schemas
│       ├── routers/            # API route handlers
│       ├── services/           # Business logic (auth, vault, RBAC, moderation, agents)
│       ├── middleware/         # Auth middleware, permission checks
│       └── i18n/               # Backend translations (en, fr, es)
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.tsx             # Root component with routing
        ├── i18n/               # i18next config + locale files (en, fr, es)
        ├── themes/             # Light, dark, accessibility themes
        ├── contexts/           # Auth + Theme React contexts
        ├── services/           # API client with auto-refresh
        ├── components/         # Layout, navigation
        └── pages/              # All application pages
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | Authenticate and get tokens |
| `POST /api/auth/refresh` | Refresh access token |
| `GET /api/auth/me` | Current user info + permissions |
| `CRUD /api/users` | User management |
| `CRUD /api/roles` | Role management with permissions |
| `GET/POST /api/llm/providers` | LLM provider configuration |
| `POST /api/llm/providers/{id}/api-key` | Store API key in Vault |
| `GET /api/consumption` | Consumption data with filters |
| `GET /api/consumption/summary` | Aggregated consumption for charts |
| `CRUD /api/quotas` | Quota management |
| `CRUD /api/costs` | Cost grid management |
| `CRUD /api/moderation/rules` | Moderation rule management |
| `POST /api/moderation/test` | Test moderation on text |
| `GET /api/agents` | Agent catalog (role-filtered) |
| `POST /api/agents/{id}/export` | Export agent as ZIP |
| `POST /api/agents/import` | Import agent from ZIP |
| `POST /api/agents/{id}/duplicate` | Duplicate an agent |
| `GET /api/system/version` | Current version |
| `GET /api/system/check-update` | Check for updates |
| `POST /api/system/update` | Apply platform update |

## Updating

```bash
bash scripts/update.sh
```

This will: backup the database, pull latest code, rebuild containers, run migrations, and restart services.

## License

Proprietary - AISOME
