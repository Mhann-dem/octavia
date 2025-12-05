"""Video translation endpoints for Octavia."""
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
from pydantic import BaseModel

from . import db, security
from .job_model import Job, JobStatus
from .video_processor import VideoProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/video", tags=["video"])


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user ID from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = security.get_bearer_token(authorization)
    payload = security.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user_id


class VideoTranslateRequest(BaseModel):
    """Request to translate a video."""
    storage_path: str
    source_language: str = "auto"
    target_language: str = "es"
    model_size: str = "base"  # Whisper model size


class VideoTranslateResponse(BaseModel):
    """Response from video translation job creation."""
    job_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[float] = None


@router.post("/translate", response_model=VideoTranslateResponse)
async def create_video_translation_job(
    request: VideoTranslateRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Create a video translation job that will:
    1. Extract audio from video
    2. Transcribe audio to text
    3. Translate text to target language
    4. Synthesize new audio from translated text
    5. Merge new audio back into video
    
    Returns a job ID that can be used to check status and download result.
    """
    try:
        # Resolve the storage path
        storage_path = Path(request.storage_path)
        if not storage_path.is_absolute():
            # Try common locations
            candidates = [
                storage_path,
                Path.cwd() / storage_path,
                Path.cwd() / 'uploads' / storage_path,
            ]
            
            resolved = None
            for candidate in candidates:
                if candidate.exists():
                    resolved = candidate
                    break
            
            if not resolved:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Video file not found at {request.storage_path}"
                )
            storage_path = resolved
        
        # Validate video file
        processor = VideoProcessor()
        if not processor.validate_video_file(str(storage_path)):
            raise HTTPException(status_code=400, detail="Invalid video file")
        
        # Get video metadata for time estimation
        metadata = processor.get_video_metadata(str(storage_path))
        if not metadata:
            raise HTTPException(status_code=400, detail="Could not read video metadata")
        
        duration = metadata.get('duration', 0)
        
        # Estimate processing time (rough estimate: 2x video duration + overhead)
        estimated_time = (duration * 2) + 30
        
        logger.info(f"Creating video translation job for {storage_path}")
        logger.info(f"Video duration: {duration}s, estimated processing: {estimated_time}s")
        
        # Create video translation job
        job = Job(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_type="video_translate",
            input_file=str(storage_path),
            status=JobStatus.PENDING,
            job_metadata=json.dumps({
                "source_language": request.source_language,
                "target_language": request.target_language,
                "model_size": request.model_size,
                "video_duration": duration,
                "video_metadata": metadata
            }),
        )
        
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        return VideoTranslateResponse(
            job_id=job.id,
            status="pending",
            message="Video translation job created. Use /api/v1/jobs/{job_id}/process to start processing.",
            estimated_time_seconds=estimated_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating video translation job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")


@router.get("/validate")
async def validate_video_file(
    storage_path: str,
    user_id: str = Depends(get_current_user),
):
    """
    Validate that a video file exists and is processable.
    Returns video metadata if valid.
    """
    try:
        # Resolve storage path
        path = Path(storage_path)
        if not path.is_absolute():
            candidates = [
                path,
                Path.cwd() / path,
                Path.cwd() / 'uploads' / path,
            ]
            
            resolved = None
            for candidate in candidates:
                if candidate.exists():
                    resolved = candidate
                    break
            
            if not resolved:
                raise HTTPException(status_code=404, detail="Video file not found")
            path = resolved
        
        processor = VideoProcessor()
        
        # Validate
        if not processor.validate_video_file(str(path)):
            raise HTTPException(status_code=400, detail="Invalid video file")
        
        # Get metadata
        metadata = processor.get_video_metadata(str(path))
        if not metadata:
            raise HTTPException(status_code=400, detail="Could not read video metadata")
        
        return {
            "valid": True,
            "path": str(path),
            "metadata": metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")