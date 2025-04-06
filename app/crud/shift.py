from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.crud.base import CRUDBase
from app.models.shift import Shift
from app.models.associations import shift_users, shift_groups
from app.schemas.shift import ShiftCreate, ShiftUpdate

class CRUDShift(CRUDBase[Shift, ShiftCreate, ShiftUpdate]):
    """
    CRUD operations for Shift model.
    Extends the base CRUD operations with shift-specific functionality.
    """
    
    def get_by_time_range(
        self, 
        db: Session, 
        *, 
        start_time: datetime, 
        end_time: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Shift]:
        """
        Get shifts within a time range.
        
        A shift is considered within the range if it overlaps with the range at all.
        """
        return db.query(Shift).filter(
            and_(
                Shift.end_time > start_time,
                Shift.start_time < end_time,
                Shift.is_active == True
            )
        ).offset(skip).limit(limit).all()
    
    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Shift]:
        """Get shifts assigned to a specific user."""
        return db.query(Shift).join(
            shift_users, Shift.id == shift_users.c.shift_id
        ).filter(
            shift_users.c.user_id == user_id,
            Shift.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_group(
        self, 
        db: Session, 
        *, 
        group_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Shift]:
        """Get shifts assigned to a specific group."""
        return db.query(Shift).join(
            shift_groups, Shift.id == shift_groups.c.shift_id
        ).filter(
            shift_groups.c.group_id == group_id,
            Shift.is_active == True
        ).offset(skip).limit(limit).all()
    
    def add_user_to_shift(
        self, 
        db: Session, 
        *, 
        shift_id: int,
        user_id: int
    ) -> Optional[Shift]:
        """
        Add a user to a shift.
        
        Checks capacity constraints before adding.
        """
        shift = self.get(db, id=shift_id)
        if not shift:
            return None
            
        # Check if user is already assigned
        if any(user.id == user_id for user in shift.users):
            return shift
            
        # Check capacity
        if shift.capacity is not None and len(shift.users) >= shift.capacity:
            return None
            
        # Get the user from the database
        from app.crud.user import user as user_crud
        user = user_crud.get(db, id=user_id)
        if not user:
            return None
            
        # Add user to shift
        shift.users.append(user)
        db.commit()
        db.refresh(shift)
        return shift
    
    def add_group_to_shift(
        self, 
        db: Session, 
        *, 
        shift_id: int,
        group_id: int
    ) -> Optional[Shift]:
        """
        Add a group to a shift.
        
        This adds the group and also adds all users in the group to the shift.
        Checks capacity constraints before adding.
        """
        shift = self.get(db, id=shift_id)
        if not shift:
            return None
            
        # Check if group is already assigned
        if any(group.id == group_id for group in shift.groups):
            return shift
            
        # Get the group from the database
        from app.crud.group import group as group_crud
        group = group_crud.get(db, id=group_id)
        if not group:
            return None
            
        # Check capacity - need to know how many new users will be added
        new_users = [user for user in group.users if user not in shift.users]
        if shift.capacity is not None and len(shift.users) + len(new_users) > shift.capacity:
            return None
            
        # Add group to shift
        shift.groups.append(group)
        
        # Add all users from the group to the shift
        for user in new_users:
            shift.users.append(user)
            
        db.commit()
        db.refresh(shift)
        return shift
    
    def remove_user_from_shift(
        self, 
        db: Session, 
        *, 
        shift_id: int,
        user_id: int
    ) -> Optional[Shift]:
        """Remove a user from a shift."""
        shift = self.get(db, id=shift_id)
        if not shift:
            return None
            
        # Get the user from the database
        from app.crud.user import user as user_crud
        user = user_crud.get(db, id=user_id)
        if not user or user not in shift.users:
            return shift
            
        # Remove user from shift
        shift.users.remove(user)
        db.commit()
        db.refresh(shift)
        return shift
    
    def remove_group_from_shift(
        self, 
        db: Session, 
        *, 
        shift_id: int,
        group_id: int
    ) -> Optional[Shift]:
        """
        Remove a group from a shift.
        
        This removes the group but does NOT remove the individual users
        that were added as part of the group.
        """
        shift = self.get(db, id=shift_id)
        if not shift:
            return None
            
        # Get the group from the database
        from app.crud.group import group as group_crud
        group = group_crud.get(db, id=group_id)
        if not group or group not in shift.groups:
            return shift
            
        # Remove group from shift
        shift.groups.remove(group)
        db.commit()
        db.refresh(shift)
        return shift

    def create(self, db: Session, *, obj_in: ShiftCreate) -> Shift:
        """
        Create a new shift with proper datetime handling
        """
        # Extract values directly from the Pydantic model
        db_obj = Shift(
            title=obj_in.title,
            description=obj_in.description,
            start_time=obj_in.start_time,
            end_time=obj_in.end_time,
            capacity=obj_in.capacity,
            is_active=True
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

# Create a singleton instance
shift = CRUDShift(Shift)
