# Async Job Queue Implementation Plan

## Current State

The media processing pipeline currently uses **synchronous endpoints** in `POST /api/v1/jobs/{job_id}/process`:
- Request blocks until job completes
- Transcription: ~5-10 seconds
- Translation: ~5-15 seconds
- Synthesis: ~5-30 seconds
- **Total**: 15-55 seconds per full pipeline

This works for testing but isn't production-ready:
- Long-running requests timeout (30s default in most cloud platforms)
- Client connections break on network issues
- No ability to scale processing (single server handles all work)
- No persistence if worker crashes mid-job

## Recommended Solution: Celery + Redis

### Why Celery?

**Pros:**
- Industry standard for Django/FastAPI async tasks
- Distributed workers across multiple servers
- Automatic retry on failure
- Task scheduling support
- Result persistence
- Progress tracking

**Cons:**
- Requires Redis or RabbitMQ
- Added infrastructure complexity
- Learning curve

### Why not RQ (Redis Queue)?

RQ is simpler but Celery is more mature for media processing:
- RQ: Good for simple fire-and-forget tasks
- Celery: Better for complex workflows with retries, chains, and monitoring

## Implementation Steps

### Step 1: Install Dependencies

```bash
pip install celery redis
```

Add to `requirements-core.txt`:
```
celery>=5.3.0
redis>=4.5.0
```

### Step 2: Set Up Redis

**Local Development:**
```bash
# Windows (WSL or Docker)
docker run -p 6379:6379 redis:latest

# Or via package manager
# Ubuntu: sudo apt-get install redis-server
# macOS: brew install redis
```

**Production:**
- Use managed Redis (AWS ElastiCache, Azure Cache, etc.)
- Set connection string in environment: `REDIS_URL=redis://user:password@host:port/db`

### Step 3: Create Celery App

Create `app/celery_app.py`:
```python
import os
from celery import Celery
from kombu import Exchange, Queue

celery_app = Celery(__name__)

# Configure Redis broker and result backend
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery_app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Task time limits (prevent hung workers)
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,        # 10 minutes hard limit
    # Result expiration
    result_expires=3600,        # Results persist 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Define task queues for priority handling
celery_app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('transcribe', Exchange('transcribe'), routing_key='transcribe.#'),
    Queue('translate', Exchange('translate'), routing_key='translate.#'),
    Queue('synthesize', Exchange('synthesize'), routing_key='synthesize.#'),
)

# Task routing
celery_app.conf.task_routes = {
    'app.tasks.transcribe_audio_task': {'queue': 'transcribe'},
    'app.tasks.translate_task': {'queue': 'translate'},
    'app.tasks.synthesize_task': {'queue': 'synthesize'},
}
```

### Step 4: Create Tasks

Create `app/tasks.py`:
```python
from celery import shared_task
from sqlalchemy.orm import Session
from . import workers, db
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def transcribe_audio_task(self, job_id, user_id):
    """Async transcription task with retry logic"""
    session = db.SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        result = workers.transcribe_audio(
            session=session,
            job_id=job_id,
            input_file_path=job.input_file,
            language=json.loads(job.job_metadata).get("language")
        )
        
        if not result:
            raise Exception("Transcription worker returned False")
        
        return {"status": "success", "job_id": job_id}
    except Exception as exc:
        logger.error(f"Task transcribe_audio_task failed: {exc}", exc_info=True)
        # Retry with exponential backoff: 60s, 180s, 600s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        session.close()

@shared_task(bind=True, max_retries=3)
def translate_task(self, job_id, user_id):
    """Async translation task"""
    session = db.SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        metadata = json.loads(job.job_metadata)
        result = workers.translate_from_transcription(
            session=session,
            job_id=job_id,
            transcription_file=job.input_file,
            source_lang=metadata.get("source_language", "en"),
            target_lang=metadata.get("target_language", "es")
        )
        
        if not result:
            raise Exception("Translation worker returned False")
        
        return {"status": "success", "job_id": job_id}
    except Exception as exc:
        logger.error(f"Task translate_task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        session.close()

@shared_task(bind=True, max_retries=3)
def synthesize_task(self, job_id, user_id):
    """Async synthesis task"""
    session = db.SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        metadata = json.loads(job.job_metadata)
        result = workers.synthesize_audio(
            session=session,
            job_id=job_id,
            input_file_path=job.input_file,
            language=metadata.get("language", "en")
        )
        
        if not result:
            raise Exception("Synthesis worker returned False")
        
        return {"status": "success", "job_id": job_id}
    except Exception as exc:
        logger.error(f"Task synthesize_task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        session.close()
```

