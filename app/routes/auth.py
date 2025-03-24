from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from app.dependencies import get_tracer, get_db
from app.crud.token import token as token_crud

# Create a router for authentication endpoints
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

# Get the tracer for this module
tracer = get_tracer()

class TokenCreate(BaseModel):
    """Schema for creating a new token"""
    name: str
    expires_in_days: Optional[int] = None

class TokenResponse(BaseModel):
    """Schema for token response"""
    id: int
    name: str
    token: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    
    class Config:
        orm_mode = True

@router.post("/tokens", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    token_data: TokenCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new access token.
    """
    with tracer.start_as_current_span("create-token") as span:
        span.set_attribute("token.name", token_data.name)
        if token_data.expires_in_days:
            span.set_attribute("token.expires_in_days", token_data.expires_in_days)
        
        # Create token
        token_obj = token_crud.create_token(
            db, 
            name=token_data.name,
            expires_in_days=token_data.expires_in_days
        )
        
        span.set_attribute("token.id", token_obj.id)
        return token_obj

@router.get("/tokens", response_model=List[TokenResponse])
def list_tokens(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    List all active tokens.
    """
    with tracer.start_as_current_span("get-tokens") as span:
        span.set_attribute("query.skip", skip)
        span.set_attribute("query.limit", limit)
        
        span.add_event("listing_tokens_started")
        
        # Add timing for the database operation
        import time
        db_start = time.time()
        
        span.add_event("database_query_started", {
            "operation": "get_active_tokens",
            "skip": skip,
            "limit": limit
        })
        
        tokens = token_crud.get_active_tokens(db, skip=skip, limit=limit)
        
        db_time = time.time() - db_start
        span.add_event("database_query_completed", {
            "execution_time_ms": db_time * 1000,
            "result_count": len(tokens)
        })
        
        # Add DB operation details to the span
        span.set_attribute("db.execution_time_ms", db_time * 1000)
        span.set_attribute("result.count", len(tokens))
        
        span.add_event("listing_tokens_completed")
        return tokens
@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def invalidate_token(
    token_id: int,
    db: Session = Depends(get_db)
) -> None:  # Changed return type to None
    """
    Invalidate a token.
    """
    with tracer.start_as_current_span("invalidate-token") as span:
        span.set_attribute("token.id", token_id)
        
        # Get the token from the database
        token_obj = token_crud.get(db, id=token_id)
        if token_obj is None:
            span.set_attribute("error", "Token not found")
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Invalidate the token
        token_crud.invalidate(db, token_obj=token_obj)
        # Don't return anything for 204 response

@router.get("/login/{token}")
def login_with_token(
    token: str,
    response: Response,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with an access token.
    """
    with tracer.start_as_current_span("login-with-token") as span:
        # We don't log the actual token for security reasons
        span.set_attribute("login.attempt", True)
        
        span.add_event("login_attempt_started")
        
        # Validate token
        span.add_event("validating_token")
        is_valid = token_crud.validate_token(db, token=token)
        if not is_valid:
            span.add_event("token_validation_failed")
            span.set_attribute("error", "Invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        span.add_event("token_validated_successfully")
        
        # Set a cookie with the token
        span.add_event("setting_auth_cookie")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=3600 * 24 * 30,  # 30 days
            path="/"
        )
        
        span.add_event("login_completed_successfully")
        span.set_attribute("login.success", True)
        return {"message": "Login successful"}
@router.get("/logout")
def logout(response: Response) -> Any:
    """
    Logout by clearing the token cookie.
    """
    with tracer.start_as_current_span("logout") as span:
        response.delete_cookie(key="access_token", path="/")
        span.set_attribute("logout.success", True)
        return {"message": "Logout successful"}

@router.get("/check")
def check_auth(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Any:
    """
    Check if the current user is authenticated.
    """
    with tracer.start_as_current_span("check-auth") as span:
        if not access_token:
            span.set_attribute("auth.status", "no_token")
            return {"authenticated": False}
        
        is_valid = token_crud.validate_token(db, token=access_token)
        span.set_attribute("auth.status", "valid" if is_valid else "invalid")
        return {"authenticated": is_valid}
