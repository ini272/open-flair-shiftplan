from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.crud.token import token as token_crud

def get_tracer():
    """
    Returns the global tracer instance.
    This will be useful when we need the tracer in other modules.
    """
    from opentelemetry import trace
    return trace.get_tracer(__name__)

def require_auth(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Dependency to require authentication.
    Raises an exception if the user is not authenticated.
    
    Args:
        access_token: The token cookie from the request
        db: Database session
        
    Returns:
        True if authenticated
        
    Raises:
        HTTPException: If not authenticated
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    is_valid = token_crud.validate_token(db, token=access_token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return True
