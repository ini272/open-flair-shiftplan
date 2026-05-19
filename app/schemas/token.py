from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TokenCreate(BaseModel):
    """Schema for creating a new token"""
    name: str
    expires_in_days: Optional[int] = None
    is_coordinator_token: Optional[bool] = False  # Add this line

class TokenResponse(BaseModel):
    """Schema for token response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    is_coordinator_token: bool  # Add this line
