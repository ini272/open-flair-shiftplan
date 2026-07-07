# Go Live

Kurzleitfaden fuer den Live-Betrieb der Open-Flair-Schichtplan-App.

## Annahmen

- Produktions-Repo liegt auf dem Server unter `/srv/open-flair-shiftplan`
- Produktivstart erfolgt mit `docker compose -f docker-compose.prod.yml up -d --build`
- Produktionsdatenbank ist `data/sql_app.db`
- HTTPS laeuft ueber Caddy

## Vor Livegang

1. `.env` pruefen
   - `APP_DOMAIN`
   - `EVENT_CODE`
   - `COORDINATOR_CODE`
   - `SESSION_SECRET_KEY`
   - `COOKIE_SECURE=true`
2. Sicherstellen, dass keine Demo-Daten mehr in `data/sql_app.db` liegen
3. Aktuellen Commit notieren
4. Ein frisches Backup ziehen
5. Smoke-Test gegen die echte Domain machen

## Backup

Vor jedem Deploy, Datenimport oder groesseren Eingriff:

```bash
cd /srv/open-flair-shiftplan
ts=$(date +%Y%m%d-%H%M%S)
cp data/sql_app.db "data/sql_app.db.backup-$ts"
cp .env ".env.backup-$ts"
```

Zusaetzlich sinnvoll:

- den Backup-Ordner gelegentlich vom Server herunterladen
- mindestens taeglich ein DB-Backup behalten, solange das Event laeuft

## Deploy

```bash
cd /srv/open-flair-shiftplan
git fetch
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100
```

## Smoke-Test

Nach jedem Deploy kurz pruefen:

1. Domain im Browser oeffnen
2. Teilnehmer-Login mit `EVENT_CODE`
3. Koordinator-Login mit `COORDINATOR_CODE`
4. Bestehenden Nutzer per E-Mail wiederfinden
5. Alleine anmelden
6. 2er- oder 3er-Gruppe anmelden
7. Schicht auf `Nicht moeglich` setzen und wieder zuruecksetzen
8. Weinzelt/Bierwagen-Praeferenz aendern
9. Plan generieren
10. XLSX-Export testen

## Inhaltliche Regeln im Live-Betrieb

- `scripts/create_production_shifts.py --clear-existing` nur verwenden, wenn wirklich alle Schichten und Zuweisungen neu aufgebaut werden sollen
- Demo-Skripte nicht auf der Live-DB ausprobieren, wenn schon echte Daten vorhanden sind
- Vor jedem Import, Reseed oder DB-Tausch immer erst Backup ziehen
- Immer klar halten:
  - welche DB ist live
  - welche Codes sind live
  - welcher Commit ist live

## Demo-Daten aufsetzen

Wenn der Server leer ist und Demo-Daten benoetigt werden:

1. Demo-Teilnehmer und Teams anlegen

```bash
cd /srv/open-flair-shiftplan
uv run python scripts/seed_demo_roster.py \
  --roster demo_liste.txt \
  --api-url https://of-weinzelt-schichtplan.ini272.de \
  --participant-access-code "$EVENT_CODE" \
  --coordinator-access-code "$COORDINATOR_CODE"
```

2. Schichten anlegen

```bash
cd /srv/open-flair-shiftplan
uv run python scripts/create_production_shifts.py \
  --access-code "$COORDINATOR_CODE" \
  --api-url https://of-weinzelt-schichtplan.ini272.de
```

Hinweis:

- `seed_demo_roster.py` legt Nutzer und Gruppen an, aber keine Schichten, Opt-outs oder Zuteilungen

## Logs und Status

```bash
cd /srv/open-flair-shiftplan
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

Einzelne Services:

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 caddy
docker compose -f docker-compose.prod.yml logs --tail=100 fastapi
docker compose -f docker-compose.prod.yml logs --tail=100 frontend
```

## Restore

Wenn ein Deploy oder Import schiefgeht:

```bash
cd /srv/open-flair-shiftplan
docker compose -f docker-compose.prod.yml down
cp data/sql_app.db.backup-YYYYMMDD-HHMMSS data/sql_app.db
cp .env.backup-YYYYMMDD-HHMMSS .env
docker compose -f docker-compose.prod.yml up -d
```

Danach kurz pruefen:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100
```

## Nach dem Event

- `data/sql_app.db` archivieren oder loeschen
- `.env` und aktive Zugangscodes nicht weiterverwenden
- ggf. einen finalen XLSX-Export fuer die Dokumentation sichern
