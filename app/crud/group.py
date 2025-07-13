from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.crud.base import CRUDBase
from app.models.group import Group
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate

# Default max group size (can be overridden)
DEFAULT_MAX_GROUP_SIZE = 4

class CRUDGroup(CRUDBase[Group, GroupCreate, GroupUpdate]):
    """
    CRUD operations for Group model.
    Extends the base CRUD operations with group-specific functionality.
    """
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[Group]:
        """Get a group by name"""
        return db.query(Group).filter(Group.name == name).first()
    
    def create(self, db: Session, *, obj_in: GroupCreate) -> Group:
        """
        Create a new group
        """
        # Create a dict of group data
        db_obj = Group(
            name=obj_in.name,
            is_active=True
        )
        
        # Add to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_active(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Group]:
        """
        Get all active groups
        """
        return db.query(Group).filter(Group.is_active is True).offset(skip).limit(limit).all()
    
    def get_group_size(self, db: Session, *, group_id: int) -> int:
        """Get the current size of a group"""
        return db.query(func.count(User.id)).filter(User.group_id == group_id).scalar() or 0
    
    def can_add_user_to_group(self, db: Session, *, group_id: int, max_size: int = DEFAULT_MAX_GROUP_SIZE) -> bool:
        """Check if a user can be added to a group (not at max capacity)"""
        current_size = self.get_group_size(db, group_id=group_id)
        return current_size < max_size
    
    def add_user_to_group(self, db: Session, *, group_id: int, user_id: int, max_size: int = DEFAULT_MAX_GROUP_SIZE) -> Optional[Group]:
        """Add a user to a group if there's space"""
        # Check if group has space
        if not self.can_add_user_to_group(db, group_id=group_id, max_size=max_size):
            return None
        
        # Get the user and group
        user = db.query(User).filter(User.id == user_id).first()
        group = self.get(db, id=group_id)
        
        if not user or not group:
            return None
        
        # Add user to group
        user.group_id = group_id
        db.commit()
        db.refresh(group)
        return group
    
    def remove_user_from_group(self, db: Session, *, user_id: int) -> Any:
        """
        Remove a user from their group
        
        Args:
            db: Database session
            user_id: ID of the user to remove from group
            
        Returns:
            Updated user object
        """
        from app.models.user import User
        
        # Get the user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
            
        # Remove the user's group
        user.group_id = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

# Create a singleton instance
group = CRUDGroup(Group)
