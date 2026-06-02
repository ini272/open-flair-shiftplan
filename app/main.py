import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.tracing import setup_tracing
from app.database import engine, Base
from app.routes import user, auth, protected, group, shift, preferences

def ensure_location_preference_columns() -> None:
    """Backfill lightweight schema changes for existing local SQLite databases."""
    inspector = inspect(engine)

    existing_tables = set(inspector.get_table_names())
    required_columns = {
        "users": "location_preference",
        "groups": "location_preference",
    }

    with engine.begin() as connection:
        for table_name, column_name in required_columns.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN location_preference VARCHAR DEFAULT 'both'"
                    )
                )

            connection.execute(
                text(
                    f"UPDATE {table_name} "
                    "SET location_preference = 'both' "
                    "WHERE location_preference IS NULL"
                )
            )


# Create database tables and backfill simple additive schema updates.
Base.metadata.create_all(bind=engine)
ensure_location_preference_columns()

# Initialize FastAPI with metadata
app = FastAPI(
    title="Open Flair Shift Planner",
    description="Volunteer shift planning for Open Flair festival coordination.",
    version="0.2.0",
)

# Set up tracing
tracer = setup_tracing(app)

# Environment-specific configuration
ENV = os.getenv("NODE_ENV", "development")
IS_PRODUCTION = ENV == "production"

# Add CORS only when the frontend is served from a different origin.
configured_origins = os.getenv("CORS_ORIGINS")
if configured_origins:
    cors_origins = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
elif IS_PRODUCTION:
    cors_origins = []
else:
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(group.router)
app.include_router(shift.router)
app.include_router(preferences.router)

# Middleware to measure request processing time
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
    print(f"Request to {request.url.path} took {process_time:.4f} seconds")
    return response

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Open Flair Shift Planner API"}
