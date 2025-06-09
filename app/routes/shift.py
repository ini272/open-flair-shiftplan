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

@router.get("/current-assignments")
def get_current_assignments(
    db: Session = Depends(get_db),
    _: bool = Depends(require_auth)
) -> Any:
    """
    Get all current shift assignments in the same format as generate-plan returns.
    """
    with tracer.start_as_current_span("get-current-assignments") as span:
        span.add_event("fetching_current_assignments")
        
        # Use existing CRUD to get all shifts
        shifts = shift_crud.get_multi(db, skip=0, limit=1000)
        
        assignments = []
        
        for shift in shifts:
            if not shift.is_active:
                continue
                
            # Track which users are assigned via groups vs individually
            users_via_groups = set()
            
            # First, process group assignments
            for group in shift.groups:
                for user in group.users:
                    if user.is_active:
                        users_via_groups.add(user.id)
                        assignments.append({
                            "shift_id": shift.id,
                            "shift_title": shift.title,
                            "user_id": user.id,
                            "username": user.username,
                            "assigned_via": "group",
                            "group_name": group.name
                        })
            
            # Then, process individual user assignments
            for user in shift.users:
                if user.is_active and user.id not in users_via_groups:
                    assignments.append({
                        "shift_id": shift.id,
                        "shift_title": shift.title,
                        "user_id": user.id,
                        "username": user.username,
                        "assigned_via": "individual",
                        "group_name": user.group.name if user.group else None
                    })
        
        span.set_attribute("assignments.count", len(assignments))
        span.add_event("current_assignments_fetched")
        
        return {
            "assignments": assignments,
            "total_assignments": len(assignments)
        }

