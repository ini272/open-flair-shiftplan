# Festival Shift Scripts

## Production Backups
On the production server, create a consistent database snapshot before every
deploy, import, or manual database change:

```bash
cd /srv/open-flair-shiftplan
./scripts/backup_production.sh
```

The script uses SQLite's online backup API, so it also includes data that is
currently in SQLite's WAL journal. It creates three private files in
`backups/`: the database snapshot, the matching `.env`, and a manifest with
checksums, Git commit, and the successful integrity check.

To rehearse that a snapshot can be restored, without touching live data:

```bash
./scripts/rehearse_production_restore.sh backups/open-flair-YYYYMMDDTHHMMSSZ.db
```

The rehearsal copies the snapshot to a temporary directory, checks database
and foreign-key integrity, and prints the number of users, groups, and shifts.

For an actual restore after a failed deploy or import:

```bash
./scripts/restore_production_backup.sh backups/open-flair-YYYYMMDDTHHMMSSZ.db --confirm
```

The script verifies the manifest checksums, rehearses the selected snapshot,
creates a final rescue backup of the current state, then stops and starts the
production stack. The previous database and SQLite WAL files are moved to
`data/pre-restore-.../` rather than deleted. Run the smoke test afterwards.

## Local Recovery Rehearsal
`docker-compose.restore-test.yml` starts only a production-configured FastAPI
container on `127.0.0.1:8000`; it does not contact the public domain. Use it
with `RESTORE_COMPOSE_FILE=docker-compose.restore-test.yml` when rehearsing the
restore script locally.

## Production Shifts
Use `create_production_shifts.py` to create the actual festival shifts from the YAML configuration:

```bash
python scripts/create_production_shifts.py --access-code YOUR_COORDINATOR_CODE
```

Or specify a custom YAML file:
```bash
python scripts/create_production_shifts.py --access-code YOUR_COORDINATOR_CODE --schedule path/to/custom_schedule.yaml
```

## Test Shifts
Use `create_test_shifts.py` to create random test shifts for development:

```bash
COORDINATOR_CODE=YOUR_COORDINATOR_CODE python scripts/create_test_shifts.py
```

## Demo Profiles
Use `seed_demo_profiles.py` to create deterministic demo users and a demo group with different availability patterns:

```bash
python scripts/seed_demo_profiles.py --api-url http://localhost:8000
```

This script assumes shifts already exist and uses the normal access-code login flow.

## Configuration
Edit `festival_schedule.yaml` to customize:
- Festival dates
- Locations (Weinzelt, Bierwagen, etc.)
- Daily schedules with specific times and capacities
- Shift descriptions
