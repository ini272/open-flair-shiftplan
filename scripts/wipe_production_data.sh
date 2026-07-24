#!/usr/bin/env bash

# Reset every application record while preserving a restorable database snapshot.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

compose_file_setting="${WIPE_COMPOSE_FILE:-docker-compose.prod.yml}"
if [[ "$compose_file_setting" == /* ]]; then
  COMPOSE_FILE="$compose_file_setting"
else
  COMPOSE_FILE="$PROJECT_DIR/$compose_file_setting"
fi

if [[ $# -ne 1 || "$1" != "--confirm" ]]; then
  printf 'Verwendung: %s --confirm\n' "$(basename "$0")" >&2
  printf 'Der Voll-Reset entfernt alle Nutzer, Gruppen, Schichten und Verfuegbarkeiten.\n' >&2
  exit 2
fi

fail() {
  printf 'Voll-Reset fehlgeschlagen: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker wird auf dem Server benoetigt"
[[ -f "$COMPOSE_FILE" ]] || fail "Compose-Datei nicht gefunden: $COMPOSE_FILE"
[[ -f "$PROJECT_DIR/data/sql_app.db" ]] || fail "Live-Datenbank nicht gefunden"

printf 'Erstelle Rettungs-Backup vor dem Voll-Reset.\n'
BACKUP_DIR="$PROJECT_DIR/backups/pre-wipe" "$SCRIPT_DIR/backup_production.sh"

wipe_timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
staging_directory="$PROJECT_DIR/data/pre-wipe-$wipe_timestamp"

printf 'Stoppe Produktions-Stack.\n'
docker compose -f "$COMPOSE_FILE" down

# The helper runs as the container user, which can move Docker-owned data/ files.
docker compose -f "$COMPOSE_FILE" run --rm --no-deps -T \
  fastapi python - "$(basename "$staging_directory")" <<'PY'
import os
import shutil
import sys

staging_name = sys.argv[1]
data_directory = "/app/data"
database_path = os.path.join(data_directory, "sql_app.db")
staging_directory = os.path.join(data_directory, staging_name)

if not os.path.isfile(database_path):
    raise RuntimeError(f"Database is missing: {database_path}")

os.makedirs(staging_directory, mode=0o700, exist_ok=False)
shutil.move(database_path, os.path.join(staging_directory, "sql_app.db"))
PY

printf 'Starte Produktions-Stack mit leerer Datenbank.\n'
docker compose -f "$COMPOSE_FILE" up -d
docker compose -f "$COMPOSE_FILE" ps

printf 'Voll-Reset erfolgreich gestartet. Bitte die leere App im Browser pruefen.\n'
printf 'Vorherige Datenbank liegt weiterhin hier: %s\n' "$staging_directory"
