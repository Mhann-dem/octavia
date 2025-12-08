import os
from fastapi import FastAPI, Depends, HTTPException, status, Response
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
from app.upload_routes import router as upload_router
from app.sse_routes import router as sse_router
from app.auth_routes import router as auth_router


app = FastAPI(title="Octavia Backend")

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(billing_router)
app.include_router(upload_router)
app.include_router(sse_router)
app.include_router(auth_router)

frontend = os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", frontend],
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
def login(payload: LoginPayload, response: Response, db_session: Session = Depends(get_db)):
    user = db_session.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # For local dev: skip email verification check (remove or comment out for production)
    # if not user.is_verified:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    token = create_access_token({"sub": str(user.id), "type": "access"})

    # Set token in an HttpOnly cookie so SSR requests can read it.
    # Use secure cookies in production if TLS is enabled.
    secure_cookie = os.environ.get("OCTAVIA_SECURE_COOKIES", "false").lower() in ("1", "true", "yes")
    # Allow cross-site cookies in dev when the frontend is on a different origin.
    # NOTE: browsers require SameSite=None for cross-site cookies. In production
    # you should set OCTAVIA_SECURE_COOKIES=true and serve over HTTPS.
    allow_cross_site = os.environ.get("OCTAVIA_ALLOW_CROSS_SITE_COOKIES", "true").lower() in ("1", "true", "yes")
    cookie_name = "octavia_token"
    samesite_setting = "none" if allow_cross_site else "lax"

    response.set_cookie(
        key=cookie_name,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite=samesite_setting,
        path="/",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )

    # Also return token in JSON for JS clients that still want to use it client-side
    return {"access_token": token}