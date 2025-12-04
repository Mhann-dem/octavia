"""Schemas for file upload and job tracking."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    """Job status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobOut(BaseModel):
    """Job response schema."""
    id: str
    user_id: str
    job_type: str
    status: JobStatus
    input_file: str
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    job_metadata: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """File upload response."""
    file_id: str
    filename: str
    file_type: str
    storage_path: str
    size_bytes: int


class TranscribeRequest(BaseModel):
    """Request to transcribe audio/video."""
    file_id: str
    storage_path: str
    language: Optional[str] = "auto"  # auto-detect or specific language code


class TranslateRequest(BaseModel):
    """Request to translate transcribed text."""
    job_id: str  # ID of the transcription job whose output we translate
    source_language: str = "en"
    target_language: str = "es"


class SynthesizeRequest(BaseModel):
    """Request to synthesize audio from text."""
    job_id: str
    voice_id: Optional[str] = "default"
    speed: Optional[float] = 1.0


class VideoMetadata(BaseModel):
    """Video file metadata."""
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec_name: str
    has_audio: bool
    audio_codec: Optional[str] = None
    bit_rate: str


class VideoUploadResponse(BaseModel):
    """Video file upload response."""
    file_id: str
    filename: str
    storage_path: str
    size_bytes: int
    metadata: VideoMetadata


class VideoTranslateRequest(BaseModel):
    """Request to translate a video."""
    video_file_id: str
    source_language: str = "en"
    target_language: str = "es"
    voice_id: Optional[str] = None  # Optional cloned voice to use

