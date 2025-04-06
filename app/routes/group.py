from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_tracer, get_db
from app.schemas.group import Group, GroupCreate, GroupUpdate, GroupWithUsers
from app.schemas.user import User
from app.crud.group import group as group_crud
from app.crud.user import user as user_crud

# Create a router for group-related endpoints
router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    responses={404: {"description": "Not found"}},
)

# Get the tracer for this module
tracer = get_tracer()

@router.post("/", response_model=Group, status_code=status.HTTP_201_CREATED)
def create_group(
    group_in: GroupCreate, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new group.
    """
    with tracer.start_as_current_span("create-group") as span:
        span.set_attribute("group.name", group_in.name)
        
        # Check if group with this name already exists
        db_group = group_crud.get_by_name(db, name=group_in.name)
        if db_group:
            span.set_attribute("error", "Group name already exists")
            raise HTTPException(
                status_code=400, detail="Group with this name already exists"
            )
        
        # Create the group
        group = group_crud.create(db=db, obj_in=group_in)
        span.set_attribute("group.id", group.id)
        return group

@router.get("/", response_model=List[Group])
def read_groups(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a list of groups with pagination.
    """
    with tracer.start_as_current_span("get-groups") as span:
        span.set_attribute("query.skip", skip)
        span.set_attribute("query.limit", limit)
        
        groups = group_crud.get_active(db, skip=skip, limit=limit)
        span.set_attribute("result.count", len(groups))
        return groups

@router.get("/{group_id}", response_model=GroupWithUsers)
def read_group(
    group_id: int, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific group by ID, including its users.
    """
    with tracer.start_as_current_span("get-group") as span:
        span.set_attribute("group.id", group_id)
        
        group = group_crud.get(db, id=group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        return group

@router.put("/{group_id}", response_model=Group)
def update_group(
    group_id: int, 
    group_in: GroupUpdate, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Update a group.
    """
    with tracer.start_as_current_span("update-group") as span:
        span.set_attribute("group.id", group_id)
        
        group = group_crud.get(db, id=group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # If name is being updated, check it doesn't conflict
        if group_in.name and group_in.name != group.name:
            existing_group = group_crud.get_by_name(db, name=group_in.name)
            if existing_group:
                span.set_attribute("error", "Group name already exists")
                raise HTTPException(
                    status_code=400, detail="Group with this name already exists"
                )
        
        updated_group = group_crud.update(db=db, db_obj=group, obj_in=group_in)
        return updated_group

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int, 
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a group.
    """
    with tracer.start_as_current_span("delete-group") as span:
        span.set_attribute("group.id", group_id)
        
        group = group_crud.get(db, id=group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_crud.remove(db=db, id=group_id)

@router.post("/{group_id}/users/{user_id}", response_model=User)
def add_user_to_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Add a user to a group.
    """
    with tracer.start_as_current_span("add-user-to-group") as span:
        span.set_attribute("group.id", group_id)
        span.set_attribute("user.id", user_id)
        
        # Check if group exists
        group = group_crud.get(db, id=group_id)
        if not group:
            span.set_attribute("error", "Group not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Check if user exists
        user = user_crud.get(db, id=user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Add user to group
        updated_user = group_crud.add_user_to_group(db, group_id=group_id, user_id=user_id)
        return updated_user

@router.delete("/users/{user_id}", response_model=User)
def remove_user_from_group(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Remove a user from their group.
    """
    with tracer.start_as_current_span("remove-user-from-group") as span:
        span.set_attribute("user.id", user_id)
        
        # Check if user exists
        user = user_crud.get(db, id=user_id)
        if not user:
            span.set_attribute("error", "User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is in a group
        if user.group_id is None:
            span.set_attribute("error", "User not in a group")
            raise HTTPException(status_code=400, detail="User is not in a group")
        
        # Remove user from group
        updated_user = group_crud.remove_user_from_group(db, user_id=user_id)
        return updated_user
