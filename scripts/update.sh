#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"

echo "=== NOVA2 Platform Update ==="
echo "Project directory: $PROJECT_DIR"

# Create backup
echo "[1/6] Creating backup..."
mkdir -p "$BACKUP_DIR"
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T postgres pg_dump -U "${POSTGRES_USER:-nova2}" nova2 > "$BACKUP_DIR/db_backup.sql" 2>/dev/null || echo "Warning: DB backup skipped"
cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env.bak" 2>/dev/null || true
echo "Backup saved to: $BACKUP_DIR"

# Pull latest changes
echo "[2/6] Pulling latest changes..."
cd "$PROJECT_DIR"
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git pull origin "$CURRENT_BRANCH"

# Rebuild containers
echo "[3/6] Rebuilding containers..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" build --no-cache

# Run database migrations
echo "[4/6] Running database migrations..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" run --rm backend alembic upgrade head

# Restart services
echo "[5/6] Restarting services..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

# Health check
echo "[6/6] Running health checks..."
sleep 10
if curl -s http://localhost:${BACKEND_PORT:-8000}/api/health | grep -q "ok"; then
    echo "Backend: OK"
else
    echo "Backend: FAILED - Check logs with: docker compose logs backend"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:${FRONTEND_PORT:-3000} | grep -q "200"; then
    echo "Frontend: OK"
else
    echo "Frontend: FAILED - Check logs with: docker compose logs frontend"
fi

echo ""
echo "=== Update complete ==="
echo "To rollback, restore backup from: $BACKUP_DIR"
