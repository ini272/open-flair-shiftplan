import time
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from app.tracing import setup_tracing

# Initialize FastAPI with metadata
app = FastAPI(title="FastAPI Tracing Demo", 
              description="A demo application showing tracing capabilities in FastAPI",
              version="0.1.0")

# Set up tracing
tracer = setup_tracing(app)

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

# Item endpoint with path parameter
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # Create a custom span for this operation
    # This allows us to track specific parts of our code execution
    with tracer.start_as_current_span("processing-item") as span:
        # Add some attributes to the span
        # These will be visible in the Jaeger UI and can be used for filtering
        span.set_attribute("item.id", item_id)
        
        # Simulate some processing time
        # In a real app, this might be a database query or external API call
        time.sleep(0.1)
        
        return {"item_id": item_id, "name": f"Item {item_id}"}
