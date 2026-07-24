#!/usr/bin/env bash

# Create a consistent SQLite snapshot while the production app is running.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

if [[ -z "${BACKUP_DIR:-}" ]]; then
  BACKUP_DIR="$PROJECT_DIR/backups"
elif [[ "$BACKUP_DIR" != /* ]]; then
  BACKUP_DIR="$PROJECT_DIR/$BACKUP_DIR"
fi

DATABASE_PATH="$PROJECT_DIR/data/sql_app.db"
ENV_PATH="$PROJECT_DIR/.env"

fail() {
  printf 'Backup fehlgeschlagen: %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 wird auf dem Server benoetigt"
[[ -f "$DATABASE_PATH" ]] || fail "Live-Datenbank nicht gefunden: $DATABASE_PATH"
[[ -f "$ENV_PATH" ]] || fail ".env nicht gefunden: $ENV_PATH"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_id="open-flair-$timestamp"
database_backup="$BACKUP_DIR/$backup_id.db"
environment_backup="$BACKUP_DIR/$backup_id.env"
manifest="$BACKUP_DIR/$backup_id.txt"
temporary_database_backup="$BACKUP_DIR/.$backup_id.db.tmp"

if [[ -e "$database_backup" || -e "$environment_backup" || -e "$manifest" ]]; then
  fail "Backup mit diesem Zeitstempel existiert bereits: $backup_id"
fi

cleanup() {
  rm -f -- "$temporary_database_backup"
}
trap cleanup EXIT

printf 'Erstelle SQLite-Snapshot: %s\n' "$database_backup"

# sqlite3.Connection.backup creates a consistent snapshot while the app is writing.
python3 - "$DATABASE_PATH" "$temporary_database_backup" <<'PY'
import sqlite3
import sys

source_path, target_path = sys.argv[1:]
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
target = sqlite3.connect(target_path)

try:
    source.backup(target)
    integrity_check = target.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity_check.lower() != "ok":
        raise RuntimeError(f"PRAGMA integrity_check returned: {integrity_check}")
finally:
    target.close()
    source.close()
PY

mv -- "$temporary_database_backup" "$database_backup"
cp -- "$ENV_PATH" "$environment_backup"
chmod 600 "$database_backup" "$environment_backup"

git_commit="unknown"
if git -C "$PROJECT_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
  git_commit="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
fi

database_checksum="$(sha256sum "$database_backup" | awk '{print $1}')"
environment_checksum="$(sha256sum "$environment_backup" | awk '{print $1}')"

printf '%s\n' \
  "created_at_utc=$timestamp" \
  "git_commit=$git_commit" \
  "database_file=$(basename "$database_backup")" \
  "database_sha256=$database_checksum" \
  "environment_file=$(basename "$environment_backup")" \
  "environment_sha256=$environment_checksum" \
  "integrity_check=ok" \
  > "$manifest"
chmod 600 "$manifest"

trap - EXIT

printf 'Backup erfolgreich erstellt.\n'
printf '  Datenbank: %s\n' "$database_backup"
printf '  Umgebung:  %s\n' "$environment_backup"
printf '  Manifest:  %s\n' "$manifest"
