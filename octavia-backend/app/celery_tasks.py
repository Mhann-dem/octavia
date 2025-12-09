"""Celery configuration and task definitions for Octavia backend."""
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

# Determine if using real Redis or fake Redis for development
USE_FAKE_REDIS = os.environ.get("USE_FAKE_REDIS", "false").lower() == "true"

if USE_FAKE_REDIS:
    # For local development without real Redis server
    import fakeredis
    REDIS_URL = None
    redis_client = fakeredis.FakeStrictRedis()
    BROKER_URL = "memory://"
    RESULT_BACKEND = "cache+memory://"
else:
    # For production or with real Redis server
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

# Initialize Celery
app = Celery(
    "octavia_tasks",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minute hard limit
    task_soft_time_limit=25 * 60,  # 25 minute soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    
    # Define task queues with priorities
    task_queues=(
        # High priority queue for paid/urgent jobs
        Queue(
            "urgent",
            Exchange("urgent", type="direct"),
            routing_key="urgent",
            priority=10,
        ),
        # Normal priority queue (default)
        Queue(
            "default",
            Exchange("default", type="direct"),
            routing_key="default",
            priority=5,
        ),
        # Low priority queue for free tier
        Queue(
            "low",
            Exchange("low", type="direct"),
            routing_key="low",
            priority=1,
        ),
    ),
    
    # Default queue
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Periodic tasks
    beat_schedule={
        "check-stale-jobs": {
            "task": "app.celery_tasks.check_stale_jobs",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "cleanup-completed-jobs": {
            "task": "app.celery_tasks.cleanup_completed_jobs",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
    },
)


# Task definitions
@app.task(bind=True, name="app.celery_tasks.process_transcription")
def process_transcription(self, job_id: str, user_id: str, input_file_path: str, language: str = None, model_size: str = "base"):
    """Async transcription task with progress tracking."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus, JobPhase
    from app import workers
    from datetime import datetime
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}
        
        # Update job status and track start
        job.status = JobStatus.PROCESSING
        job.phase = JobPhase.TRANSCRIBING
        job.current_step = "Initializing transcription"
        job.progress_percentage = 0.0
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Execute transcription
        try:
            # Update progress: 20% - starting transcription
            job.progress_percentage = 20.0
            job.current_step = "Transcribing audio with Whisper"
            db.commit()
            
            success = workers.transcribe_audio(
                session=db,
                job_id=job_id,
                input_file_path=input_file_path,
                language=language,
                model_size=model_size,
            )
            
            if success:
                # Update progress: 100% - completed
                job.status = JobStatus.COMPLETED
                job.phase = JobPhase.COMPLETED
                job.current_step = "Transcription completed"
                job.progress_percentage = 100.0
                db.commit()
                return {"status": "success", "job_id": job_id}
            else:
                job.status = JobStatus.FAILED
                job.phase = JobPhase.FAILED
                job.current_step = "Transcription failed"
                job.error_message = "Transcription failed"
                job.progress_percentage = 0.0
                db.commit()
                return {"status": "error", "message": "Transcription failed"}
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.phase = JobPhase.FAILED
            job.current_step = f"Error: {str(e)}"
            job.error_message = str(e)
            job.progress_percentage = 0.0
            db.commit()
            raise
            
    finally:
        db.close()



@app.task(bind=True, name="app.celery_tasks.process_translation")
def process_translation(self, job_id: str, user_id: str, input_file_path: str, source_lang: str, target_lang: str):
    """Async translation task with progress tracking."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus, JobPhase
    from app import workers
    from datetime import datetime
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}
        
        job.status = JobStatus.PROCESSING
        job.phase = JobPhase.TRANSLATING
        job.current_step = "Initializing translation"
        job.progress_percentage = 0.0
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Update progress: 20% - starting translation
            job.progress_percentage = 20.0
            job.current_step = f"Translating from {source_lang} to {target_lang}"
            db.commit()
            
            success = workers.translate_from_transcription(
                session=db,
                job_id=job_id,
                transcription_file=input_file_path,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            
            if success:
                job.status = JobStatus.COMPLETED
                job.phase = JobPhase.COMPLETED
                job.current_step = "Translation completed"
                job.progress_percentage = 100.0
                db.commit()
                return {"status": "success", "job_id": job_id}
            else:
                job.status = JobStatus.FAILED
                job.phase = JobPhase.FAILED
                job.current_step = "Translation failed"
                job.error_message = "Translation failed"
                job.progress_percentage = 0.0
                db.commit()
                return {"status": "error", "message": "Translation failed"}
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.phase = JobPhase.FAILED
            job.current_step = f"Error: {str(e)}"
            job.error_message = str(e)
            job.progress_percentage = 0.0
            db.commit()
            raise
            
    finally:
        db.close()


@app.task(bind=True, name="app.celery_tasks.process_synthesis")
def process_synthesis(self, job_id: str, user_id: str, input_file_path: str, language: str = "en"):
    """Async synthesis task with progress tracking."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus, JobPhase
    from app import workers
    from datetime import datetime
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}
        
        job.status = JobStatus.PROCESSING
        job.phase = JobPhase.SYNTHESIZING
        job.current_step = "Initializing synthesis"
        job.progress_percentage = 0.0
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Update progress: 20% - starting synthesis
            job.progress_percentage = 20.0
            job.current_step = f"Synthesizing audio in {language}"
            db.commit()
            
            success = workers.synthesize_audio(
                session=db,
                job_id=job_id,
                input_file_path=input_file_path,
                language=language,
            )
            
            if success:
                job.status = JobStatus.COMPLETED
                job.phase = JobPhase.COMPLETED
                job.current_step = "Synthesis completed"
                job.progress_percentage = 100.0
                db.commit()
                return {"status": "success", "job_id": job_id}
            else:
                job.status = JobStatus.FAILED
                job.phase = JobPhase.FAILED
                job.current_step = "Synthesis failed"
                job.error_message = "Synthesis failed"
                job.progress_percentage = 0.0
                db.commit()
                return {"status": "error", "message": "Synthesis failed"}
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.phase = JobPhase.FAILED
            job.current_step = f"Error: {str(e)}"
            job.error_message = str(e)
            job.progress_percentage = 0.0
            db.commit()
            raise
            
    finally:
        db.close()


@app.task(bind=True, name="app.celery_tasks.process_video_translation")
def process_video_translation(self, job_id: str, user_id: str, input_file_path: str, 
                               source_lang: str, target_lang: str, model_size: str = "base"):
    """Async video translation task with progress tracking."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus, JobPhase
    from app import workers
    from datetime import datetime
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}
        
        job.status = JobStatus.PROCESSING
        job.phase = JobPhase.TRANSCRIBING  # Video translation starts with transcription
        job.current_step = "Initializing video translation pipeline"
        job.progress_percentage = 0.0
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Update progress: 15% - starting transcription phase
            job.progress_percentage = 15.0
            job.current_step = f"Transcribing video audio from {source_lang}"
            db.commit()
            
            success = workers.video_translate_pipeline(
                session=db,
                job_id=job_id,
                input_file_path=input_file_path,
                source_language=source_lang,
                target_language=target_lang,
                model_size=model_size,
                enable_dubbing=True,
            )
            
            if success:
                job.status = JobStatus.COMPLETED
                job.phase = JobPhase.COMPLETED
                job.current_step = "Video translation completed"
                job.progress_percentage = 100.0
                db.commit()
                return {"status": "success", "job_id": job_id}
            else:
                job.status = JobStatus.FAILED
                job.phase = JobPhase.FAILED
                job.current_step = "Video translation failed"
                job.error_message = "Video translation failed"
                job.progress_percentage = 0.0
                db.commit()
                return {"status": "error", "message": "Video translation failed"}
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.phase = JobPhase.FAILED
            job.current_step = f"Error: {str(e)}"
            job.error_message = str(e)
            job.progress_percentage = 0.0
            db.commit()
            raise
            
    finally:
        db.close()


@app.task(bind=True, name="app.celery_tasks.check_stale_jobs")
def check_stale_jobs(self):
    """Check for jobs that have been processing too long and fail them."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Find jobs processing for more than 30 minutes
        stale_time = datetime.utcnow() - timedelta(minutes=30)
        stale_jobs = db.query(Job).filter(
            Job.status == JobStatus.PROCESSING,
            Job.created_at < stale_time
        ).all()
        
        for job in stale_jobs:
            job.status = JobStatus.FAILED
            job.error_message = "Job processing timed out after 30 minutes"
        
        db.commit()
        return {"status": "success", "jobs_failed": len(stale_jobs)}
        
    finally:
        db.close()


@app.task(bind=True, name="app.celery_tasks.cleanup_completed_jobs")
def cleanup_completed_jobs(self):
    """Clean up old completed jobs (older than 7 days)."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus
    from datetime import datetime, timedelta
    import os
    
    db = SessionLocal()
    try:
        # Find completed jobs older than 7 days
        old_time = datetime.utcnow() - timedelta(days=7)
        old_jobs = db.query(Job).filter(
            Job.status == JobStatus.COMPLETED,
            Job.completed_at < old_time
        ).all()
        
        deleted_count = 0
        for job in old_jobs:
            # Delete associated files
            if job.output_file:
                try:
                    from app.storage import delete_file
                    delete_file(job.output_file)
                except:
                    pass
            
            # Delete job record
            db.delete(job)
            deleted_count += 1
        
        db.commit()
        return {"status": "success", "jobs_deleted": deleted_count}
        
    finally:
        db.close()


@app.task(name="app.celery_tasks.heartbeat")
def heartbeat():
    """Simple heartbeat task for monitoring."""
    return {"status": "alive", "timestamp": str(__import__('datetime').datetime.utcnow())}


# Error handling
@app.task(bind=True)
def on_failure(self, exc, task_id, args, kwargs, einfo):
    """Handle task failures."""
    from app.core.database import SessionLocal
    from app.job_model import Job, JobStatus
    
    db = SessionLocal()
    try:
        job_id = kwargs.get("job_id") or (args[0] if args else None)
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                db.commit()
    finally:
        db.close()
