from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
    expires_at: datetime


class UserInfo(BaseModel):
    username: str
    full_name: str
    role: str
    expires_at: datetime