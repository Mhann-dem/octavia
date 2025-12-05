"""User model."""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    credits = Column(BigInteger, default=0)
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
