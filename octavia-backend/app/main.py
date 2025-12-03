import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import db, models, schemas, security
from .emailer import send_verification_email

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Octavia Backend")

frontend = os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/signup")
def signup(payload: schemas.SignupPayload, db_session: Session = Depends(db.get_db)):
    existing = db_session.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=payload.email,
        password_hash=security.get_password_hash(payload.password),
        is_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # create a verification token and URL
    token = security.create_verification_token(str(user.id))
    verify_url = f"{frontend}/auth/verify?token={token}"

    # Attempt to send verification email. If email provider isn't configured, print the link for dev.
    sent = send_verification_email(user.email, verify_url)

    user_out = schemas.UserOut.from_orm(user)
    response = {"user": user_out}
    if not sent:
        # Return the link in response for easier local testing when emails aren't configured
        response["verify_url"] = verify_url
    return response


@app.get("/verify")
def verify(token: str, db_session: Session = Depends(db.get_db)):
    payload = security.decode_token(token)
    if not payload or not security.is_verification_token(payload):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user_id = payload.get("sub")
    user = db_session.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db_session.add(user)
    db_session.commit()
    return {"status": "verified"}


@app.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginPayload, db_session: Session = Depends(db.get_db)):
    user = db_session.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    token = security.create_access_token({"sub": str(user.id), "type": "access"})
    return {"access_token": token}
