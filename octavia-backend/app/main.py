import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.core.security import (
    get_password_hash, create_verification_token, decode_token, 
    verify_password, create_access_token, is_verification_token
)
from app.models import User
from app.schemas.auth import SignupPayload, LoginPayload, TokenResponse, UserOut
from app.utils.email import send_verification_email
from app.routes.billing import router as billing_router


app = FastAPI(title="Octavia Backend")

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(billing_router)

frontend = os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/signup")
def signup(payload: SignupPayload, db_session: Session = Depends(get_db)):
    existing = db_session.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        is_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # create a verification token and URL
    token = create_verification_token(str(user.id))
    verify_url = f"{frontend}/auth/verify?token={token}"

    # Attempt to send verification email. If email provider isn't configured, print the link for dev.
    sent = send_verification_email(user.email, verify_url)

    user_out = UserOut.model_validate(user)
    response = {
        "user": user_out.model_dump(),
        "verify_url": verify_url  # Always include for dev convenience
    }
    return response


@app.get("/verify")
def verify(token: str, db_session: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload or not is_verification_token(payload):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user_id = payload.get("sub")
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db_session.add(user)
    db_session.commit()
    return {"status": "verified"}


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginPayload, db_session: Session = Depends(get_db)):
    user = db_session.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    token = create_access_token({"sub": str(user.id), "type": "access"})
    return {"access_token": token}