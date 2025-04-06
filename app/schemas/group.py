from typing import Optional, List
from pydantic import BaseModel

from app.schemas.user import User

class GroupBase(BaseModel):
    """Base schema with common group attributes"""
    name: Optional[str] = None
    is_active: Optional[bool] = None

class GroupCreate(GroupBase):
    """Schema for creating a group"""
    name: str

class GroupUpdate(GroupBase):
    """Schema for updating a group"""
    pass

class Group(GroupBase):
    """Schema for returning group data"""
    id: int
    name: str
    is_active: bool
    
    class Config:
        orm_mode = True

class GroupWithUsers(Group):
    """Schema for returning group data with its users"""
    users: List[User] = []
    
    class Config:
        orm_mode = True
