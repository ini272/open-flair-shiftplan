# Open Flair Festival Shift Scheduler

## Project Overview

A custom web application for coordinating volunteer shifts at Open Flair Festival 2026, currently being prepared for a coordinator-facing showcase and possible home-server pilot.

The goal is practical: let members mark which shifts they cannot work before arrival, then let the coordinator generate a first-pass plan and adjust it manually. If the process does not land, the existing paper workflow can still be used as fallback.

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM and SQLite
- **Frontend**: React with Material UI and German localization
- **Deployment target**: Docker Compose on a home server or small VPS
- **Database**: SQLite persisted in `./data` for production compose

## Key Features

- Event-code access flow without member passwords
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
- Access-code login replaced token links.
- Coordinator-only backend authorization protects admin-like operations.
- The old external tracing experiment was removed from active dependencies.

## Quick Start

```bash
# Development
docker compose up

# Production-style local/home-server run
cp .env.example .env
# edit EVENT_CODE, COORDINATOR_CODE, SESSION_SECRET_KEY
docker compose -f docker-compose.prod.yml up --build

# Backend tests without Docker
uv venv
uv pip install -r requirements.txt
uv run python -m pytest
```

## Shift Data

Create production-shaped shifts from the YAML schedule:

```bash
python scripts/create_production_shifts.py --access-code YOUR_COORDINATOR_CODE
```

The default schedule is stored in `scripts/festival_schedule.yaml`.

## Known Limitations

- The event code is a lightweight shared barrier, not strong personal authentication.
- No database migration system yet.
- Generated plans are randomized and should be reviewed by the coordinator.
- The 2026 shift times are still starter/demo data until confirmed by the coordinator.
