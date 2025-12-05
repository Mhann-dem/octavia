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
from .credit_calculator import CreditCalculator
from .billing_routes import deduct_credits

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


@router.post("/jobs/synthesize/create", response_model=upload_schemas.JobOut)
def create_synthesize_job(
    request: upload_schemas.SynthesizeRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Create a synthesis job from a translation output."""
    # Get the translation job to verify it exists and get its output file
    translation_job = db_session.query(Job).filter(
        Job.id == request.job_id,
        Job.user_id == user_id,
        Job.job_type == "translate"
    ).first()
    
    if not translation_job:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if translation_job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Translation job must be completed first")
    
    if not translation_job.output_file:
        raise HTTPException(status_code=400, detail="Translation job has no output file")
    
    # Create synthesis job
    job = Job(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_type="synthesize",
        input_file=translation_job.output_file,  # Use translation output as input
        status=JobStatus.PENDING,
        job_metadata=json.dumps({
            "voice_id": request.voice_id,
            "speed": request.speed,
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


"""
Updated process_job endpoint to handle video translation jobs.
Add this to the existing upload_routes.py process_job function.
"""

@router.post("/jobs/{job_id}/process", response_model=upload_schemas.JobOut)
def process_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Process a job (transcribe, translate, synthesize, or video_translate).
    Validates credits before processing and deducts them on completion.
    Runs synchronously for now.
    """
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Cannot process job with status {job.status}")
    
    # Get user for credit validation
    user = db_session.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        input_file_path = job.input_file
        
        # Resolve file path with multiple strategies
        candidates = []
        candidates.append(Path(input_file_path))
        candidates.append(Path.cwd() / input_file_path)
        candidates.append(Path.cwd() / 'uploads' / input_file_path)
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
            cand_list = ", ".join([str(c) for c in candidates])
            logger.error(f"Job {job_id}: none of the path candidates exist: {cand_list}")
            raise HTTPException(status_code=400, detail=f"Input file not found: {input_file_path}")

        input_file_path = str(resolved_path)
        logger.info(f"Job {job_id}: resolved input file path: {input_file_path}")
        
        # STEP 1: Calculate credit cost
        calculator = CreditCalculator()
        credit_cost = calculator.calculate_credits(
            job_type=job.job_type,
            input_file_path=input_file_path
        )
        
        logger.info(f"Job {job_id}: Estimated cost: {credit_cost} credits")
        
        # STEP 2: Validate sufficient credits
        if user.credits < credit_cost:
            error_msg = f"Insufficient credits. Required: {credit_cost}, Available: {user.credits}"
            logger.warning(f"Job {job_id}: {error_msg}")
            raise HTTPException(
                status_code=402,  # Payment Required
                detail=error_msg
            )
        
        logger.info(f"Job {job_id}: User has sufficient credits ({user.credits} >= {credit_cost})")
        
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
            logger.info(f"Processing synthesis job {job_id}")
            metadata = json.loads(job.job_metadata) if job.job_metadata else {}
            language = metadata.get("language", "en")
            
            success = workers.synthesize_audio(
                session=db_session,
                job_id=job_id,
                input_file_path=input_file_path,
                language=language
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Synthesis processing failed")
        
        elif job.job_type == "video_translate":
            logger.info(f"Processing video translation job {job_id}")
            metadata = json.loads(job.job_metadata) if job.job_metadata else {}
            source_lang = metadata.get("source_language", "auto")
            target_lang = metadata.get("target_language", "es")
            model_size = metadata.get("model_size", "base")
            
            success = workers.video_translate_pipeline(
                session=db_session,
                job_id=job_id,
                input_file_path=input_file_path,
                source_language=source_lang,
                target_language=target_lang,
                model_size=model_size,
                enable_dubbing=True
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Video translation processing failed")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job.job_type}")
        
        # STEP 3: Deduct credits on successful completion
        if job.status == JobStatus.COMPLETED:
            logger.info(f"Job {job_id}: Deducting {credit_cost} credits")
            success = deduct_credits(
                session=db_session,
                user_id=user_id,
                job_id=job_id,
                job_type=job.job_type,
                credits=credit_cost,
                reason=f"{job.job_type} job completed"
            )
            
            if not success:
                logger.error(f"Job {job_id}: Failed to deduct credits, but job completed")
                # Don't fail the job if credit deduction fails - job is already done
        
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


@router.post("/estimate", response_model=upload_schemas.CreditEstimate)
def estimate_credits(
    request: upload_schemas.EstimateRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Estimate credit cost for a job before processing."""
    try:
        credit_cost = CreditCalculator.calculate_credits(
            job_type=request.job_type,
            input_file_path=request.input_file_path,
            duration_override=request.duration_override,
        )
        
        # Get user current balance
        user = db_session.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_balance = user.credits if user.credits is not None else 0
        
        return upload_schemas.CreditEstimate(
            job_type=request.job_type,
            estimated_credits=credit_cost,
            current_balance=current_balance,
            sufficient_balance=current_balance >= credit_cost,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"File not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error estimating credits: {str(e)}")


@router.get("/jobs", response_model=list[upload_schemas.JobOut])
def list_jobs(
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    db_session: Session = Depends(db.get_db),
):
    """List all jobs for the current user."""
    jobs = db_session.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(limit).all()
    return jobs
