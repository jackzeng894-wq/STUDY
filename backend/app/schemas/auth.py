"""Auth request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class StudentRegister(BaseModel):
    username: str
    email: str | None = None
    password: str


class StudentLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StudentResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
