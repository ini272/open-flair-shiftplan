from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr

LocationPreference = Literal["both", "weinzelt", "bierwagen"]

class UserBase(BaseModel):
    """Base schema with common user attributes"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    is_coordinator: Optional[bool] = None  # Add this line
    location_preference: Optional[LocationPreference] = "both"

class UserCreate(UserBase):
    """Schema for creating a user"""
    email: EmailStr
    username: str

class UserUpdate(UserBase):
    """Schema for updating a user"""

class User(UserBase):
    """Schema for returning user data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_active: bool
    is_coordinator: bool  # Add this line
    group_id: Optional[int] = None
    location_preference: LocationPreference = "both"

# Add this new schema for email lookup
class EmailLookup(BaseModel):
    """Schema for looking up a user by email"""
    email: EmailStr
