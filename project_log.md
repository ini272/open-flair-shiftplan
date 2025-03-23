# FastAPI Tracing Project Log

## 2025-03-23

### Initial Setup
- Basic FastAPI app with `/` and `/items/{item_id}` endpoints
- Added `time.sleep(0.1)` to simulate processing time

### Request Timing
- Added HTTP middleware to measure request duration
- Added `X-Process-Time` response header
- Fixed favicon 404 with `FileResponse`

### OpenTelemetry Integration
- Added basic OTel setup with console exporter
- Created custom span for item processing
- Added item ID as span attribute

### Dockerization
- Containerized app with simple Dockerfile
- Added docker-compose with FastAPI + Jaeger
- Fixed networking between containers

### Jaeger Visualization
- Switched to Jaeger v2 image
- Configured proper service name in traces
- Verified trace data in Jaeger UI

### Dev Experience
- Added volume mounts for live code changes
- Enabled `--reload` flag in Uvicorn
- No more container rebuilds for code changes

### Tech Stack
- FastAPI + Uvicorn
- OpenTelemetry SDK
- Jaeger for trace visualization
- Docker + Docker Compose
