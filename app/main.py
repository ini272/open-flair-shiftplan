import time
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from app.tracing import setup_tracing
from app.database import engine, Base
from app.routes import user, auth, protected  # Updated import

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI with metadata
app = FastAPI(title="FastAPI Tracing Demo", 
              description="A demo application showing tracing capabilities in FastAPI",
              version="0.1.0")

# Set up tracing
tracer = setup_tracing(app)

# Include routers
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(protected.router)

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
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Adjust the path to look for favicon.ico in the project root
    current_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    favicon_path = os.path.join(current_dir, "favicon.ico")
    return FileResponse(favicon_path)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}