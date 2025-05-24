from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_tracer, get_db, require_auth
from app.crud.preferences import preference as preference_crud
from app.schemas.preferences import PreferenceCreate, PreferenceResponse

# Create a router for preference-related endpoints
router = APIRouter(
    prefix="/preferences",
    tags=["preferences"],
    dependencies=[Depends(require_auth)],  # All preference endpoints require authentication
    responses={401: {"description": "Not authenticated"}},
)

# Get the tracer for this module
tracer = get_tracer()

@router.post("/", response_model=PreferenceResponse)
def set_preference(
    preference_in: PreferenceCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Set a user's preference for a shift.
    """
    with tracer.start_as_current_span("set-preference") as span:
        span.set_attribute("user.id", preference_in.user_id)
        span.set_attribute("shift.id", preference_in.shift_id)
        span.set_attribute("can_work", preference_in.can_work)
        
        success = preference_crud.set_preference(
            db, 
            user_id=preference_in.user_id,
            shift_id=preference_in.shift_id,
            can_work=preference_in.can_work
        )
        
        if not success:
            span.set_attribute("error", "Failed to set preference")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to set preference. User or shift may not exist."
            )
        
        return {
            "user_id": preference_in.user_id,
            "shift_id": preference_in.shift_id,
            "can_work": preference_in.can_work
        }

@router.get("/users/{user_id}", response_model=List[PreferenceResponse])
def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all preferences for a user.
    """
    with tracer.start_as_current_span("get-user-preferences") as span:
        span.set_attribute("user.id", user_id)
        
        preferences = preference_crud.get_preferences(db, user_id=user_id)
        
        span.set_attribute("preferences.count", len(preferences))
        return preferences

@router.get("/shifts/{shift_id}", response_model=List[int])
def get_users_for_shift(
    shift_id: int,
    can_work: bool = True,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all users who can/cannot work a shift.
    """
    with tracer.start_as_current_span("get-users-for-shift") as span:
        span.set_attribute("shift.id", shift_id)
        span.set_attribute("can_work", can_work)
        
        user_ids = preference_crud.get_users_for_shift(
            db, shift_id=shift_id, can_work=can_work
        )
        
        span.set_attribute("users.count", len(user_ids))
        return user_ids