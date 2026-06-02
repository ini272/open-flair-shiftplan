from typing import Literal, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    access_code: str


class LoginResponse(BaseModel):
    authenticated: bool
    role: Literal["participant", "coordinator"]
    user_id: Optional[int] = None
    message: str


class AuthCheckResponse(BaseModel):
    authenticated: bool
    role: Optional[Literal["participant", "coordinator"]] = None
    user_id: Optional[int] = None
