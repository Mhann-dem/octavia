from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from uuid import UUID


class SignupPayload(BaseModel):
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
