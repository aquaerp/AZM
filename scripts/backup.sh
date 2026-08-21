#!/usr/bin/env bash
#
# Azm — automated backup script.
#
# Dumps the PostgreSQL database and archives the encrypted media volume
# (uploaded documents/invoices) from a running Docker Compose deployment,
# stores them locally with checksums, optionally uploads them to a remote
# (S3-compatible) location via rclone, and prunes local backups past the
# retention window.
#
# Usage:
#   ./scripts/backup.sh [options]
#
# Options (all optional, with defaults matching deploy/hostinger):
#   --compose-file PATH     Path to the docker-compose file (default: deploy/hostinger/compose.yml)
#   --env-file PATH         Path to the .env file passed to compose (default: deploy/hostinger/.env)
#   --db-service NAME       Name of the PostgreSQL service (default: db)
#   --media-volume NAME     Name of the Docker volume holding /app/media (default: <project>_media_data)
#   --backup-dir PATH       Local directory to store backups (default: ./backups)
#   --retention-days N      Delete local backups older than N days (default: 14)
#   --rclone-remote NAME    rclone remote:path to upload to, e.g. "azm-backup:azm/db" (optional)
#   --require-remote        Fail instead of accepting a local-only backup
#   --healthcheck-url URL   Ping a monitoring endpoint on success, and URL/fail on failure
#
# Exit code is non-zero on any failure so cron/systemd can alert on it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILE="$PROJECT_ROOT/deploy/hostinger/compose.yml"
ENV_FILE="$PROJECT_ROOT/deploy/hostinger/.env"
DB_SERVICE="db"
MEDIA_VOLUME=""
BACKUP_DIR="$PROJECT_ROOT/backups"
RETENTION_DAYS="14"
RCLONE_REMOTE="${AZM_BACKUP_REMOTE:-}"
REQUIRE_REMOTE="${AZM_BACKUP_REQUIRE_REMOTE:-false}"
HEALTHCHECK_URL="${AZM_BACKUP_HEALTHCHECK_URL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --db-service) DB_SERVICE="$2"; shift 2 ;;
    --media-volume) MEDIA_VOLUME="$2"; shift 2 ;;
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
    --rclone-remote) RCLONE_REMOTE="$2"; shift 2 ;;
    --require-remote) REQUIRE_REMOTE="true"; shift ;;
    --healthcheck-url) HEALTHCHECK_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }
fail() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: $*" >&2; exit 1; }

notify_monitor() {
  local suffix="${1:-}"
  [[ -z "$HEALTHCHECK_URL" ]] && return 0
  command -v curl >/dev/null || { log "WARNING: curl is unavailable; monitoring ping skipped."; return 0; }
  curl --fail --silent --show-error --max-time 15 --retry 2 "${HEALTHCHECK_URL}${suffix}" >/dev/null \
    || log "WARNING: monitoring ping to '${HEALTHCHECK_URL}${suffix}' failed."
}

on_exit() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    notify_monitor "/fail"
  fi
}
trap on_exit EXIT

command -v docker >/dev/null || fail "docker is required but was not found in PATH."
if [[ "$REQUIRE_REMOTE" == "true" && -z "$RCLONE_REMOTE" ]]; then
  fail "Remote backup is required but AZM_BACKUP_REMOTE/--rclone-remote is empty."
fi

# Resolve to an absolute path so volume-name auto-detection (based on the
# parent directory name) works regardless of the caller's current directory.
COMPOSE_FILE="$(cd "$(dirname "$COMPOSE_FILE")" && pwd)/$(basename "$COMPOSE_FILE")"

COMPOSE=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ENV_FILE" ]]; then
  COMPOSE+=(--env-file "$ENV_FILE")
fi

TIMESTAMP="$(date -u '+%Y%m%d-%H%M%S')"
mkdir -p "$BACKUP_DIR"

DB_DUMP_FILE="$BACKUP_DIR/azm-db-$TIMESTAMP.sql.gz"
MEDIA_ARCHIVE_FILE="$BACKUP_DIR/azm-media-$TIMESTAMP.tar.gz"
CHECKSUM_FILE="$BACKUP_DIR/azm-$TIMESTAMP.sha256"

