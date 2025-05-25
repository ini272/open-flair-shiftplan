from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_tracer, get_db, require_auth
from app.schemas.shift import (
    Shift, ShiftCreate, ShiftUpdate, ShiftWithAssignees,
    ShiftUserBase, ShiftGroupBase
)
from app.schemas.user import User
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
        
        # Add event: Starting shift creation process
        span.add_event("starting_shift_creation")
        
        # Create the shift
        span.add_event("creating_shift_in_database")
        shift = shift_crud.create(db=db, obj_in=shift_in)
        
        span.add_event("shift_created_successfully", {
            "shift_id": shift.id,
            "capacity": shift.capacity
        })
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
        
        span.add_event("starting_user_shift_assignment")
        
        # Check if shift exists
        span.add_event("checking_shift_exists")
        shift = shift_crud.get(db, id=assignment.shift_id)
        if not shift:
            span.add_event("shift_not_found", {"shift_id": assignment.shift_id})
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if user exists
        span.add_event("checking_user_exists")
        user = user_crud.get(db, id=assignment.user_id)
        if not user:
            span.add_event("user_not_found", {"user_id": assignment.user_id})
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check capacity
        span.add_event("checking_shift_capacity", {
            "current_users": shift.current_user_count,
            "capacity": shift.capacity
        })
        if shift.capacity is not None and shift.current_user_count >= shift.capacity:
            span.add_event("shift_at_capacity", {
                "shift_id": assignment.shift_id,
                "capacity": shift.capacity
            })
            span.set_attribute("error", "Shift is at capacity")
            raise HTTPException(status_code=400, detail="Shift is at capacity")
        
        # Add user to shift
        span.add_event("assigning_user_to_shift")
        updated_shift = shift_crud.add_user_to_shift(
            db, shift_id=assignment.shift_id, user_id=assignment.user_id
        )
        
        if not updated_shift:
            span.add_event("assignment_failed")
            span.set_attribute("error", "Failed to add user to shift")
            raise HTTPException(status_code=400, detail="Failed to add user to shift")
        
        span.add_event("user_assigned_successfully", {
            "user_id": assignment.user_id,
            "shift_id": assignment.shift_id,
            "new_user_count": updated_shift.current_user_count
        })
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
        
        span.add_event("starting_group_shift_assignment")
        
        # Check if shift exists
        span.add_event("checking_shift_exists")
        shift = shift_crud.get(db, id=assignment.shift_id)
        if not shift:
            span.add_event("shift_not_found", {"shift_id": assignment.shift_id})
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if group exists
        span.add_event("checking_group_exists")
        group = group_crud.get(db, id=assignment.group_id)
        if not group:
            span.add_event("group_not_found", {"group_id": assignment.group_id})
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Add group to shift (this will check capacity)
        span.add_event("assigning_group_to_shift", {
            "group_user_count": len(group.users),
            "shift_capacity": shift.capacity
        })
        updated_shift = shift_crud.add_group_to_shift(
            db, shift_id=assignment.shift_id, group_id=assignment.group_id
        )
        
        if not updated_shift:
            span.add_event("assignment_failed_capacity_exceeded")
            span.set_attribute("error", "Failed to add group to shift (possibly due to capacity)")
            raise HTTPException(
                status_code=400, 
                detail="Failed to add group to shift. The shift may not have enough capacity for all users in the group."
            )
        
        span.add_event("group_assigned_successfully", {
            "group_id": assignment.group_id,
            "shift_id": assignment.shift_id,
            "new_user_count": updated_shift.current_user_count
        })
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

