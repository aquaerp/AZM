#!/usr/bin/env bash
#
# Azm — restore script.
#
# Restores a PostgreSQL dump and/or media archive produced by scripts/backup.sh
# into a running Docker Compose deployment. Designed to be run against a
# staging/disaster-recovery environment first to validate a backup before
# ever running it against production.
#
# Usage:
#   ./scripts/restore.sh --db-dump backups/azm-db-20260810-120000.sql.gz \
#                         [--media-archive backups/azm-media-20260810-120000.tar.gz] \
#                         [--compose-file deploy/hostinger/compose.yml] \
#                         [--env-file deploy/hostinger/.env] \
#                         [--project-name azm-staging] \
#                         [--db-service db] [--media-volume azm_media_data] \
#                         [--checksum-file backups/azm-20260810-120000.sha256] \
#                         [--yes]
#
# By default the script requires interactive confirmation because it is
# DESTRUCTIVE: it drops and recreates the target database, and replaces the
# contents of the media volume. Pass --yes to skip the prompt (e.g. in
# scripted DR drills against an isolated environment).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILE="$PROJECT_ROOT/deploy/hostinger/compose.yml"
ENV_FILE="$PROJECT_ROOT/deploy/hostinger/.env"
PROJECT_NAME=""
DB_SERVICE="db"
MEDIA_VOLUME=""
DB_DUMP=""
MEDIA_ARCHIVE=""
CHECKSUM_FILE=""
ASSUME_YES="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --db-service) DB_SERVICE="$2"; shift 2 ;;
    --media-volume) MEDIA_VOLUME="$2"; shift 2 ;;
    --db-dump) DB_DUMP="$2"; shift 2 ;;
    --media-archive) MEDIA_ARCHIVE="$2"; shift 2 ;;
    --checksum-file) CHECKSUM_FILE="$2"; shift 2 ;;
    --yes) ASSUME_YES="1"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }
fail() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: $*" >&2; exit 1; }

[[ -n "$DB_DUMP" ]] || fail "--db-dump is required."
[[ -f "$DB_DUMP" ]] || fail "Database dump not found: $DB_DUMP"
if [[ -n "$MEDIA_ARCHIVE" && ! -f "$MEDIA_ARCHIVE" ]]; then
  fail "Media archive not found: $MEDIA_ARCHIVE"
fi
if [[ -n "$CHECKSUM_FILE" && ! -f "$CHECKSUM_FILE" ]]; then
  fail "Checksum file not found: $CHECKSUM_FILE"
fi

command -v docker >/dev/null || fail "docker is required but was not found in PATH."

# Resolve to an absolute path so volume-name auto-detection (based on the
# parent directory name) works regardless of the caller's current directory.
COMPOSE_FILE="$(cd "$(dirname "$COMPOSE_FILE")" && pwd)/$(basename "$COMPOSE_FILE")"

COMPOSE=(docker compose -f "$COMPOSE_FILE")
if [[ -n "$PROJECT_NAME" ]]; then
  COMPOSE+=(-p "$PROJECT_NAME")
fi
if [[ -f "$ENV_FILE" ]]; then
  COMPOSE+=(--env-file "$ENV_FILE")
fi

if [[ -z "$MEDIA_VOLUME" ]]; then
  if [[ -n "$PROJECT_NAME" ]]; then
    RESOLVED_PROJECT_NAME="$PROJECT_NAME"
  else
    RESOLVED_PROJECT_NAME="$(basename "$(dirname "$COMPOSE_FILE")")"
  fi
  MEDIA_VOLUME="${RESOLVED_PROJECT_NAME}_media_data"
fi

if [[ -n "$CHECKSUM_FILE" ]]; then
  log "Verifying backup checksums before destructive restore..."
  CHECKSUM_DIR="$(cd "$(dirname "$CHECKSUM_FILE")" && pwd)"
  DB_DUMP_DIR="$(cd "$(dirname "$DB_DUMP")" && pwd)"
  [[ "$DB_DUMP_DIR" == "$CHECKSUM_DIR" ]] \
    || fail "Database dump and checksum file must be in the same directory."
  grep -F -- "  $(basename "$DB_DUMP")" "$CHECKSUM_FILE" >/dev/null \
    || fail "Checksum file does not contain the selected database dump."
  if [[ -n "$MEDIA_ARCHIVE" ]]; then
    MEDIA_ARCHIVE_DIR="$(cd "$(dirname "$MEDIA_ARCHIVE")" && pwd)"
    [[ "$MEDIA_ARCHIVE_DIR" == "$CHECKSUM_DIR" ]] \
      || fail "Media archive and checksum file must be in the same directory."
    grep -F -- "  $(basename "$MEDIA_ARCHIVE")" "$CHECKSUM_FILE" >/dev/null \
      || fail "Checksum file does not contain the selected media archive."
  fi
  (cd "$CHECKSUM_DIR" && sha256sum -c "$(basename "$CHECKSUM_FILE")") \
    || fail "Backup checksum verification failed; restore was not started."
  log "Backup checksums verified."
else
  log "WARNING: no --checksum-file provided; backup integrity was not verified by this command."
fi

if [[ "$ASSUME_YES" != "1" ]]; then
  echo "This will DROP and RECREATE the database used by service '$DB_SERVICE'"
  echo "and REPLACE the contents of media volume '$MEDIA_VOLUME'."
  read -r -p "Type 'yes' to continue: " CONFIRM
  [[ "$CONFIRM" == "yes" ]] || fail "Aborted by user."
fi

log "Terminating active connections and recreating the target database..."
cat <<'EOSQL' | "${COMPOSE[@]}" exec -T "$DB_SERVICE" sh -c 'psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=0 -v dbname="$POSTGRES_DB"' >/dev/null
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :'dbname' AND pid <> pg_backend_pid();
EOSQL

"${COMPOSE[@]}" exec -T "$DB_SERVICE" sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  || fail "Failed to drop/recreate the target database."

gunzip -c "$DB_DUMP" | "${COMPOSE[@]}" exec -T "$DB_SERVICE" sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  || fail "Failed to load the database dump."
log "Database restore completed."

if [[ -n "$MEDIA_ARCHIVE" ]]; then
  log "Restoring media volume '$MEDIA_VOLUME' from $MEDIA_ARCHIVE ..."
  docker volume inspect "$MEDIA_VOLUME" >/dev/null 2>&1 || docker volume create "$MEDIA_VOLUME" >/dev/null
  # MSYS2_ARG_CONV_EXCL prevents Git-Bash-on-Windows from mangling the
  # container-side /data and /backup paths into Windows paths; harmless
  # on native Linux hosts (e.g. the Hostinger deployment target).
  MSYS2_ARG_CONV_EXCL="*" docker run --rm \
    -v "$MEDIA_VOLUME":/data \
    -v "$(cd "$(dirname "$MEDIA_ARCHIVE")" && pwd)":/backup:ro \
    alpine:3.20 \
    sh -c "rm -rf /data/* /data/..?* /data/.[!.]* 2>/dev/null; tar xzf /backup/$(basename "$MEDIA_ARCHIVE") -C /data" \
    || fail "Failed to restore the media volume."
  log "Media restore completed."
else
  log "No --media-archive provided; skipped media restore."
fi

log "Restore finished. Run 'docker compose ... exec api python manage.py migrate --check' and verify the application before serving production traffic."
