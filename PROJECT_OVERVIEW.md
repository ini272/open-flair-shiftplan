# Open Flair Festival Shift Scheduler

## Project Overview

A custom web application for coordinating volunteer shifts at Open Flair Festival 2026, currently being prepared for a coordinator-facing showcase and possible home-server pilot.

The goal is practical: let members mark which shifts they cannot work before arrival, then let the coordinator generate a first-pass plan and adjust it manually. If the process does not land, the existing paper workflow can still be used as fallback.

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM and SQLite
- **Frontend**: React with Material UI and German localization
- **Deployment target**: Docker Compose on a home server or local LAN
- **Database**: SQLite persisted in `./data` for production compose

## Key Features

- Token-based access flow without member passwords
- User onboarding for solo workers or small groups
- Shift availability opt-outs by individual or group
- Fast day/location selection for Weinzelt and Bierwagen
- Coordinator dashboard with assignment statistics
- First-pass shift-plan generation plus manual add/remove controls

## Core Models

```text
User (email, username, is_coordinator, is_active, group_id)
Group (name, is_active)
Shift (title, description, start_time, end_time, capacity, is_active)
AccessToken (token, name, expires_at, is_active, is_coordinator_token)
```

Users can belong to one group. Shifts can have assigned users and groups, and opt-outs are tracked separately for users and groups.

## Festival Context

- **Dates**: 5-9 August 2026
- **Location**: Eschwege, Germany
- **Shift locations**: Weinzelt and Bierwagen by default
- **Scale**: Small volunteer team, coordinator-operated

## Current Status

- Core planning flow is implemented.
- Docker-based local/home-server deployment is the intended path.
- The old public DNS, certificate, and cloud-server assumptions were removed from active config.
- The old external tracing experiment was removed from active dependencies.
- The app still needs authorization hardening before real participant data is exposed beyond a trusted LAN.

## Quick Start

```bash
# Development
docker compose up

# Production-style local/home-server run
docker compose -f docker-compose.prod.yml up --build

# Backend tests without Docker
uv run --with-requirements requirements.txt pytest tests
```

## Shift Data

Create production-shaped shifts from the YAML schedule:

```bash
python scripts/create_production_shifts.py --token YOUR_ACCESS_TOKEN
```

The default schedule is stored in `scripts/festival_schedule.yaml`.

## Known Limitations

- Authorization is too permissive for public internet exposure.
- No database migration system yet.
- Generated plans are randomized and should be reviewed by the coordinator.
- The 2026 shift times are still starter/demo data until confirmed by the coordinator.
