from pydantic import BaseModel

class PreferenceBase(BaseModel):
    """Base schema for shift preferences"""
    user_id: int
    shift_id: int
    can_work: bool

class PreferenceCreate(PreferenceBase):
    """Schema for creating a preference"""
    pass

class PreferenceResponse(PreferenceBase):
    """Schema for returning a preference"""
    class Config:
        orm_mode = True