### Step 5: Update Endpoints

Modify `app/upload_routes.py`:
```python
from .tasks import transcribe_audio_task, translate_task, synthesize_task

@router.post("/jobs/{job_id}/process", response_model=upload_schemas.JobOut)
def process_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """
    Queue a job for processing.
    Returns immediately with job status = 'pending'.
    Actual processing happens asynchronously.
    """
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Cannot process job with status {job.status}")
    
    # Update job status
    job.status = JobStatus.PROCESSING
    db_session.commit()
    
    # Queue task based on job type
    if job.job_type == "transcribe":
        transcribe_audio_task.apply_async(
            args=[job_id, user_id],
            task_id=f"{job_id}",  # Link task to job ID
            queue="transcribe"
        )
    elif job.job_type == "translate":
        translate_task.apply_async(
            args=[job_id, user_id],
            task_id=f"{job_id}",
            queue="translate"
        )
    elif job.job_type == "synthesize":
        synthesize_task.apply_async(
            args=[job_id, user_id],
            task_id=f"{job_id}",
            queue="synthesize"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown job type: {job.job_type}")
    
    # Return job with status = PROCESSING
    db_session.refresh(job)
    return job
```

### Step 6: Update Job Status Tracking

Add a new endpoint to check job progress:
```python
@router.get("/jobs/{job_id}/status", response_model=upload_schemas.JobOut)
def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Get current job status and progress."""
    job = db_session.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If processing, check Celery task state
    if job.status == JobStatus.PROCESSING:
        from celery.result import AsyncResult
        from .celery_app import celery_app
        
        task_result = AsyncResult(job_id, app=celery_app)
        # Optionally update DB based on task state
        # (in production, use Celery signals for this)
    
    return job
```

### Step 7: Start Workers

**Development:**
```bash
# Terminal 1: Start Celery worker for all queues
celery -A app.celery_app worker -l info --queues default,transcribe,translate,synthesize

# Terminal 2: Start FastAPI
uvicorn app.main:app --reload

# Terminal 3 (optional): Monitor tasks
celery -A app.celery_app events
```

**Production (Supervisor/systemd):**

Create `/etc/systemd/system/celery.service`:
```ini
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/octavia
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/octavia/venv/bin/celery -A app.celery_app worker -l info

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable celery
sudo systemctl start celery
```

## Monitoring & Observability

### Option 1: Flower (Celery Monitoring UI)

```bash
pip install flower
celery -A app.celery_app flower
# Access at http://localhost:5555
```

### Option 2: Prometheus + Grafana

Export Celery metrics:
```bash
pip install prometheus-client
```

### Option 3: Simple Logging

Already implemented in tasks — check logs for progress.

## Migration Path

1. **Phase 1**: Deploy async tasks alongside current sync endpoints
   - Keep `/process` synchronous for backward compatibility
   - Add new `/process-async` endpoint that queues tasks

2. **Phase 2**: Update clients to use async endpoints
   - Clients poll `/jobs/{job_id}` for status
   - Optionally add WebSocket for live updates

3. **Phase 3**: Deprecate sync endpoints
   - Remove `/process` endpoint
   - All processing goes through async queue

## Cost/Complexity Trade-offs

| Component | Complexity | Cost | Time |
|-----------|-----------|------|------|
| Redis | Low | $5-20/mo managed | 1-2 days |
| Celery integration | Medium | Free | 2-3 days |
| Monitoring (Flower) | Low | Free | 1 day |
| Worker scaling | Medium | $5-50/mo extra servers | 1-2 days |
| **Total** | **Medium** | **$15-70/mo** | **5-8 days** |

## When to Implement

**Implement async queue when:**
- Processing pipeline exceeds 10 seconds consistently
- Users report timeout errors
- You want to scale to multiple servers
- You need job persistence/recovery

**Not needed if:**
- Processing stays under 5 seconds
- Running on single server
- Can tolerate occasional timeouts

## Testing Async Tasks

```python
# test_async_tasks.py
from app.tasks import transcribe_audio_task
from celery import current_app

def test_transcribe_task(celery_app):
    # Use eager mode for testing (executes synchronously)
    celery_app.conf.update(task_always_eager=True)
    
    result = transcribe_audio_task.apply_async(
        args=["test-job-id", "test-user-id"]
    )
    
    assert result.status == 'SUCCESS'
    assert result.result['status'] == 'success'
```

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [FastAPI + Celery](https://fastapi.tiangolo.com/en/deployment/concepts/#tasks)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/bestpractices.html)
