from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, validator

class ShiftBase(BaseModel):
    """Base schema with common shift attributes"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None

class ShiftCreate(ShiftBase):
    """Schema for creating a shift"""
    title: str
    start_time: datetime
    end_time: datetime
    
    @validator('start_time', 'end_time', pre=True)
    def parse_datetime(cls, value):
        """Convert string datetime to Python datetime object"""
        if isinstance(value, str):
            try:
                # Try ISO format with timezone
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try ISO format without microseconds
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    try:
                        # Try ISO format with microseconds
                        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        raise ValueError(f"Invalid datetime format: {value}")
        return value
    
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @validator('capacity')
    def capacity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('capacity must be positive or null for unlimited')
        return v

class ShiftUpdate(ShiftBase):
    """Schema for updating a shift"""
    
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if v is not None and 'start_time' in values and values['start_time'] is not None and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @validator('capacity')
    def capacity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('capacity must be positive or null for unlimited')
        return v

class ShiftUserBase(BaseModel):
    """Base schema for shift-user assignments"""
    shift_id: int
    user_id: int

class ShiftGroupBase(BaseModel):
    """Base schema for shift-group assignments"""
    shift_id: int
    group_id: int

class ShiftUser(ShiftUserBase):
    """Schema for returning shift-user assignment"""
    assigned_at: datetime
    
    class Config:
        orm_mode = True

class ShiftGroup(ShiftGroupBase):
    """Schema for returning shift-group assignment"""
    assigned_at: datetime
    
    class Config:
        orm_mode = True

class Shift(ShiftBase):
    """Schema for returning shift data"""
    id: int
    title: str
    start_time: datetime
    end_time: datetime
    capacity: Optional[int] = None
    created_at: datetime
    is_active: bool
    current_user_count: int
    
    class Config:
        orm_mode = True

class ShiftWithAssignees(Shift):
    """Schema for returning shift with assignee details"""
    users: List['User'] = []
    groups: List['Group'] = []
    
    class Config:
        orm_mode = True

# Avoid circular imports by importing these after the class definitions
from app.schemas.user import User
from app.schemas.group import Group

# Update forward references
ShiftWithAssignees.update_forward_refs()
