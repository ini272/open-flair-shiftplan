from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_tracer
from app.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.crud.user import user as user_crud

# Create a router for user-related endpoints
router = APIRouter(
    prefix="/users",  # All routes will be prefixed with /users
    tags=["users"],   # For API documentation grouping
    responses={404: {"description": "Not found"}},  # Default responses
)

# Get the tracer for this module
tracer = get_tracer()

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Create a new user.
    """
    with tracer.start_as_current_span("create-user") as span:
        # Add user information to the span for tracing
        span.set_attribute("user.email", user_in.email)
        span.set_attribute("user.username", user_in.username)
        
        # Add event: Starting user creation process
        span.add_event("starting_user_creation")
        
        # Check if email is already registered
        span.add_event("checking_email_uniqueness")
        user_by_email = user_crud.get_by_email(db, email=user_in.email)
        if user_by_email:
            span.add_event("email_already_exists", {
                "email": user_in.email
            })
            span.set_attribute("error", "Email already registered")
            raise HTTPException(
                status_code=400, detail="Email already registered"
            )
        
        # Check if username is already taken    
        span.add_event("checking_username_uniqueness")
        user_by_username = user_crud.get_by_username(db, username=user_in.username)
        if user_by_username:
            span.add_event("username_already_exists", {
                "username": user_in.username
            })
            span.set_attribute("error", "Username already taken")
            raise HTTPException(
                status_code=400, detail="Username already taken"
            )
        
        # Create the user
        span.add_event("creating_user_in_database")
        user = user_crud.create(db=db, obj_in=user_in)
        
        span.add_event("user_created_successfully", {
            "user_id": user.id
        })
        
        return user
@router.get("/", response_model=List[User])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a list of users with pagination.
    """
    with tracer.start_as_current_span("get-users") as span:
        # Add query parameters to the span for tracing
        span.set_attribute("query.skip", skip)
        span.set_attribute("query.limit", limit)
        
        # Get users from the database
        users = user_crud.get_multi(db, skip=skip, limit=limit)
        
        # Add result count to the span
        span.set_attribute("result.count", len(users))
        return users

@router.get("/{user_id}", response_model=User)
def read_user(user_id: int, db: Session = Depends(get_db)) -> Any:
    """
    Get a specific user by ID.
    """
    with tracer.start_as_current_span("get-user") as span:
        # Add user ID to the span for tracing
        span.set_attribute("user.id", user_id)
        
        # Get the user from the database
        db_user = user_crud.get(db, id=user_id)
        
        # Return 404 if user not found
        if db_user is None:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        return db_user

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int, 
    user_in: UserUpdate, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Update a user's information.
    """
    with tracer.start_as_current_span("update-user") as span:
        # Add user ID to the span for tracing
        span.set_attribute("user.id", user_id)
        
        # Get the user from the database
        db_user = user_crud.get(db, id=user_id)
        if db_user is None:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update the user
        return user_crud.update(db=db, db_obj=db_user, obj_in=user_in)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:  # Change return type to None
    """
    Delete a user.
    """
    with tracer.start_as_current_span("delete-user") as span:
        # Add user ID to the span for tracing
        span.set_attribute("user.id", user_id)
        
        # Get the user from the database
        db_user = user_crud.get(db, id=user_id)
        if db_user is None:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete the user
        user_crud.remove(db=db, id=user_id)
        # Don't return anything
