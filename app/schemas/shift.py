from typing import Literal, Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class ShiftBase(BaseModel):
    """Base schema with common shift attributes"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
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

    @field_validator('capacity')
    @classmethod
    def capacity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('capacity must be positive or null for unlimited')
        return v

class ShiftCreate(ShiftBase):
    """Schema for creating a shift"""
    title: str
    start_time: datetime
    end_time: datetime

    @model_validator(mode='after')
    def end_time_must_be_after_start_time(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self

class ShiftUpdate(ShiftBase):
    """Schema for updating a shift"""

    @model_validator(mode='after')
    def end_time_must_be_after_start_time(self):
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self

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
    model_config = ConfigDict(from_attributes=True)

    assigned_at: datetime

class ShiftGroup(ShiftGroupBase):
    """Schema for returning shift-group assignment"""
    model_config = ConfigDict(from_attributes=True)

    assigned_at: datetime


class ShiftExportAssignment(BaseModel):
    """Assignment payload used for XLSX export previews."""
    shift_id: int
    username: str
    assigned_via: Literal["group", "individual"]
    group_name: Optional[str] = None
    user_id: Optional[int] = None


class ShiftXlsxExportRequest(BaseModel):
    """Optional assignment overlay for exporting the currently shown plan."""
    assignments: Optional[List[ShiftExportAssignment]] = None

class Shift(ShiftBase):
    """Schema for returning shift data"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_time: datetime
    end_time: datetime
    capacity: Optional[int] = None
    created_at: datetime
    is_active: bool
    current_user_count: int

class ShiftWithAssignees(Shift):
    """Schema for returning shift with assignee details"""
    model_config = ConfigDict(from_attributes=True)

    users: List['User'] = []
    groups: List['Group'] = []

# Avoid circular imports by importing these after the class definitions
from app.schemas.user import User
from app.schemas.group import Group

# Update forward references
ShiftWithAssignees.model_rebuild()
