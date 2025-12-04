"""Upload and job management endpoints."""
import uuid
import json
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pathlib import Path

from . import db, models, security, upload_schemas, workers
from .storage import save_upload, delete_file
from .job_model import Job, JobStatus

logger = logging.getLogger(__name__)

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


@router.post("/jobs/translate/create", response_model=upload_schemas.JobOut)
def create_translate_job(
    request: upload_schemas.TranslateRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Create a translation job from a transcription output."""
    # Get the transcription job to verify it exists and get its output file
    transcription_job = db_session.query(Job).filter(
        Job.id == request.job_id,
        Job.user_id == user_id,
        Job.job_type == "transcribe"
    ).first()
    
    if not transcription_job:
        raise HTTPException(status_code=404, detail="Transcription job not found")
    
    if transcription_job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transcription job must be completed first")
    
    if not transcription_job.output_file:
        raise HTTPException(status_code=400, detail="Transcription job has no output file")
    
    # Create translation job
    job = Job(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_type="translate",
        input_file=transcription_job.output_file,  # Use transcription output as input
        status=JobStatus.PENDING,
        job_metadata=json.dumps({
            "source_language": request.source_language,
            "target_language": request.target_language,
            "from_job_id": request.job_id
        }),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


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
        input_file=request.storage_path,  # Store full path
        status=JobStatus.PENDING,
        job_metadata=json.dumps({"language": request.language}),
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


@router.post("/jobs/{job_id}/process", response_model=upload_schemas.JobOut)
def process_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Process a job (transcribe, translate, or synthesize).
    Runs synchronously for now.
    """
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Cannot process job with status {job.status}")
    
    try:
        input_file_path = job.input_file  # Storage path from job

        # Try multiple resolution strategies for the stored path and log attempts.
        candidates = []
        # 1) As-is
        candidates.append(Path(input_file_path))
        # 2) Relative to cwd
        candidates.append(Path.cwd() / input_file_path)
        # 3) Under cwd/uploads/<input_file_path>
        candidates.append(Path.cwd() / 'uploads' / input_file_path)
        # 4) If input already begins with 'uploads/', join directly
        if str(input_file_path).replace('\\', '/').startswith('uploads/'):
            candidates.append(Path.cwd() / Path(input_file_path.replace('/', '\\')))
        
        resolved_path = None
        for cand in candidates:
            try_path = cand if isinstance(cand, Path) else Path(cand)
            logger.debug(f"Job {job_id}: checking path candidate: {try_path}")
            if try_path.exists():
                resolved_path = try_path
                break
        
        if resolved_path is None:
            # Provide diagnostic message listing candidates
            cand_list = ", ".join([str(c) for c in candidates])
            logger.error(f"Job {job_id}: none of the path candidates exist: {cand_list}")
            raise HTTPException(status_code=400, detail=f"Input file not found: {input_file_path}")

        input_file_path = str(resolved_path)
        logger.info(f"Job {job_id}: resolved input file path: {input_file_path}")

        
        # Process based on job type
        if job.job_type == "transcribe":
            logger.info(f"Processing transcription job {job_id} from {input_file_path}")
            metadata = json.loads(job.job_metadata) if job.job_metadata else {}
            language = metadata.get("language")
            if language == "auto":
                language = None
            model_size = metadata.get("model_size", "base")
            
            success = workers.transcribe_audio(
                session=db_session,
                job_id=job_id,
                input_file_path=input_file_path,
                language=language,
                model_size=model_size
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Transcription processing failed")
        
        elif job.job_type == "translate":
            logger.info(f"Processing translation job {job_id}")
            metadata = json.loads(job.job_metadata) if job.job_metadata else {}
            source_lang = metadata.get("source_language", "en")
            target_lang = metadata.get("target_language", "es")
            
            success = workers.translate_from_transcription(
                session=db_session,
                job_id=job_id,
                transcription_file=input_file_path,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Translation processing failed")
        
        elif job.job_type == "synthesize":
            # TODO: Implement synthesis worker
            raise HTTPException(status_code=501, detail="Synthesis not yet implemented")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job.job_type}")
        
        # Refresh job to get updated status and output_file
        db_session.refresh(job)
        return job
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        db_session.commit()
        raise HTTPException(status_code=500, detail=f"Error processing job: {str(e)}")


@router.get("/jobs", response_model=list[upload_schemas.JobOut])
def list_jobs(
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    db_session: Session = Depends(db.get_db),
):
    """List all jobs for the current user."""
    jobs = db_session.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(limit).all()
    return jobs
