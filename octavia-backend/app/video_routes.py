"""Video translation endpoints and handlers."""
import uuid
import json
import logging
import subprocess
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pathlib import Path

from . import db, security, upload_schemas, workers
from .storage import save_upload, get_file_local
from .job_model import Job, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user ID from JWT token in Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    payload = security.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user_id


def get_video_metadata(video_path: str) -> dict:
    """
    Extract video metadata using FFmpeg.
    Returns: {duration_seconds, width, height, fps, codec_name, bit_rate}
    """
    try:
        # Use ffprobe to get metadata
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error(f"FFprobe failed: {result.stderr}")
            raise HTTPException(status_code=400, detail="Failed to extract video metadata")
        
        data = json.loads(result.stdout)
        
        # Extract video stream info
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            {}
        )
        format_info = data.get("format", {})
        
        metadata = {
            "duration_seconds": float(format_info.get("duration", 0)),
            "width": video_stream.get("width", 0),
            "height": video_stream.get("height", 0),
            "fps": video_stream.get("r_frame_rate", "0/1").split("/"),
            "codec_name": video_stream.get("codec_name", "unknown"),
            "has_audio": bool(audio_stream),
            "audio_codec": audio_stream.get("codec_name", "unknown") if audio_stream else None,
            "bit_rate": format_info.get("bit_rate", "0"),
        }
        
        # Parse FPS
        if metadata["fps"][0] and metadata["fps"][1]:
            try:
                metadata["fps"] = float(metadata["fps"][0]) / float(metadata["fps"][1])
            except:
                metadata["fps"] = 0
        
        return metadata
    except subprocess.TimeoutExpired:
        logger.error("FFprobe timed out")
        raise HTTPException(status_code=400, detail="Video analysis timeout")
    except Exception as e:
        logger.error(f"Error extracting video metadata: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract video metadata: {str(e)}")


@router.post("/videos/upload", response_model=upload_schemas.VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Upload a video file and extract metadata.
    
    Returns:
    - file_id: Unique identifier for this upload
    - filename: Original filename
    - storage_path: Path where video is stored
    - size_bytes: File size in bytes
    - metadata: Video metadata (duration, dimensions, codecs, etc.)
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    # Check file extension
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format. Supported: {', '.join(valid_extensions)}"
        )
    
    # Read file
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Check file size (max 5GB for videos)
    max_size = 5 * 1024 * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 5GB)")
    
    # Save to storage
    file_id = str(uuid.uuid4())
    storage_path = save_upload(user_id, "video", contents, f"{file_id}_{file.filename}")
    
    # Extract metadata
    metadata = get_video_metadata(storage_path)
    
    return upload_schemas.VideoUploadResponse(
        file_id=file_id,
        filename=file.filename,
        storage_path=storage_path,
        size_bytes=len(contents),
        metadata=metadata,
    )


@router.post("/jobs/video-translate/create", response_model=upload_schemas.JobOut)
def create_video_translate_job(
    request: upload_schemas.VideoTranslateRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Create a video translation job.
    
    This will:
    1. Extract audio from video using FFmpeg
    2. Transcribe audio using Whisper
    3. Translate text using Helsinki NLP
    4. Synthesize translated audio using Coqui XTTS
    5. Reassemble video with new audio
    
    Request body:
    {
        "video_file_id": "uuid-from-upload",
        "source_language": "en",
        "target_language": "es",
        "voice_id": "optional-cloned-voice-uuid"
    }
    """
    # Verify file exists
    try:
        storage_path = Path(f"uploads/users/{user_id}/video/{request.video_file_id}*")
        matching_files = list(Path("uploads/users").glob(f"{user_id}/video/{request.video_file_id}*"))
        if not matching_files:
            raise HTTPException(status_code=404, detail="Video file not found")
        
        video_path = str(matching_files[0])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Video file not found: {str(e)}")
    
    # Verify video can be read
    if not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not accessible")
    
    # Create job with metadata
    job = Job(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_type="video-translate",
        status=JobStatus.PENDING,
        input_file=video_path,
        output_file=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        job_metadata=json.dumps({
            "source_language": request.source_language,
            "target_language": request.target_language,
            "voice_id": request.voice_id,
            "video_file_id": request.video_file_id,
        })
    )
    
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    logger.info(f"Created video-translate job {job.id} for user {user_id}")
    
    return upload_schemas.JobOut(
        id=job.id,
        user_id=job.user_id,
        job_type=job.job_type,
        status=job.status,
        input_file=job.input_file,
        output_file=job.output_file,
        created_at=job.created_at,
        updated_at=job.updated_at,
        job_metadata=job.job_metadata,
    )


@router.post("/jobs/{job_id}/extract-audio", response_model=upload_schemas.JobOut)
def extract_audio_from_video(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Extract audio from video and create a transcription job.
    Returns the transcription job ID for chaining.
    """
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.job_type != "video-translate":
        raise HTTPException(status_code=400, detail="Job must be video-translate type")
    
    if job.status != JobStatus.PENDING:
        raise HTTPException(status_code=400, detail="Job must be in pending state")
    
    # Extract audio
    success = workers.extract_audio_from_video(
        session=db_session,
        job_id=job_id,
        video_path=job.input_file
    )
    
    if not success:
        job.status = JobStatus.FAILED
        db_session.commit()
        raise HTTPException(status_code=500, detail="Failed to extract audio from video")
    
    # Get updated job
    db_session.refresh(job)
    
    return upload_schemas.JobOut(
        id=job.id,
        user_id=job.user_id,
        job_type=job.job_type,
        status=job.status,
        input_file=job.input_file,
        output_file=job.output_file,
        created_at=job.created_at,
        updated_at=job.updated_at,
        job_metadata=job.job_metadata,
    )
