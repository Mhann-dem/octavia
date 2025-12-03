import uuid
from sqlalchemy import Column, String, Boolean, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    credits = Column(BigInteger, default=0)
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