@router.post("/generate-plan", status_code=status.HTTP_200_OK)
def generate_shift_plan(
    db: Session = Depends(get_db)
) -> Any:
    """
    Generate a shift plan by randomly assigning users to shifts based on their preferences.
    
    This endpoint:
    1. Gets all shifts for the festival period (Aug 6-10, 2025)
    2. For each shift, finds users who have opted in (set preference to can_work=True)
    3. Randomly assigns users to shifts respecting capacity limits
    """
    with tracer.start_as_current_span("generate-shift-plan") as span:
        # Define festival date range (August 6-10, 2025)
        start_time = datetime(2025, 8, 6, 0, 0, 0)
        end_time = datetime(2025, 8, 11, 0, 0, 0)  # Day after festival ends
        
        span.set_attribute("festival.start_time", start_time.isoformat())
        span.set_attribute("festival.end_time", end_time.isoformat())
        
        # Get all shifts for the festival period
        shifts = shift_crud.get_by_time_range(
            db, start_time=start_time, end_time=end_time
        )
        
        span.set_attribute("shifts.count", len(shifts))
        span.add_event("fetched_festival_shifts", {"count": len(shifts)})
        
        # Import needed for randomization
        import random
        
        # Import preference CRUD
        from app.crud.preferences import preference as preference_crud
        
        # Track assignments for reporting
        assignments = []
        
        # Process each shift
        for shift in shifts:
            span.add_event("processing_shift", {"shift_id": shift.id, "title": shift.title})
            
            # Get all users who have opted in for this shift
            eligible_user_ids = preference_crud.get_users_for_shift(
                db, shift_id=shift.id, can_work=True
            )
            
            # Get user objects
            from app.crud.user import user as user_crud
            eligible_users = [user_crud.get(db, id=user_id) for user_id in eligible_user_ids]
            eligible_users = [user for user in eligible_users if user is not None]
            
            # Filter out users already assigned to this shift
            eligible_users = [user for user in eligible_users if user not in shift.users]
            
            span.add_event("eligible_users", {"count": len(eligible_users)})
            
            # Calculate how many slots are available
            available_slots = shift.capacity - len(shift.users) if shift.capacity else len(eligible_users)
            
            # If no slots available or no eligible users, skip this shift
            if available_slots <= 0 or not eligible_users:
                span.add_event("skipping_shift", {
                    "reason": "no_slots" if available_slots <= 0 else "no_eligible_users"
                })
                continue
            
            # Randomly select users to assign
            selected_users = random.sample(eligible_users, min(available_slots, len(eligible_users)))
            
            span.add_event("selected_users", {"count": len(selected_users)})
            
            # Assign selected users to the shift
            for user in selected_users:
                shift_crud.add_user_to_shift(db, shift_id=shift.id, user_id=user.id)
                assignments.append({
                    "shift_id": shift.id,
                    "shift_title": shift.title,
                    "user_id": user.id,
                    "username": user.username
                })
            
            span.add_event("users_assigned", {"count": len(selected_users)})
        
        span.set_attribute("assignments.count", len(assignments))
        return {"message": f"Successfully generated shift plan with {len(assignments)} assignments", "assignments": assignments}

