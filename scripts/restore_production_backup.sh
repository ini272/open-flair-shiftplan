#!/usr/bin/env bash

# Restore a verified production snapshot with a final rescue backup first.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

compose_file_setting="${RESTORE_COMPOSE_FILE:-docker-compose.prod.yml}"
if [[ "$compose_file_setting" == /* ]]; then
  COMPOSE_FILE="$compose_file_setting"
else
  COMPOSE_FILE="$PROJECT_DIR/$compose_file_setting"
fi

if [[ $# -ne 2 || "$2" != "--confirm" ]]; then
  printf 'Verwendung: %s BACKUP.db --confirm\n' "$(basename "$0")" >&2
  printf 'Der Restore stoppt die App und ersetzt die Live-Datenbank.\n' >&2
  exit 2
fi

backup_database="$1"
if [[ "$backup_database" != /* ]]; then
  backup_database="$PROJECT_DIR/$backup_database"
fi

fail() {
  printf 'Restore fehlgeschlagen: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker wird auf dem Server benoetigt"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum wird auf dem Server benoetigt"
[[ -f "$COMPOSE_FILE" ]] || fail "Compose-Datei nicht gefunden: $COMPOSE_FILE"
[[ -f "$backup_database" ]] || fail "Backup-Datei nicht gefunden: $backup_database"

case "$backup_database" in
  *.db) backup_prefix="${backup_database%.db}" ;;
  *) fail "Backup-Datei muss auf .db enden" ;;
esac

backup_environment="$backup_prefix.env"
backup_manifest="$backup_prefix.txt"
[[ -f "$backup_environment" ]] || fail "Passende .env-Datei nicht gefunden: $backup_environment"
[[ -f "$backup_manifest" ]] || fail "Passendes Manifest nicht gefunden: $backup_manifest"

case "$backup_database" in
  "$PROJECT_DIR"/backups/*) ;;
  *) fail "Backup-Datei muss innerhalb von $PROJECT_DIR/backups liegen" ;;
esac

manifest_value() {
  awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$backup_manifest"
}

expected_database_file="$(manifest_value database_file)"
expected_database_checksum="$(manifest_value database_sha256)"
expected_environment_file="$(manifest_value environment_file)"
expected_environment_checksum="$(manifest_value environment_sha256)"
manifest_integrity="$(manifest_value integrity_check)"

[[ "$(basename "$backup_database")" == "$expected_database_file" ]] || fail "Manifest passt nicht zur Datenbank-Datei"
[[ "$(basename "$backup_environment")" == "$expected_environment_file" ]] || fail "Manifest passt nicht zur .env-Datei"
[[ "$manifest_integrity" == "ok" ]] || fail "Manifest bestaetigt keinen erfolgreichen Integritaetscheck"

database_checksum="$(sha256sum "$backup_database" | awk '{print $1}')"
environment_checksum="$(sha256sum "$backup_environment" | awk '{print $1}')"
[[ "$database_checksum" == "$expected_database_checksum" ]] || fail "Pruefsumme der Datenbank stimmt nicht mit dem Manifest ueberein"
[[ "$environment_checksum" == "$expected_environment_checksum" ]] || fail "Pruefsumme der .env stimmt nicht mit dem Manifest ueberein"

printf 'Pruefe Snapshot vor dem Restore.\n'
"$SCRIPT_DIR/rehearse_production_restore.sh" "$backup_database"

printf 'Erstelle Rettungs-Backup des aktuellen Live-Stands.\n'
BACKUP_DIR="$PROJECT_DIR/backups/pre-restore" "$SCRIPT_DIR/backup_production.sh"

restore_timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
staging_directory="$PROJECT_DIR/data/pre-restore-$restore_timestamp"
backup_database_name="$(basename "$backup_database")"

printf 'Stoppe Produktions-Stack.\n'
docker compose -f "$COMPOSE_FILE" down

# The helper runs as the container user, which can safely handle Docker-owned data/ files.
docker compose -f "$COMPOSE_FILE" run --rm --no-deps -T \
  -v "$PROJECT_DIR/backups:/app/backups" \
  fastapi python - "$backup_database_name" "$(basename "$staging_directory")" <<'PY'
import os
import shutil
import sys

backup_name, staging_name = sys.argv[1:]
data_directory = "/app/data"
backup_database = os.path.join("/app/backups", backup_name)
staging_directory = os.path.join(data_directory, staging_name)

if not os.path.isfile(backup_database):
    raise RuntimeError(f"Backup is not mounted in the helper container: {backup_database}")

os.makedirs(staging_directory, mode=0o700, exist_ok=False)
for filename in ("sql_app.db",):
    source = os.path.join(data_directory, filename)
    if os.path.exists(source):
        shutil.move(source, os.path.join(staging_directory, filename))

shutil.copyfile(backup_database, os.path.join(data_directory, "sql_app.db"))
os.chmod(os.path.join(data_directory, "sql_app.db"), 0o600)
PY

cp -- "$backup_environment" "$PROJECT_DIR/.env"
chmod 600 "$PROJECT_DIR/.env"

printf 'Starte Produktions-Stack mit wiederhergestellter Datenbank.\n'
docker compose -f "$COMPOSE_FILE" up -d
docker compose -f "$COMPOSE_FILE" ps

printf 'Restore erfolgreich gestartet. Bitte jetzt den Smoke-Test aus GO_LIVE.md ausfuehren.\n'
printf 'Vorheriger Stand liegt weiterhin hier: %s\n' "$staging_directory"
