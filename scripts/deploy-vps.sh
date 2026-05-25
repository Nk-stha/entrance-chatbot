#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/entrance-chatbot}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8002/health}"
READY_URL="${READY_URL:-http://127.0.0.1:8002/api/v1/health/ready}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-180}"

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy:error] %s\n' "$*" >&2
  exit 1
}

cd "$APP_DIR"

[[ -f "$COMPOSE_FILE" ]] || fail "Missing $APP_DIR/$COMPOSE_FILE"
[[ -f .env.production ]] || fail "Missing $APP_DIR/.env.production"

if grep -q 'REPLACE_' .env.production; then
  fail ".env.production still contains REPLACE_ placeholders"
fi

if ! command -v docker >/dev/null 2>&1; then
  fail "docker is not installed"
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose plugin is not available"
fi

log "Checking whether localhost:8002 is already used by a non-chatbot process"
if sudo ss -tulpn 2>/dev/null | grep -qE '127\.0\.0\.1:8002|0\.0\.0\.0:8002|\[::\]:8002'; then
  if ! docker ps --format '{{.Names}} {{.Ports}}' | grep -q 'entrance-chatbot-backend'; then
    fail "Port 8002 is already in use by another process"
  fi
fi

log "Validating compose configuration"
docker compose --env-file .env.production -f "$COMPOSE_FILE" config >/dev/null

log "Pulling production images"
docker compose --env-file .env.production -f "$COMPOSE_FILE" pull

log "Starting production stack"
docker compose --env-file .env.production -f "$COMPOSE_FILE" up -d --remove-orphans

log "Waiting for health endpoint: $HEALTH_URL"
deadline=$((SECONDS + MAX_WAIT_SECONDS))
until curl -fsS "$HEALTH_URL" >/dev/null; do
  if (( SECONDS >= deadline )); then
    docker compose --env-file .env.production -f "$COMPOSE_FILE" ps
    docker compose --env-file .env.production -f "$COMPOSE_FILE" logs --tail=200 backend
    fail "Health check did not pass within ${MAX_WAIT_SECONDS}s"
  fi
  sleep 5
done

log "Waiting for readiness endpoint: $READY_URL"
deadline=$((SECONDS + MAX_WAIT_SECONDS))
until curl -fsS "$READY_URL" | grep -q '"status":"ready"'; do
  if (( SECONDS >= deadline )); then
    docker compose --env-file .env.production -f "$COMPOSE_FILE" ps
    docker compose --env-file .env.production -f "$COMPOSE_FILE" logs --tail=200 backend
    fail "Readiness check did not pass within ${MAX_WAIT_SECONDS}s"
  fi
  sleep 5
done

log "Verifying safe published ports"
ports="$(docker ps --format '{{.Names}} {{.Ports}}' | grep 'entrance-chatbot' || true)"
printf '%s\n' "$ports"

if printf '%s\n' "$ports" | grep -qE '0\.0\.0\.0:(6379|8001|11434|11435)|:\:\]:(6379|8001|11434|11435)'; then
  fail "Unsafe public chatbot dependency port detected"
fi

if ! printf '%s\n' "$ports" | grep -q 'entrance-chatbot-backend'; then
  fail "Backend container is not running"
fi

log "Deployment completed successfully"
