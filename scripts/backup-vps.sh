#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/entrance-chatbot}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/entrance-chatbot/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

log() {
  printf '[backup] %s\n' "$*"
}

fail() {
  printf '[backup:error] %s\n' "$*" >&2
  exit 1
}

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"

[[ -f "$COMPOSE_FILE" ]] || fail "Missing $APP_DIR/$COMPOSE_FILE"
[[ -f .env.production ]] || fail "Missing $APP_DIR/.env.production"

log "Backing up .env.production"
cp .env.production "$BACKUP_DIR/env.production.backup"
chmod 600 "$BACKUP_DIR/env.production.backup"

backup_volume() {
  local volume_name="$1"
  local output_name="$2"

  if docker volume inspect "$volume_name" >/dev/null 2>&1; then
    log "Backing up Docker volume $volume_name"
    docker run --rm \
      -v "$volume_name:/data:ro" \
      -v "$BACKUP_DIR:/backup" \
      alpine:3.20 \
      tar czf "/backup/${output_name}.tar.gz" -C /data .
  else
    log "Skipping missing Docker volume $volume_name"
  fi
}

backup_volume entrance-chatbot-chroma-data chroma-data
backup_volume entrance-chatbot-redis-data redis-data
backup_volume entrance-chatbot-ollama-data ollama-data

log "Writing service snapshot"
docker compose --env-file .env.production -f "$COMPOSE_FILE" ps > "$BACKUP_DIR/docker-compose-ps.txt" || true
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' > "$BACKUP_DIR/docker-ps.txt" || true

log "Pruning backups older than ${RETENTION_DAYS} days"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -print -exec rm -rf {} +

log "Backup completed at $BACKUP_DIR"
