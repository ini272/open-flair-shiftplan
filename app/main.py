import time
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware

from app.tracing import setup_tracing
from app.database import engine, Base
from app.routes import user, auth, protected, group, shift, preferences

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI with metadata
app = FastAPI(title="FastAPI Tracing Demo", 
              description="A demo application showing tracing capabilities in FastAPI",
              version="0.1.0")

# Set up tracing
tracer = setup_tracing(app)

# Environment-specific configuration
ENV = os.getenv("NODE_ENV", "development")
IS_PRODUCTION = ENV == "production"

# Add middleware based on environment
if IS_PRODUCTION:
    # Production: Behind nginx proxy with HTTPS
    app.add_middleware(ProxyHeadersMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["weinzelt.duckdns.org"])
    
    # CORS for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://weinzelt.duckdns.org"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Development: Direct access, allow localhost
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # React app's address
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
    # Add processing time as a header to the response
    response.headers["X-Process-Time"] = str(process_time)
    print(f"Request to {request.url.path} took {process_time:.4f} seconds")
    return response

# Handle favicon.ico requests to prevent 404 errors
# @app.get("/favicon.ico", include_in_schema=False)
# async def favicon():
#     # Adjust the path to look for favicon.ico in the project root
#     current_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
#     favicon_path = os.path.join(current_dir, "favicon.ico")
#     return FileResponse(favicon_path)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}