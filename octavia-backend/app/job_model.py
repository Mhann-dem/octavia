"""Job model for tracking media processing tasks."""
import uuid
from sqlalchemy import Column, String, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base
import enum


class JobStatus(str, enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """Represents a background job (transcription, translation, synthesis, etc.)."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    job_type = Column(String, nullable=False)  # 'transcribe', 'translate', 'synthesize', etc.
    input_file = Column(String, nullable=False)  # Storage path
    output_file = Column(String, nullable=True)  # Storage path (set when completed)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    error_message = Column(String, nullable=True)
    job_metadata = Column(Text, nullable=True)  # JSON string with job-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
