from typing import Any
from fastapi import APIRouter, Depends

from app.dependencies import get_tracer, require_auth

# Create a router for protected endpoints
router = APIRouter(
    prefix="/protected",
    tags=["protected"],
    dependencies=[Depends(require_auth)],  # All routes in this router require authentication
    responses={401: {"description": "Not authenticated"}},
)

# Get the tracer for this module
tracer = get_tracer()

@router.get("/")
def protected_route() -> Any:
    """
    A protected route that requires authentication.
    """
    with tracer.start_as_current_span("protected-route") as span:
        return {"message": "This is a protected route"}

@router.get("/admin")
def admin_route() -> Any:
    """
    Another protected route.
    """
    with tracer.start_as_current_span("admin-route") as span:
        return {"message": "This is an admin route"}
