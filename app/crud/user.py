from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
import hashlib

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model.
    Extends the base CRUD operations with user-specific functionality.
    """
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """Get a user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Create a new user with password hashing
        """
        # Hash the password
        hashed_password = hashlib.sha256(obj_in.password.encode()).hexdigest()
        
        # Create a dict of user data
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            hashed_password=hashed_password,
            is_active=True
        )
        
        # Add to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: User, 
        obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        Update a user, handling password hashing if needed
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        # Hash password if it's being updated
        if "password" in update_data:
            hashed_password = hashlib.sha256(update_data["password"].encode()).hexdigest()
            update_data["hashed_password"] = hashed_password
            del update_data["password"]
            
        return super().update(db, db_obj=db_obj, obj_in=update_data)

# Create a singleton instance
user = CRUDUser(User)
