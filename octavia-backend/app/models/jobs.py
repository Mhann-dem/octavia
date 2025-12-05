"""Job models for transcription and video translation."""
import uuid
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class JobStatus(str, enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJob(Base):
    """Transcription job record."""
    __tablename__ = "transcription_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class VideoTranslationJob(Base):
    """Video translation job record."""
    __tablename__ = "video_translation_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    target_language = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
