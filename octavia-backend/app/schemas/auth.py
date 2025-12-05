"""Authentication schemas."""
from pydantic import BaseModel, EmailStr
from typing import Optional


class SignupPayload(BaseModel):
    """User signup request."""
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """User output schema."""
    id: str
    email: str
    is_verified: bool
    credits: int

    class Config:
        from_attributes = True
