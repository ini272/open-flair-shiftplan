from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    """Base schema with common user attributes"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    is_coordinator: Optional[bool] = None  # Add this line

class UserCreate(UserBase):
    """Schema for creating a user"""
    email: EmailStr
    username: str

class UserUpdate(UserBase):
    """Schema for updating a user"""

class User(UserBase):
    """Schema for returning user data"""
    id: int
    email: EmailStr
    username: str
    is_active: bool
    is_coordinator: bool  # Add this line
    group_id: Optional[int] = None
    
    class Config:
        orm_mode = True

# Add this new schema for email lookup
class EmailLookup(BaseModel):
    """Schema for looking up a user by email"""
    email: EmailStr