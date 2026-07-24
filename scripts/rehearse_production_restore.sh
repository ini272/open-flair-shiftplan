#!/usr/bin/env bash

# Verify that a production database snapshot can be copied and opened safely.
set -euo pipefail
umask 077

if [[ $# -ne 1 ]]; then
  printf 'Verwendung: %s PFAD_ZUM_BACKUP.db\n' "$(basename "$0")" >&2
  exit 2
fi

backup_database="$1"

fail() {
  printf 'Wiederherstellungsprobe fehlgeschlagen: %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 wird auf dem Server benoetigt"
[[ -f "$backup_database" ]] || fail "Backup-Datei nicht gefunden: $backup_database"

restore_directory="$(mktemp -d "${TMPDIR:-/tmp}/open-flair-restore.XXXXXX")"
restored_database="$restore_directory/sql_app.db"

cleanup() {
  rm -rf -- "$restore_directory"
}
trap cleanup EXIT

cp -- "$backup_database" "$restored_database"

printf 'Pruefe wiederhergestellte Kopie in %s\n' "$restore_directory"

python3 - "$restored_database" <<'PY'
import sqlite3
import sys

database_path = sys.argv[1]
connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)

try:
    integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity_check.lower() != "ok":
        raise RuntimeError(f"PRAGMA integrity_check returned: {integrity_check}")

    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(f"PRAGMA foreign_key_check returned {len(foreign_key_errors)} errors")

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    required_tables = {"users", "groups", "shifts"}
    missing_tables = required_tables - tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Expected tables are missing: {missing}")

    for table_name in ("users", "groups", "shifts"):
        count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"{table_name}={count}")
finally:
    connection.close()
PY

printf 'Wiederherstellungsprobe erfolgreich. Die Live-Datenbank wurde nicht veraendert.\n'
