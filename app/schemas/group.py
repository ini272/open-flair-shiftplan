from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.user import User

LocationPreference = Literal["both", "weinzelt", "bierwagen"]

class GroupBase(BaseModel):
    """Base schema with common group attributes"""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    location_preference: Optional[LocationPreference] = "both"

class GroupCreate(GroupBase):
    """Schema for creating a group"""
    name: str

class GroupUpdate(GroupBase):
    """Schema for updating a group"""
    pass

class Group(GroupBase):
    """Schema for returning group data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    location_preference: LocationPreference = "both"

class GroupWithUsers(Group):
    """Schema for returning group data with its users"""
    model_config = ConfigDict(from_attributes=True)

    users: List[User] = []
