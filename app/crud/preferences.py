from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.preferences import user_shift_preferences
from app.models.user import User
from app.models.shift import Shift

class CRUDPreference:
    """
    CRUD operations for user shift preferences.
    """
    
    def set_preference(
        self, 
        db: Session, 
        *, 
        user_id: int,
        shift_id: int,
        can_work: bool
    ) -> bool:
        """
        Set a user's preference for a shift.
        
        Args:
            db: Database session
            user_id: ID of the user
            shift_id: ID of the shift
            can_work: Whether the user can work this shift
            
        Returns:
            True if successful, False otherwise
        """
        # Check if user and shift exist
        user = db.query(User).filter(User.id == user_id).first()
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        
        if not user or not shift:
            return False
        
        # Check if preference already exists
        stmt = user_shift_preferences.delete().where(
            and_(
                user_shift_preferences.c.user_id == user_id,
                user_shift_preferences.c.shift_id == shift_id
            )
        )
        db.execute(stmt)
        
        # Insert new preference
        stmt = user_shift_preferences.insert().values(
            user_id=user_id,
            shift_id=shift_id,
            can_work=can_work
        )
        db.execute(stmt)
        db.commit()
        
        return True
    
    def get_preferences(
        self, 
        db: Session, 
        *, 
        user_id: int
    ) -> List[dict]:
        """
        Get all preferences for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            List of preferences (shift_id, can_work)
        """
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Get preferences
        stmt = db.query(
            user_shift_preferences.c.shift_id,
            user_shift_preferences.c.can_work
        ).filter(
            user_shift_preferences.c.user_id == user_id
        )
        
        # Include the user_id in each preference
        return [{"user_id": user_id, "shift_id": row[0], "can_work": row[1]} for row in stmt]
    
    def get_users_for_shift(
        self, 
        db: Session, 
        *, 
        shift_id: int,
        can_work: bool = True
    ) -> List[int]:
        """
        Get all users who can/cannot work a shift.
        
        Args:
            db: Database session
            shift_id: ID of the shift
            can_work: Filter for users who can work (True) or cannot work (False)
            
        Returns:
            List of user IDs
        """
        # Check if shift exists
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            return []
        
        # Get users
        stmt = db.query(
            user_shift_preferences.c.user_id
        ).filter(
            and_(
                user_shift_preferences.c.shift_id == shift_id,
                user_shift_preferences.c.can_work == can_work
            )
        )
        
        return [row[0] for row in stmt]

# Create a singleton instance
preference = CRUDPreference()