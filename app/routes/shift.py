from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import random
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import (
    ensure_group_member_or_coordinator,
    ensure_self_or_coordinator,
    get_tracer,
    get_db,
    require_auth,
    require_coordinator,
)
from app.schemas.shift import (
    Shift, ShiftCreate, ShiftUpdate, ShiftWithAssignees,
    ShiftUserBase, ShiftGroupBase, ShiftXlsxExportRequest
)
from app.schemas.user import User
from app.crud.shift import shift as shift_crud
from app.crud.user import user as user_crud
from app.crud.group import group as group_crud
from app.security import AuthSession
from app.xlsx_export import build_shift_plan_xlsx

# Create a router for shift-related endpoints
router = APIRouter(
    prefix="/shifts",
    tags=["shifts"],
    dependencies=[Depends(require_auth)],  # All shift endpoints require authentication
    responses={401: {"description": "Not authenticated"}},
)

# Get the tracer for this module
tracer = get_tracer()

PLANNER_RANDOMIZATION_SCORE_WINDOW = 3.0


def get_planner_day_start(shift) -> datetime:
    """
    Return the festival-planning day a shift belongs to.

    Early-morning slots after midnight still belong to the previous festival night.
    """
    shift_start = shift.start_time
    if shift_start.hour < 6:
        return shift_start - timedelta(days=1)
    return shift_start


def get_shift_day_key(shift) -> str:
    """Return a stable day key for a shift."""
    return get_planner_day_start(shift).date().isoformat()


def get_shift_slot_signature(shift) -> Tuple[int, int, int, int]:
    """Return a time-slot signature so parallel location shifts share the same slot index."""
    return (
        shift.start_time.hour,
        shift.start_time.minute,
        shift.end_time.hour,
        shift.end_time.minute,
    )


def get_shift_slot_key(shift) -> Tuple[str, Tuple[int, int, int, int]]:
    """Return a slot key that is stable per day and timeslot."""
    return (get_shift_day_key(shift), get_shift_slot_signature(shift))


def get_shift_location_key(shift) -> str:
    """Map a shift title to its location key."""
    normalized_title = shift.title.lower()
    if "weinzelt" in normalized_title:
        return "weinzelt"
    if "bierwagen" in normalized_title:
        return "bierwagen"
    return "both"


def shift_starts_in_evening_window(shift) -> bool:
    """Return True for shifts that start at or after 20:00 or after midnight."""
    return (
        (shift.start_time.hour, shift.start_time.minute) >= (20, 0)
        or shift.start_time.hour < 6
    )


def is_under_16_restricted_shift(shift) -> bool:
    """Users under 16 may not work shifts from 20:00 onward."""
    return shift_starts_in_evening_window(shift)


def is_priority_evening_shift(shift) -> bool:
    """
    Thursday/Friday/Saturday evening shifts include the night after midnight.

    This treats 00:00-02:00 slots as part of the previous festival night.
    """
    planner_day = get_planner_day_start(shift)
    return planner_day.weekday() in (3, 4, 5) and shift_starts_in_evening_window(shift)


def get_max_consecutive_slots(slot_positions: List[int]) -> int:
    """Return the longest chain of consecutive slot indices."""
    if not slot_positions:
        return 0

    ordered_positions = sorted(slot_positions)
    max_streak = 1
    current_streak = 1

    for previous, current in zip(ordered_positions, ordered_positions[1:]):
        if current == previous + 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    return max_streak


def has_single_slot_gap(slot_positions: List[int]) -> bool:
    """Return True if there is exactly one empty slot between two assignments."""
    ordered_positions = sorted(slot_positions)
    return any(
        current == previous + 2
        for previous, current in zip(ordered_positions, ordered_positions[1:])
    )