@router.post("/user-opt-out", status_code=status.HTTP_200_OK)
def opt_out_user(
    opt_out: ShiftUserBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Opt a user out of a shift.
    """
    with tracer.start_as_current_span("opt-out-user") as span:
        span.set_attribute("shift.id", opt_out.shift_id)
        span.set_attribute("user.id", opt_out.user_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=opt_out.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if user exists
        user = user_crud.get(db, id=opt_out.user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is in a group - if so, they can't have individual opt-outs
        if user.group_id is not None:
            span.set_attribute("error", "User is in a group")
            raise HTTPException(
                status_code=400, 
                detail="Users in groups cannot have individual opt-outs. Please opt out the entire group."
            )
        
        # Opt the user out
        updated_shift = shift_crud.opt_out_user(
            db, shift_id=opt_out.shift_id, user_id=opt_out.user_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to opt out user")
            raise HTTPException(status_code=400, detail="Failed to opt out user")
        
        return {"message": f"User {opt_out.user_id} opted out of shift {opt_out.shift_id}"}

@router.post("/user-opt-in", status_code=status.HTTP_200_OK)
def opt_in_user(
    opt_in: ShiftUserBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Opt a user back into a shift.
    """
    with tracer.start_as_current_span("opt-in-user") as span:
        span.set_attribute("shift.id", opt_in.shift_id)
        span.set_attribute("user.id", opt_in.user_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=opt_in.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if user exists
        user = user_crud.get(db, id=opt_in.user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is in a group - if so, they can't have individual opt-outs
        if user.group_id is not None:
            span.set_attribute("error", "User is in a group")
            raise HTTPException(
                status_code=400, 
                detail="Users in groups cannot have individual opt-outs. Please opt in the entire group."
            )
        
        # Opt the user in
        updated_shift = shift_crud.opt_in_user(
            db, shift_id=opt_in.shift_id, user_id=opt_in.user_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to opt in user")
            raise HTTPException(status_code=400, detail="Failed to opt in user")
        
        return {"message": f"User {opt_in.user_id} opted into shift {opt_in.shift_id}"}

@router.post("/group-opt-out", status_code=status.HTTP_200_OK)
def opt_out_group(
    opt_out: ShiftGroupBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Opt a group out of a shift.
    """
    with tracer.start_as_current_span("opt-out-group") as span:
        span.set_attribute("shift.id", opt_out.shift_id)
        span.set_attribute("group.id", opt_out.group_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=opt_out.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if group exists
        group = group_crud.get(db, id=opt_out.group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Opt the group out
        updated_shift = shift_crud.opt_out_group(
            db, shift_id=opt_out.shift_id, group_id=opt_out.group_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to opt out group")
            raise HTTPException(status_code=400, detail="Failed to opt out group")
        
        return {"message": f"Group {opt_out.group_id} opted out of shift {opt_out.shift_id}"}

@router.post("/group-opt-in", status_code=status.HTTP_200_OK)
def opt_in_group(
    opt_in: ShiftGroupBase,
    db: Session = Depends(get_db)
) -> Any:
    """
    Opt a group back into a shift.
    """
    with tracer.start_as_current_span("opt-in-group") as span:
        span.set_attribute("shift.id", opt_in.shift_id)
        span.set_attribute("group.id", opt_in.group_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=opt_in.shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if group exists
        group = group_crud.get(db, id=opt_in.group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Opt the group in
        updated_shift = shift_crud.opt_in_group(
            db, shift_id=opt_in.shift_id, group_id=opt_in.group_id
        )
        
        if not updated_shift:
            span.set_attribute("error", "Failed to opt in group")
            raise HTTPException(status_code=400, detail="Failed to opt in group")
        
        return {"message": f"Group {opt_in.group_id} opted into shift {opt_in.shift_id}"}

@router.get("/opt-out-status/{shift_id}/{user_id}", status_code=status.HTTP_200_OK)
def check_opt_out_status(
    shift_id: int,
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Check if a user is opted out of a shift.
    """
    with tracer.start_as_current_span("check-opt-out-status") as span:
        span.set_attribute("shift.id", shift_id)
        span.set_attribute("user.id", user_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Check if user exists
        user = user_crud.get(db, id=user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is opted out
        is_opted_out = shift_crud.is_user_opted_out(
            db, shift_id=shift_id, user_id=user_id
        )
        
        return {"is_opted_out": is_opted_out}

@router.get("/user-opt-outs/{user_id}", response_model=List[Shift])
def get_user_opt_outs(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all shifts a user is opted out of.
    """
    with tracer.start_as_current_span("get-user-opt-outs") as span:
        span.set_attribute("user.id", user_id)
        
        # Check if user exists
        user = user_crud.get(db, id=user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get opt-outs
        opt_outs = shift_crud.get_user_opt_outs(db, user_id=user_id)
        
        return opt_outs

@router.get("/group-opt-outs/{group_id}", response_model=List[Shift])
def get_group_opt_outs(
    group_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all shifts a group is opted out of.
    """
    with tracer.start_as_current_span("get-group-opt-outs") as span:
        span.set_attribute("group.id", group_id)
        
        # Check if group exists
        group = group_crud.get(db, id=group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get opt-outs
        opt_outs = shift_crud.get_group_opt_outs(db, group_id=group_id)
        
        return opt_outs

@router.get("/available-users/{shift_id}", response_model=List[User])
def get_available_users(
    shift_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all users available for a shift (not opted out).
    """
    with tracer.start_as_current_span("get-available-users") as span:
        span.set_attribute("shift.id", shift_id)
        
        # Check if shift exists
        shift = shift_crud.get(db, id=shift_id)
        if not shift:
            span.set_attribute("error", "Shift not found")
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Get available users
        available_users = shift_crud.get_available_users(db, shift_id=shift_id)
        
        return available_users