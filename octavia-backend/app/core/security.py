"""Security utilities: password hashing and JWT token management."""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException

SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))

# Use pbkdf2_sha256 instead of bcrypt to avoid passlib/bcrypt version issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_verification_token(user_id: str, expires_minutes: int = 60 * 24) -> str:
    """Create email verification token."""
    return create_access_token({"sub": str(user_id), "type": "verify"}, expires_delta=timedelta(minutes=expires_minutes))


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def is_verification_token(payload: Dict[str, Any]) -> bool:
    """Check if token is a verification token."""
    return payload.get("type") == "verify"


def get_bearer_token(authorization: Optional[str] = None) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return parts[1]


def extract_token_from_request(authorization: Optional[str] = None, cookies: Optional[dict] = None) -> str:
    """Extract token either from Authorization header or from cookies.

    This helper allows the application to accept HttpOnly cookies set by the
    backend for SSR and normal Authorization headers for API clients.
    """
    # Prefer Authorization header if provided
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    # Fallback to cookie token
    if cookies:
        # Common cookie name used by the app
        token = cookies.get("octavia_token") or cookies.get("token")
        if token:
            return token

    raise HTTPException(status_code=401, detail="Missing authorization token")