@router.post("/", response_model=Shift, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift_in: ShiftCreate,
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
    _: AuthSession = Depends(require_coordinator),
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
                    if user.is_active and not user.is_coordinator:
                        users_via_groups.add(user.id)
                        assignments.append({
                            "shift_id": shift.id,
                            "shift_title": shift.title,
                            "user_id": user.id,
                            "username": user.username,
                            "assigned_via": "group",
                            "group_name": group.name,
                        })
            
            # Then, process individual user assignments
            for user in shift.users:
                if user.is_active and not user.is_coordinator and user.id not in users_via_groups:
                    assignments.append({
                        "shift_id": shift.id,
                        "shift_title": shift.title,
                        "user_id": user.id,
                        "username": user.username,
                        "assigned_via": "individual",
                        "group_name": user.group.name if user.group else None,
                    })
        
        span.set_attribute("assignments.count", len(assignments))
        span.add_event("current_assignments_fetched")
        
        return {
            "assignments": assignments,
            "total_assignments": len(assignments),
            "planner": None,
        }

@router.delete("/all-assignments", status_code=status.HTTP_200_OK)
def clear_all_assignments(
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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


@router.post("/export/xlsx")
def export_shift_plan_xlsx(
    export_request: Optional[ShiftXlsxExportRequest] = None,
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
) -> Response:
    """Export the coordinator plan as an XLSX workbook with one sheet per day."""
    with tracer.start_as_current_span("export-shift-plan-xlsx") as span:
        shifts = shift_crud.get_multi(db, skip=0, limit=1000)
        assignments = export_request.assignments if export_request else None

        span.set_attribute("shifts.count", len(shifts))
        span.set_attribute("export.assignments_override", assignments is not None)
        if assignments is not None:
            span.set_attribute("export.assignments_count", len(assignments))

        workbook_bytes = build_shift_plan_xlsx(shifts=shifts, assignments=assignments)
        headers = {
            "Content-Disposition": 'attachment; filename="open-flair-schichtplan.xlsx"'
        }

        return Response(
            content=workbook_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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

        if user.is_coordinator:
            span.add_event("coordinator_assignment_blocked", {"user_id": assignment.user_id})
            span.set_attribute("error", "Coordinator accounts cannot be assigned to shifts")
            raise HTTPException(
                status_code=400,
                detail="Coordinator accounts cannot be assigned to shifts",
            )

        if user.is_under_16 and is_under_16_restricted_shift(shift):
            span.add_event("under_16_evening_assignment_blocked", {"user_id": assignment.user_id})
            span.set_attribute("error", "Users under 16 cannot be assigned to shifts from 20:00 onward")
            raise HTTPException(
                status_code=400,
                detail="Users under 16 cannot be assigned to shifts from 20:00 onward",
            )

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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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

        if any(user.is_coordinator for user in group.users):
            span.add_event("coordinator_group_assignment_blocked", {"group_id": assignment.group_id})
            span.set_attribute("error", "Groups with coordinator accounts cannot be assigned to shifts")
            raise HTTPException(
                status_code=400,
                detail="Groups with coordinator accounts cannot be assigned to shifts",
            )

        if is_under_16_restricted_shift(shift) and any(user.is_under_16 for user in group.users):
            span.add_event("under_16_group_evening_assignment_blocked", {"group_id": assignment.group_id})
            span.set_attribute("error", "Groups with users under 16 cannot be assigned to shifts from 20:00 onward")
            raise HTTPException(
                status_code=400,
                detail="Groups with users under 16 cannot be assigned to shifts from 20:00 onward",
            )

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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
    max_shifts_per_user: int = 10,
    planner_seed: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
) -> Any:
    """
    Generate a shift plan by assigning users and groups to shifts based on opt-outs.
    
    This endpoint:
    1. Gets all active shifts
    2. Clears existing assignments
    3. For each shift, considers both individual users and groups
    4. Assigns users/groups to shifts respecting capacity limits, avoiding conflicts, and respecting max shifts per user
    """
    with tracer.start_as_current_span("generate-shift-plan") as span:
        span.set_attribute("max_shifts_per_user", max_shifts_per_user)
        
        # Get all active shifts
        shifts = shift_crud.get_multi(db, skip=0, limit=1000)
        active_shifts = [shift for shift in shifts if shift.is_active]
        
        # Get all active users
        from app.crud.user import user as user_crud
        from app.crud.group import group as group_crud
        
        all_users = user_crud.get_multi(db, skip=0, limit=1000)
        active_users = [
            user for user in all_users
            if user.is_active and not user.is_coordinator
        ]
        
        # Get all active groups (always use groups)
        all_groups = group_crud.get_multi(db, skip=0, limit=1000)
        active_groups = [group for group in all_groups if group.is_active]
        
        span.set_attribute("shifts.total", len(shifts))
        span.set_attribute("shifts.active", len(active_shifts))
        span.set_attribute("users.total", len(all_users))
        span.set_attribute("users.active", len(active_users))
        span.set_attribute("groups.total", len(all_groups))
        span.set_attribute("groups.active", len(active_groups))

        resolved_planner_seed = planner_seed if planner_seed is not None else secrets.randbelow(2**32)
        rng = random.Random(resolved_planner_seed)
        randomized_decisions = 0
        span.set_attribute("planner.seed", resolved_planner_seed)
        
        if not active_shifts:
            return {
                "message": "No active shifts found",
                "assignments": [],
                "planner": {
                    "seed": resolved_planner_seed,
                    "score_window": PLANNER_RANDOMIZATION_SCORE_WINDOW,
                    "randomized_decisions": randomized_decisions,
                },
                "statistics": {
                    "shifts_assigned": 0,
                    "total_assignments": 0,
                    "group_assignments": 0,
                    "individual_assignments": 0,
                    "average_assignments_per_user": 0,
                    "conflicts_avoided": 0,
                    "max_shifts_limit_hits": 0
                }
            }
        
        if not active_users:
            return {
                "message": "No active participant users found",
                "assignments": [],
                "planner": {
                    "seed": resolved_planner_seed,
                    "score_window": PLANNER_RANDOMIZATION_SCORE_WINDOW,
                    "randomized_decisions": randomized_decisions,
                },
                "statistics": {
                    "shifts_assigned": 0,
                    "total_assignments": 0,
                    "group_assignments": 0,
                    "individual_assignments": 0,
                    "average_assignments_per_user": 0,
                    "conflicts_avoided": 0,
                    "max_shifts_limit_hits": 0
                }
            }
        
        # Always clear existing assignments
        span.add_event("clearing_existing_assignments")
        for shift in active_shifts:
            shift.users.clear()
            shift.groups.clear()
        db.commit()
        span.add_event("existing_assignments_cleared")
        
        # Track assignments and conflicts
        assignments = []
        group_assignments = 0
        individual_assignments = 0
        conflicts_avoided = 0
        max_shifts_limit_hits = 0

        # Build slot indices so we can reason about consecutive and one-gap patterns per day.
        shifts_by_day: Dict[str, List[Any]] = {}
        for shift in active_shifts:
            day_key = get_shift_day_key(shift)
            shifts_by_day.setdefault(day_key, []).append(shift)

        shift_slot_index: Dict[int, int] = {}
        for day_key, day_shifts in shifts_by_day.items():
            ordered_slot_signatures = []
            for shift in sorted(day_shifts, key=lambda s: (s.start_time, s.end_time, s.id)):
                slot_signature = get_shift_slot_signature(shift)
                if slot_signature not in ordered_slot_signatures:
                    ordered_slot_signatures.append(slot_signature)

            slot_index_by_signature = {
                signature: index for index, signature in enumerate(ordered_slot_signatures)
            }

            for shift in day_shifts:
                shift_slot_index[shift.id] = slot_index_by_signature[get_shift_slot_signature(shift)]

        # Planning units are active groups plus standalone users. Grouped users are never split up.
        planning_units: List[Dict[str, Any]] = []
        active_group_ids: Set[int] = set()

        for group in active_groups:
            if any(user.is_active and user.is_coordinator for user in group.users):
                continue

            group_users = [user for user in group.users if user.is_active]
            if not group_users:
                continue

            planning_units.append({
                "key": f"group-{group.id}",
                "type": "group",
                "group": group,
                "members": group_users,
                "size": len(group_users),
                "label": group.name,
                "location_preference": group.location_preference or "both",
                "sort_order": (0, group.id),
            })
            active_group_ids.add(group.id)

        for user in active_users:
            active_group = user.group if user.group and user.group.is_active else None
            if active_group and active_group.id in active_group_ids:
                continue

            planning_units.append({
                "key": f"user-{user.id}",
                "type": "individual",
                "user": user,
                "members": [user],
                "size": 1,
                "label": user.username,
                "location_preference": user.location_preference or "both",
                "sort_order": (1, user.id),
            })

        if not planning_units:
            return {
                "message": "No active planning units found",
                "assignments": [],
                "planner": {
                    "seed": resolved_planner_seed,
                    "score_window": PLANNER_RANDOMIZATION_SCORE_WINDOW,
                    "randomized_decisions": randomized_decisions,
                },
                "statistics": {
                    "shifts_assigned": 0,
                    "total_assignments": 0,
                    "group_assignments": 0,
                    "individual_assignments": 0,
                    "average_assignments_per_user": 0,
                    "conflicts_avoided": 0,
                    "max_shifts_limit_hits": 0,
                }
            }

        shift_slot_key: Dict[int, Tuple[str, Tuple[int, int, int, int]]] = {
            shift.id: get_shift_slot_key(shift)
            for shift in active_shifts
        }

        def unit_can_work_specific_shift(unit: Dict[str, Any], shift: Any) -> bool:
            capacity = shift.capacity or 5
            if unit["size"] > capacity:
                return False

            if is_under_16_restricted_shift(shift) and any(
                user.is_under_16 for user in unit["members"]
            ):
                return False

            return all(
                not shift_crud.is_user_opted_out(db, shift_id=shift.id, user_id=user.id)
                for user in unit["members"]
            )

        unit_available_shift_ids: Dict[str, Set[int]] = {}
        unit_available_day_keys: Dict[str, Set[str]] = {}
        unit_available_evening_counts: Dict[str, int] = {}
        unit_available_slot_counts: Dict[str, int] = {}

        for unit in planning_units:
            specifically_available_shift_ids = set()
            available_slot_keys = set()
            available_day_keys = set()
            available_evening_slots = set()

            for shift in active_shifts:
                if not unit_can_work_specific_shift(unit, shift):
                    continue

                specifically_available_shift_ids.add(shift.id)
                available_slot_keys.add(shift_slot_key[shift.id])
                available_day_keys.add(get_shift_day_key(shift))

                if is_priority_evening_shift(shift):
                    available_evening_slots.add(shift_slot_key[shift.id])

            available_shift_ids = {
                shift.id
                for shift in active_shifts
                if shift_slot_key[shift.id] in available_slot_keys
            }

            unit_available_shift_ids[unit["key"]] = available_shift_ids
            unit_available_day_keys[unit["key"]] = available_day_keys
            unit_available_evening_counts[unit["key"]] = len(available_evening_slots)
            unit_available_slot_counts[unit["key"]] = len(available_slot_keys)

        potential_unit_count = {
            shift.id: sum(
                1
                for unit in planning_units
                if shift.id in unit_available_shift_ids[unit["key"]]
            )
            for shift in active_shifts
        }

        shift_order_tiebreak = {
            shift.id: rng.random()
            for shift in active_shifts
        }

        shifts_by_slot: Dict[Tuple[str, Tuple[int, int, int, int]], List[Any]] = {}
        for shift in active_shifts:
            shifts_by_slot.setdefault(shift_slot_key[shift.id], []).append(shift)

        sorted_slot_keys = sorted(
            shifts_by_slot.keys(),
            key=lambda slot_key: (
                0 if any(is_priority_evening_shift(shift) for shift in shifts_by_slot[slot_key]) else 1,
                shift_slot_index[shifts_by_slot[slot_key][0].id],
                min(get_planner_day_start(shift).date() for shift in shifts_by_slot[slot_key]),
                min(potential_unit_count[shift.id] for shift in shifts_by_slot[slot_key]),
                min(shift.start_time for shift in shifts_by_slot[slot_key]),
                min(shift.id for shift in shifts_by_slot[slot_key]),
            ),
        )

        sorted_shifts = [
            shift
            for slot_key in sorted_slot_keys
            for shift in sorted(
                shifts_by_slot[slot_key],
                key=lambda shift: (
                    potential_unit_count[shift.id],
                    shift_order_tiebreak[shift.id],
                    shift.id,
                ),
            )
        ]

        unit_assignments: Dict[str, List[Any]] = {unit["key"]: [] for unit in planning_units}
        unit_shift_count: Dict[str, int] = {unit["key"]: 0 for unit in planning_units}
        unit_assigned_days: Dict[str, Set[str]] = {unit["key"]: set() for unit in planning_units}
        unit_day_slots: Dict[str, Dict[str, List[int]]] = {unit["key"]: {} for unit in planning_units}
        unit_evening_count: Dict[str, int] = {unit["key"]: 0 for unit in planning_units}
        unit_location_count: Dict[str, Dict[str, int]] = {
            unit["key"]: {"weinzelt": 0, "bierwagen": 0}
            for unit in planning_units
        }
        user_shift_count = {user.id: 0 for user in active_users}

        def unit_has_time_conflict(unit: Dict[str, Any], shift: Any) -> bool:
            return any(
                shifts_overlap(shift, assigned_shift)
                for assigned_shift in unit_assignments[unit["key"]]
            )

        def unit_would_create_long_stretch(unit: Dict[str, Any], shift: Any) -> bool:
            unit_key = unit["key"]
            day_key = get_shift_day_key(shift)
            same_day_slots = unit_day_slots[unit_key].get(day_key, [])
            candidate_slots = sorted(same_day_slots + [shift_slot_index[shift.id]])
            return get_max_consecutive_slots(candidate_slots) > 2

        def score_unit_for_shift(unit: Dict[str, Any], shift: Any) -> float:
            unit_key = unit["key"]
            day_key = get_shift_day_key(shift)
            assigned_days = unit_assigned_days[unit_key]
            available_days = unit_available_day_keys[unit_key]
            same_day_slots = unit_day_slots[unit_key].get(day_key, [])
            candidate_slots = sorted(same_day_slots + [shift_slot_index[shift.id]])
            location_preference = unit.get("location_preference") or "both"
            shift_location = get_shift_location_key(shift)

            score = 0.0

            # Balance overall load first.
            score -= unit_shift_count[unit_key] * 30

            # Scarcer units should be placed before highly flexible ones.
            score += max(0, 10 - unit_available_slot_counts[unit_key]) * 3

            # Prefer spreading assignments across festival days whenever possible.
            if day_key not in assigned_days:
                score += 34
                if len(available_days) > 1:
                    score += 18
            elif available_days - assigned_days:
                score -= 18
            else:
                score += 4

            # Prefer fewer assignments on the same day.
            score -= len(same_day_slots) * 8

            # Avoid stretches longer than two slots and avoid "one-slot gap" patterns.
            max_consecutive_slots = get_max_consecutive_slots(candidate_slots)
            if max_consecutive_slots > 2:
                score -= 90 * (max_consecutive_slots - 2)
            elif max_consecutive_slots == 2:
                score += 6

            if has_single_slot_gap(candidate_slots):
                score -= 45

            # Thursday/Friday/Saturday >= 20:00 should be shared fairly across planning units.
            if is_priority_evening_shift(shift):
                if unit_evening_count[unit_key] == 0:
                    score += 55
                    if unit_available_evening_counts[unit_key] == 1:
                        score += 15
                else:
                    score -= 35 * unit_evening_count[unit_key]

            # Respect preferred location when possible without making it a hard rule.
            if shift_location != "both":
                if location_preference == "both":
                    other_location = (
                        "bierwagen" if shift_location == "weinzelt" else "weinzelt"
                    )
                    score += (
                        unit_location_count[unit_key][other_location]
                        - unit_location_count[unit_key][shift_location]
                    ) * 7
                elif location_preference == shift_location:
                    score += 14
                else:
                    score -= 8

            return score

        for slot_key in sorted_slot_keys:
            slot_shifts = sorted(
                shifts_by_slot[slot_key],
                key=lambda shift: (
                    potential_unit_count[shift.id],
                    shift_order_tiebreak[shift.id],
                    shift.id,
                ),
            )

            span.add_event("processing_shift_slot", {
                "slot_day": slot_key[0],
                "slot_signature": str(slot_key[1]),
                "shift_ids": ",".join(str(shift.id) for shift in slot_shifts),
            })

            remaining_capacity_by_shift = {
                shift.id: (shift.capacity or 5) - len(shift.users)
                for shift in slot_shifts
            }

            while any(capacity > 0 for capacity in remaining_capacity_by_shift.values()):
                candidate_entries = []
                preferred_candidate_entries = []

                for shift in slot_shifts:
                    remaining_capacity = remaining_capacity_by_shift[shift.id]
                    if remaining_capacity <= 0:
                        continue

                    for unit in planning_units:
                        unit_key = unit["key"]

                        if shift.id not in unit_available_shift_ids[unit_key]:
                            continue

                        if unit["size"] > remaining_capacity:
                            continue

                        if any(
                            user_shift_count[user.id] >= max_shifts_per_user
                            for user in unit["members"]
                        ):
                            max_shifts_limit_hits += 1
                            continue

                        if unit_has_time_conflict(unit, shift):
                            conflicts_avoided += 1
                            continue

                        candidate_entry = {
                            "score": score_unit_for_shift(unit, shift),
                            "unit_shift_count": unit_shift_count[unit_key],
                            "shift_candidate_count": potential_unit_count[shift.id],
                            "shift_order_tiebreak": shift_order_tiebreak[shift.id],
                            "sort_order": unit["sort_order"],
                            "shift": shift,
                            "unit": unit,
                        }
                        candidate_entries.append(candidate_entry)

                        if not unit_would_create_long_stretch(unit, shift):
                            preferred_candidate_entries.append(candidate_entry)

                if preferred_candidate_entries:
                    candidate_entries = preferred_candidate_entries

                if not candidate_entries:
                    break

                scored_candidates = sorted(
                    candidate_entries,
                    key=lambda item: (
                        -item["score"],
                        item["unit_shift_count"],
                        item["shift_candidate_count"],
                        item["shift_order_tiebreak"],
                        item["sort_order"],
                    ),
                )

                best_score = scored_candidates[0]["score"]
                top_candidate_entries = [
                    entry
                    for entry in scored_candidates
                    if best_score - entry["score"] <= PLANNER_RANDOMIZATION_SCORE_WINDOW
                ]
                if len(top_candidate_entries) > 1:
                    randomized_decisions += 1

                selected_entry = rng.choice(top_candidate_entries)
                selected_shift = selected_entry["shift"]
                selected_unit = selected_entry["unit"]
                selected_unit_key = selected_unit["key"]
                selected_day_key = get_shift_day_key(selected_shift)

                unit_assignments[selected_unit_key].append(selected_shift)
                unit_shift_count[selected_unit_key] += 1
                unit_assigned_days[selected_unit_key].add(selected_day_key)
                unit_day_slots[selected_unit_key].setdefault(selected_day_key, []).append(
                    shift_slot_index[selected_shift.id]
                )

                if is_priority_evening_shift(selected_shift):
                    unit_evening_count[selected_unit_key] += 1

                selected_location = get_shift_location_key(selected_shift)
                if selected_location in ("weinzelt", "bierwagen"):
                    unit_location_count[selected_unit_key][selected_location] += 1

                if selected_unit["type"] == "group":
                    selected_group = selected_unit["group"]
                    if selected_group not in selected_shift.groups:
                        selected_shift.groups.append(selected_group)
                    group_assignments += 1
                else:
                    selected_group = None
                    individual_assignments += 1

                for user in selected_unit["members"]:
                    if user not in selected_shift.users:
                        selected_shift.users.append(user)
                    user_shift_count[user.id] += 1

                    assignments.append({
                        "shift_id": selected_shift.id,
                        "shift_title": selected_shift.title,
                        "user_id": user.id,
                        "username": user.username,
                        "assigned_via": "group" if selected_unit["type"] == "group" else "individual",
                        "group_name": selected_group.name if selected_group else None,
                    })

                remaining_capacity_by_shift[selected_shift.id] -= selected_unit["size"]

                span.add_event("planning_unit_assigned", {
                    "shift_id": selected_shift.id,
                    "planning_unit": selected_unit["label"],
                    "assigned_via": selected_unit["type"],
                    "unit_size": selected_unit["size"],
                    "remaining_capacity": remaining_capacity_by_shift[selected_shift.id],
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
            "max_shifts_limit_hits": max_shifts_limit_hits,
            "groups_used": len(set(a.get("group_name") for a in assignments if a.get("assigned_via") == "group"))
        }
        
        span.set_attribute("assignments.total", total_assignments)
        span.set_attribute("assignments.groups", group_assignments)
        span.set_attribute("assignments.individuals", individual_assignments)
        span.set_attribute("max_shifts_limit_hits", max_shifts_limit_hits)
        span.set_attribute("planner.randomized_decisions", randomized_decisions)
        
        return {
            "message": f"Successfully generated shift plan with {total_assignments} assignments ({group_assignments} groups, {individual_assignments} individuals). Max shifts limit hit {max_shifts_limit_hits} times.",
            "assignments": assignments,
            "planner": {
                "seed": resolved_planner_seed,
                "score_window": PLANNER_RANDOMIZATION_SCORE_WINDOW,
                "randomized_decisions": randomized_decisions,
            },
            "statistics": statistics
        }

def shifts_overlap(shift1, shift2):
    """Check if two shifts overlap in time."""
    return (shift1.start_time < shift2.end_time and 
            shift1.end_time > shift2.start_time)

@router.post("/user-opt-out", status_code=status.HTTP_200_OK)
def opt_out_user(
    opt_out: ShiftUserBase,
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_self_or_coordinator(auth_session, opt_out.user_id)
        
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
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_self_or_coordinator(auth_session, opt_in.user_id)
        
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
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_group_member_or_coordinator(db, auth_session, opt_out.group_id)
        
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
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_group_member_or_coordinator(db, auth_session, opt_in.group_id)
        
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
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_self_or_coordinator(auth_session, user_id)
        
        # Check if user is opted out
        is_opted_out = shift_crud.is_user_opted_out(
            db, shift_id=shift_id, user_id=user_id
        )
        
        return {"is_opted_out": is_opted_out}

@router.get("/user-opt-outs/{user_id}", response_model=List[Shift])
def get_user_opt_outs(
    user_id: int,
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_self_or_coordinator(auth_session, user_id)
        
        # Get opt-outs
        opt_outs = shift_crud.get_user_opt_outs(db, user_id=user_id)
        
        return opt_outs

@router.get("/group-opt-outs/{group_id}", response_model=List[Shift])
def get_group_opt_outs(
    group_id: int,
    db: Session = Depends(get_db),
    auth_session: AuthSession = Depends(require_auth),
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

        ensure_group_member_or_coordinator(db, auth_session, group_id)
        
        # Get opt-outs
        opt_outs = shift_crud.get_group_opt_outs(db, group_id=group_id)
        
        return opt_outs

@router.get("/available-users/{shift_id}", response_model=List[User])
def get_available_users(
    shift_id: int,
    db: Session = Depends(get_db),
    _: AuthSession = Depends(require_coordinator),
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
        if is_under_16_restricted_shift(shift):
            available_users = [
                user for user in available_users
                if not user.is_under_16
            ]

        return available_users
