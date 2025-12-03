"""Upload and job management endpoints."""
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from . import db, models, security, upload_schemas
from .storage import save_upload, delete_file
from .job_model import Job, JobStatus

router = APIRouter(prefix="/api/v1", tags=["uploads"])


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


@router.post("/upload", response_model=upload_schemas.UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Query(...),  # 'video', 'audio', 'subtitle'
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Upload a media file for processing."""
    # Validate file type
    if file_type not in ("video", "audio", "subtitle"):
        raise HTTPException(status_code=400, detail="Invalid file_type. Must be video, audio, or subtitle")
    
    # Read file
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Check file size (max 500MB)
    if len(contents) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 500MB)")
    
    # Save to storage
    file_id = str(uuid.uuid4())
    storage_path = save_upload(user_id, file_type, contents, f"{file_id}_{file.filename}")
    
    return upload_schemas.UploadResponse(
        file_id=file_id,
        filename=file.filename,
        file_type=file_type,
        storage_path=storage_path,
        size_bytes=len(contents),
    )


@router.post("/jobs/transcribe", response_model=upload_schemas.JobOut)
def create_transcribe_job(
    request: upload_schemas.TranscribeRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Create a transcription job."""
    job = Job(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_type="transcribe",
        input_file=request.file_id,
        status=JobStatus.PENDING,
        metadata=json.dumps({"language": request.language}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@router.get("/jobs/{job_id}", response_model=upload_schemas.JobOut)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Get job status."""
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs", response_model=list[upload_schemas.JobOut])
def list_jobs(
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    db_session: Session = Depends(db.get_db),
):
    """List all jobs for the current user."""
    jobs = db_session.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(limit).all()
    return jobs