log "Starting backup $TIMESTAMP"

# --- 1. Database dump ---------------------------------------------------
log "Dumping PostgreSQL database via '${DB_SERVICE}' service..."
if ! "${COMPOSE[@]}" exec -T "$DB_SERVICE" sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$DB_DUMP_FILE"; then
  rm -f "$DB_DUMP_FILE"
  fail "Database dump failed."
fi
[[ -s "$DB_DUMP_FILE" ]] || fail "Database dump is empty; aborting."
log "Database dump written to $DB_DUMP_FILE ($(du -h "$DB_DUMP_FILE" | cut -f1))"

# --- 2. Media volume archive ---------------------------------------------
if [[ -z "$MEDIA_VOLUME" ]]; then
  # Default Docker Compose volume naming: <project-name>_<volume-key>
  PROJECT_NAME="$(basename "$(dirname "$COMPOSE_FILE")")"
  MEDIA_VOLUME="${PROJECT_NAME}_media_data"
fi

if docker volume inspect "$MEDIA_VOLUME" >/dev/null 2>&1; then
  log "Archiving media volume '$MEDIA_VOLUME'..."
  # MSYS2_ARG_CONV_EXCL prevents Git-Bash-on-Windows from mangling the
  # container-side /data and /backup paths into Windows paths; harmless
  # on native Linux hosts (e.g. the Hostinger deployment target).
  MSYS2_ARG_CONV_EXCL="*" docker run --rm \
    -v "$MEDIA_VOLUME":/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3.20 \
    tar czf "/backup/$(basename "$MEDIA_ARCHIVE_FILE")" -C /data . \
    || fail "Media volume archive failed."
  log "Media archive written to $MEDIA_ARCHIVE_FILE ($(du -h "$MEDIA_ARCHIVE_FILE" | cut -f1))"
else
  log "WARNING: media volume '$MEDIA_VOLUME' not found; skipping media archive."
  MEDIA_ARCHIVE_FILE=""
fi

# --- 3. Checksums ----------------------------------------------------------
( cd "$BACKUP_DIR" && sha256sum "$(basename "$DB_DUMP_FILE")" ${MEDIA_ARCHIVE_FILE:+"$(basename "$MEDIA_ARCHIVE_FILE")"} > "$(basename "$CHECKSUM_FILE")" )
log "Checksums written to $CHECKSUM_FILE"

# --- 4. Optional remote upload (S3-compatible via rclone) ------------------
if [[ -n "$RCLONE_REMOTE" ]]; then
  command -v rclone >/dev/null || fail "rclone is required for --rclone-remote but was not found in PATH."
  log "Uploading backup set to $RCLONE_REMOTE ..."
  rclone copy "$DB_DUMP_FILE" "$RCLONE_REMOTE" || fail "rclone upload of database dump failed."
  [[ -n "$MEDIA_ARCHIVE_FILE" ]] && { rclone copy "$MEDIA_ARCHIVE_FILE" "$RCLONE_REMOTE" || fail "rclone upload of media archive failed."; }
  rclone copy "$CHECKSUM_FILE" "$RCLONE_REMOTE" || fail "rclone upload of checksum file failed."
  log "Verifying uploaded backup set..."
  rclone check "$DB_DUMP_FILE" "$RCLONE_REMOTE" --one-way || fail "Remote database backup verification failed."
  [[ -n "$MEDIA_ARCHIVE_FILE" ]] && { rclone check "$MEDIA_ARCHIVE_FILE" "$RCLONE_REMOTE" --one-way || fail "Remote media backup verification failed."; }
  rclone check "$CHECKSUM_FILE" "$RCLONE_REMOTE" --one-way || fail "Remote checksum verification failed."
  log "Remote upload complete."
else
  log "No --rclone-remote provided; backup kept locally only. Configure remote storage before relying on this in production."
fi

# --- 5. Retention cleanup ----------------------------------------------------
log "Pruning local backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'azm-*' -mtime "+$RETENTION_DAYS" -print -delete || true

log "Backup $TIMESTAMP completed successfully."
notify_monitor
