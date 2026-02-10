#!/bin/bash
set -e

echo "=== NOVA2 Platform Initialization ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Copy env if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "Created .env from .env.example"
fi

# Start all services
echo "Starting services..."
cd "$PROJECT_DIR"
docker compose up -d --build

# Wait for services
echo "Waiting for services to be ready..."
sleep 15

# Run migrations
echo "Running database migrations..."
docker compose exec -T backend alembic upgrade head

# Initialize vault secrets engine
echo "Initializing Vault..."
docker compose exec -T vault vault secrets enable -path=nova2 kv-v2 2>/dev/null || echo "Vault secrets engine already enabled"

echo ""
echo "=== NOVA2 Platform is ready ==="
echo "Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "Backend API: http://localhost:${BACKEND_PORT:-8000}/docs"
echo "MinIO Console: http://localhost:${MINIO_CONSOLE_PORT:-9001}"
echo "Vault UI: http://localhost:${VAULT_PORT:-8200}"
echo ""
echo "Default admin credentials:"
echo "  Email: ${ADMIN_EMAIL:-admin@nova2.local}"
echo "  Password: ${ADMIN_PASSWORD:-Admin123!}"
