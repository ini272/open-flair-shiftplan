# Open Flair Festival Shift Scheduler

## Project Overview
A custom web application for managing volunteer shifts at the Open Flair festival (August 2-11, 2025). Built for a small team of coordinators and volunteers, deployed on Google Cloud for one-time use.

## Architecture
- **Backend**: FastAPI with SQLAlchemy ORM, SQLite database
- **Frontend**: React with Material-UI, German localization
- **Deployment**: Docker Compose on Google Cloud
- **Observability**: Jaeger tracing integration

## Key Features
- Token-based authentication with role-based access (coordinators vs regular users)
- Manual shift creation and assignment by coordinators
- User preference system and opt-out functionality
- Responsive web interface (primarily PC usage)
- German language support

## Core Models & Relationships
```
User (email, username, is_coordinator, is_active)
├── Many-to-Many → Shifts (via shift_users association)
├── Many-to-Many → Groups (via user_groups association)
└── One-to-Many → ShiftPreferences

Shift (name, description, start_time, end_time, location, max_users)
├── Many-to-Many → Users
└── Many-to-Many → Groups

Group (name, description, is_active)
└── Many-to-Many → Users

AccessToken (token, name, user_id, expires_at)
```

## Festival Context
- **Dates**: August 2-11, 2025
- **Locations**: Weinzelt, Bierwagen (expandable)
- **Workflow**: Coordinators manually create shifts, users can express preferences/opt-outs
- **Scale**: Small team, one-time event

## Technical Stack
### Backend (`/app`)
- FastAPI with automatic OpenAPI docs
- SQLAlchemy models with association tables
- Generic CRUD base classes
- Pydantic schemas for validation
- Token-based auth system

### Frontend (`/frontend`)
- React 18 with Material-UI v5
- Axios for API communication
- React Router for navigation
- Custom theming with Open Flair branding
- Components: Login, Dashboard, CoordinatorView, ShiftGrid

### Key Files Structure
```
app/
├── main.py                 # FastAPI app setup
├── database.py            # SQLAlchemy config
├── models/               # SQLAlchemy models
├── schemas/              # Pydantic schemas
├── crud/                 # Database operations
├── routes/               # API endpoints
└── dependencies.py       # Auth dependencies

frontend/src/
├── components/           # React components
├── pages/               # Page components
├── services/api.js      # API client
└── utils/translations.js # German translations
```

## Deployment
- **Development**: `docker-compose.yml` with live reload
- **Production**: `docker-compose.prod.yml` with Nginx, HTTPS, persistent SQLite
- **Database**: SQLite with persistent volume mounting
- **SSL**: Let's Encrypt certificates (manual renewal)

## Current Status
- ✅ Core functionality implemented
- ✅ Deployed on Google Cloud
- ✅ Basic testing suite with pytest
- 🔄 German translations may need completion
- 🔄 Festival shifts created manually by coordinators

## Setup Script
`scripts/create_festival_shifts.py` - Creates base shifts for festival dates and locations

## Testing
Comprehensive pytest suite covering:
- Authentication flows
- User/group management
- Shift operations
- Preferences and opt-outs
- Protected routes

## Known Limitations
- SQLite database (sufficient for scale)
- No automatic shift assignment logic
- Manual certificate renewal required
- No database migration system
- Token refresh not implemented

## Quick Start Commands
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up

# Run tests
pytest tests/
```

## API Endpoints
- `/auth/*` - Authentication (login, logout, token management)
- `/users/*` - User CRUD operations
- `/groups/*` - Group management
- `/shifts/*` - Shift operations
- `/protected/*` - Authenticated routes

## Environment Variables
- `DATABASE_URL` - SQLite database path
- `NODE_ENV` - Environment mode
- Jaeger tracing configuration

This is a purpose-built, time-limited application optimized for the specific needs of Open Flair festival volunteer coordination.