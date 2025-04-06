from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_tracer, get_db, require_auth
from app.schemas.shift import (
    Shift, ShiftCreate, ShiftUpdate, ShiftWithAssignees,
    ShiftUserBase, ShiftGroupBase
)
from app.crud.shift import shift as shift_crud
from app.crud.user import user as user_crud
from app.crud.group import group as group_crud

# Create a router for shift-related endpoints
router = APIRouter(
    prefix="/shifts",
    tags=["shifts"],
    dependencies=[Depends(require_auth)],  # All shift endpoints require authentication
    responses={401: {"description": "Not authenticated"}},
)

# Get the tracer for this module
tracer = get_tracer()

@router.post("/", response_model=Shift, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift_in: ShiftCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new shift.
    """
    with tracer.start_as_current_span("create-shift") as span:
        span.set_attribute("shift.title", shift_in.title)
        span.set_attribute("shift.start_time", shift_in.start_time.isoformat())
        span.set_attribute("shift.end_time", shift_in.end_time.isoformat())
        
        # Create the shift
        shift = shift_crud.create(db=db, obj_in=shift_in)
        span.set_attribute("shift.id", shift.id)
        return shift

@router.get("/", response_model=List[Shift])
def read_shifts(
    skip: int = 0,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    user_id: Optional[int] = None,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get shifts with various filtering options.
    """
    with tracer.start_as_current_span("get-shifts") as span:
        span.set_attribute("query.skip", skip)
        span.set_attribute("query.limit", limit)
        
        # Filter by time range if provided
        if start_time and end_time:
            span.set_attribute("query.start_time", start_time.isoformat())
            span.set_attribute("query.end_time", end_time.isoformat())
            shifts = shift_crud.get_by_time_range(
                db, start_time=start_time, end_time=end_time, skip=skip, limit=limit
            )
        # Filter by user
        elif user_id is not None:
            span.set_attribute("query.user_id", user_id)
            shifts = shift_crud.get_by_user(db, user_id=user_id, skip=skip, limit=limit)
        # Filter by group
        elif group_id is not None:
            span.set_attribute("query.group_id", group_id)
            shifts = shift_crud.get_by_group(db, group_id=group_id, skip=skip, limit=limit)
        # No filters, get all active shifts
        else:
            shifts = shift_crud.get_multi(db, skip=skip, limit=limit)
        
        span.set_attribute("result.count", len(shifts))
        return shifts

@router.get("/{shift_id}", response_model=ShiftWithAssignees)
def read_shift(
    shift_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific shift by ID, including its assigned users and groups.
    """
    with tracer.start_as_current_span("get-shift") as span:
        span.set_attribute("shift.id", shift_id)
        
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        return shift

@router.put("/{shift_id}", response_model=Shift)
def update_shift(
    shift_id: int,
    shift_in: ShiftUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Update a shift.
    """
    with tracer.start_as_current_span("update-shift") as span:
        span.set_attribute("shift.id", shift_id)
        
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        updated_shift = shift_crud.update(db=db, db_obj=shift, obj_in=shift_in)
        return updated_shift

@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a shift.
    """
    with tracer.start_as_current_span("delete-shift") as span:
        span.set_attribute("shift.id", shift_id)
        
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        shift_crud.remove(db=db, id=shift_id)

@router.post("/users/", status_code=status.HTTP_200_OK)
def add_user_to_shift(
    assignment: ShiftUserBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Add a user to a shift.
    """
    with tracer.start_as_current_span("add-user-to-shift") as span:
        span.set_attribute("shift.id", assignment.shift_id)
        span.set_attribute("user.id", assignment.user_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=assignment.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if user exists
        user = user_crud.get(db, id=assignment.user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check capacity
        if shift.capacity is not None and shift.current_user_count >= shift.capacity:
            span.set_attribute("error", "Shift is at capacity")
            raise HTTPException(status_code=400, detail="Shift is at capacity")
        
        # Add user to shift
        updated_shift = shift_crud.add_user_to_shift(
            db, shift_id=assignment.shift_id, user_id=assignment.user_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to add user to shift")
            raise HTTPException(status_code=400, detail="Failed to add user to shift")
        
        return {"message": "User added to shift successfully"}

@router.post("/groups/", status_code=status.HTTP_200_OK)
def add_group_to_shift(
    assignment: ShiftGroupBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Add a group to a shift.
    
    This will also add all users in the group to the shift.
    """
    with tracer.start_as_current_span("add-group-to-shift") as span:
        span.set_attribute("shift.id", assignment.shift_id)
        span.set_attribute("group.id", assignment.group_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=assignment.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if group exists
        group = group_crud.get(db, id=assignment.group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Add group to shift (this will check capacity)
        updated_shift = shift_crud.add_group_to_shift(
            db, shift_id=assignment.shift_id, group_id=assignment.group_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to add group to shift (possibly due to capacity)")
            raise HTTPException(
                status_code=400, 
                detail="Failed to add group to shift. The shift may not have enough capacity for all users in the group."
            )
        
        return {"message": "Group added to shift successfully"}

@router.delete("/users/{shift_id}/{user_id}", status_code=status.HTTP_200_OK)
def remove_user_from_shift(
    shift_id: int,
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Remove a user from a shift.
    """
    with tracer.start_as_current_span("remove-user-from-shift") as span:
        span.set_attribute("shift.id", shift_id)
        span.set_attribute("user.id", user_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Remove user from shift
        updated_shift = shift_crud.remove_user_from_shift(
            db, shift_id=shift_id, user_id=user_id
        )
        
        return {"message": "User removed from shift successfully"}

@router.delete("/groups/{shift_id}/{group_id}", status_code=status.HTTP_200_OK)
def remove_group_from_shift(
    shift_id: int,
    group_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Remove a group from a shift.
    
    This removes the group association but does NOT remove individual users
    that were added as part of the group.
    """
    with tracer.start_as_current_span("remove-group-from-shift") as span:
        span.set_attribute("shift.id", shift_id)
        span.set_attribute("group.id", group_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Remove group from shift
        updated_shift = shift_crud.remove_group_from_shift(
            db, shift_id=shift_id, group_id=group_id
        )
        
        return {"message": "Group removed from shift successfully"}
