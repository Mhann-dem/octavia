import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=(expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_verification_token(user_id: str, expires_minutes: int = 60 * 24) -> str:
    return create_access_token({"sub": str(user_id), "type": "verify"}, expires_delta=expires_minutes)


def is_verification_token(payload: dict) -> bool:
    return payload.get("type") == "verify"


def get_bearer_token(authorization: str | None = None) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return parts[1]


def extract_token_from_request(authorization: str | None = None, cookies: dict | None = None) -> str:
    """Extract token from Authorization header or cookies (compatibility helper).

    This mirrors the helper used in app.core.security to allow both
    header-based Bearer tokens and HttpOnly cookie tokens to be accepted.
    """
    # Prefer Authorization header if present
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    # Fallback to cookie token
    if cookies:
        token = cookies.get("octavia_token") or cookies.get("token")
        if token:
            return token

    raise HTTPException(status_code=401, detail="Missing authorization token")