@router.delete("/all-assignments", status_code=status.HTTP_200_OK)
def clear_all_assignments(
    db: Session = Depends(get_db),
    _: bool = Depends(require_auth)
) -> Any:
    """Clear all shift assignments (both users and groups)."""
    with tracer.start_as_current_span("clear-all-assignments") as span:
        span.add_event("clearing_all_assignments")
        
        shifts = shift_crud.get_multi(db, skip=0, limit=1000)
        
        assignments_cleared = 0
        for shift in shifts:
            assignments_cleared += len(shift.users) + len(shift.groups)
            shift.users.clear()
            shift.groups.clear()
        
        db.commit()
        span.set_attribute("assignments.cleared", assignments_cleared)
        span.add_event("all_assignments_cleared")
        
        return {
            "message": f"Cleared {assignments_cleared} assignments",
            "assignments_cleared": assignments_cleared
        }

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
    clear_existing: bool = False,
    use_groups: bool = True,  # New parameter to enable/disable group assignments
    db: Session = Depends(get_db)
) -> Any:
    """
    Generate a shift plan by assigning users and groups to shifts based on opt-outs.
    
    This endpoint:
    1. Gets all active shifts
    2. For each shift, considers both individual users and groups
    3. Assigns users/groups to shifts respecting capacity limits and avoiding conflicts
    4. Optionally clears existing assignments first
    """
    with tracer.start_as_current_span("generate-shift-plan") as span:
        span.set_attribute("clear_existing", clear_existing)
        span.set_attribute("use_groups", use_groups)
        
        # Get all active shifts
        shifts = shift_crud.get_multi(db, skip=0, limit=1000)
        active_shifts = [shift for shift in shifts if shift.is_active]
        
        # Get all active users
        from app.crud.user import user as user_crud
        from app.crud.group import group as group_crud
        
        all_users = user_crud.get_multi(db, skip=0, limit=1000)
        active_users = [user for user in all_users if user.is_active]
        
        # Get all active groups
        all_groups = group_crud.get_multi(db, skip=0, limit=1000)
        active_groups = [group for group in all_groups if group.is_active] if use_groups else []
        
        span.set_attribute("shifts.total", len(shifts))
        span.set_attribute("shifts.active", len(active_shifts))
        span.set_attribute("users.total", len(all_users))
        span.set_attribute("users.active", len(active_users))
        span.set_attribute("groups.total", len(all_groups))
        span.set_attribute("groups.active", len(active_groups))
        
        if not active_shifts:
            return {
                "message": "No active shifts found",
                "assignments": [],
                "statistics": {
                    "shifts_assigned": 0,
                    "total_assignments": 0,
                    "group_assignments": 0,
                    "individual_assignments": 0,
                    "average_assignments_per_user": 0,
                    "conflicts_avoided": 0
                }
            }
        
        if not active_users:
            return {
                "message": "No active users found",
                "assignments": [],
                "statistics": {
                    "shifts_assigned": 0,
                    "total_assignments": 0,
                    "group_assignments": 0,
                    "individual_assignments": 0,
                    "average_assignments_per_user": 0,
                    "conflicts_avoided": 0
                }
            }
        
        # Clear existing assignments if requested
        if clear_existing:
            span.add_event("clearing_existing_assignments")
            for shift in active_shifts:
                shift.users.clear()
                shift.groups.clear()
            db.commit()
            span.add_event("existing_assignments_cleared")
        
        import random
        
        # Track assignments and conflicts
        assignments = []
        group_assignments = 0
        individual_assignments = 0
        conflicts_avoided = 0
        
        # Sort shifts by start time
        sorted_shifts = sorted(active_shifts, key=lambda s: s.start_time)
        
        # Track user assignments to avoid time conflicts
        user_assignments = {user.id: [] for user in active_users}
        
        # Process each shift
        for shift in sorted_shifts:
            span.add_event("processing_shift", {
                "shift_id": shift.id,
                "title": shift.title,
                "capacity": shift.capacity
            })
            
            # Calculate current assignments
            current_user_count = len(shift.users)
            capacity = shift.capacity or 5  # Default capacity if none set
            remaining_capacity = capacity - current_user_count
            
            if remaining_capacity <= 0:
                span.add_event("shift_already_full", {"shift_id": shift.id})
                continue
            
            # Strategy: Try to assign groups first (more efficient), then individuals
            
            # 1. Try to assign groups
            if use_groups and remaining_capacity >= 2:  # Only try groups if we have space for at least 2 people
                eligible_groups = []
                
                for group in active_groups:
                    # Skip if group already assigned to this shift
                    if group in shift.groups:
                        continue
                    
                    # Get active users in this group
                    group_users = [user for user in group.users if user.is_active]
                    if not group_users:
                        continue
                    
                    # Check if group would fit in remaining capacity
                    if len(group_users) > remaining_capacity:
                        continue
                    
                    # Check if any user in the group has opted out of this shift
                    group_has_opt_out = False
                    for user in group_users:
                        if shift_crud.is_user_opted_out(db, shift_id=shift.id, user_id=user.id):
                            group_has_opt_out = True
                            break
                    
                    if group_has_opt_out:
                        continue
                    
                    # Check for time conflicts for all users in the group
                    group_has_conflict = False
                    for user in group_users:
                        for assigned_shift_id in user_assignments[user.id]:
                            assigned_shift = next((s for s in sorted_shifts if s.id == assigned_shift_id), None)
                            if assigned_shift and shifts_overlap(shift, assigned_shift):
                                group_has_conflict = True
                                conflicts_avoided += 1
                                break
                        if group_has_conflict:
                            break
                    
                    if not group_has_conflict:
                        eligible_groups.append((group, group_users))
                
                # Assign one group randomly if available
                if eligible_groups:
                    selected_group, group_users = random.choice(eligible_groups)
                    
                    # Assign the group
                    shift.groups.append(selected_group)
                    
                    # Assign all users in the group
                    for user in group_users:
                        if user not in shift.users:  # Avoid duplicates
                            shift.users.append(user)
                            user_assignments[user.id].append(shift.id)
                            
                            assignments.append({
                                "shift_id": shift.id,
                                "shift_title": shift.title,
                                "user_id": user.id,
                                "username": user.username,
                                "assigned_via": "group",
                                "group_name": selected_group.name
                            })
                    
                    group_assignments += 1
                    remaining_capacity -= len(group_users)
                    
                    span.add_event("group_assigned", {
                        "shift_id": shift.id,
                        "group_id": selected_group.id,
                        "group_name": selected_group.name,
                        "users_count": len(group_users)
                    })
            
            # 2. Fill remaining capacity with individual users
            if remaining_capacity > 0:
                already_assigned = {user.id for user in shift.users}
                eligible_users = []
                
                for user in active_users:
                    # Skip if already assigned to this shift
                    if user.id in already_assigned:
                        continue
                    
                    # Check if user has opted out of this shift
                    if shift_crud.is_user_opted_out(db, shift_id=shift.id, user_id=user.id):
                        continue
                    
                    # Check for time conflicts
                    has_conflict = False
                    for assigned_shift_id in user_assignments[user.id]:
                        assigned_shift = next((s for s in sorted_shifts if s.id == assigned_shift_id), None)
                        if assigned_shift and shifts_overlap(shift, assigned_shift):
                            has_conflict = True
                            conflicts_avoided += 1
                            break
                    
                    if not has_conflict:
                        eligible_users.append(user)
                
                # Assign individual users randomly
                assignment_count = min(len(eligible_users), remaining_capacity)
                if assignment_count > 0:
                    selected_users = random.sample(eligible_users, assignment_count)
                    
                    for user in selected_users:
                        shift.users.append(user)
                        user_assignments[user.id].append(shift.id)
                        
                        assignments.append({
                            "shift_id": shift.id,
                            "shift_title": shift.title,
                            "user_id": user.id,
                            "username": user.username,
                            "assigned_via": "individual",
                            "group_name": user.group.name if user.group else None
                        })
                    
                    individual_assignments += len(selected_users)
                    
                    span.add_event("individuals_assigned", {
                        "shift_id": shift.id,
                        "assigned_count": len(selected_users)
                    })
        
        # Commit all changes
        try:
            db.commit()
            span.add_event("assignments_committed")
        except Exception as e:
            db.rollback()
            span.add_event("commit_failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Failed to save assignments: {str(e)}")
        
        # Calculate statistics
        assigned_shifts = len([s for s in sorted_shifts if len(s.users) > 0])
        total_assignments = len(assignments)
        avg_per_user = total_assignments / len(active_users) if active_users else 0
        
        statistics = {
            "shifts_assigned": assigned_shifts,
            "total_assignments": total_assignments,
            "group_assignments": group_assignments,
            "individual_assignments": individual_assignments,
            "average_assignments_per_user": round(avg_per_user, 1),
            "conflicts_avoided": conflicts_avoided,
            "groups_used": len(set(a.get("group_name") for a in assignments if a.get("assigned_via") == "group"))
        }
        
        span.set_attribute("assignments.total", total_assignments)
        span.set_attribute("assignments.groups", group_assignments)
        span.set_attribute("assignments.individuals", individual_assignments)
        
        return {
            "message": f"Successfully generated shift plan with {total_assignments} assignments ({group_assignments} groups, {individual_assignments} individuals)",
            "assignments": assignments,
            "statistics": statistics
        }

def shifts_overlap(shift1, shift2):
    """Check if two shifts overlap in time."""
    return (shift1.start_time < shift2.end_time and 
            shift1.end_time > shift2.start_time)

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