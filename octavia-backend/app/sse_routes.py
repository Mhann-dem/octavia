"""Server-Sent Events (SSE) endpoint for real-time job progress updates."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import get_db
from app.job_model import Job, JobStatus
from app.upload_routes import get_current_user

router = APIRouter()


async def job_progress_stream(job_id: str, user_id: str, db_session: Session):
    """Stream job progress updates as Server-Sent Events."""
    last_status = None
    last_progress = None
    last_update = datetime.now()
    check_interval = 0.5  # Check every 500ms
    
    while True:
        try:
            # Get current job status
            job = db_session.query(Job).filter(
                Job.id == job_id,
                Job.user_id == user_id
            ).first()
            
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            
            # Prepare status data with progress tracking
            status_data = {
                "job_id": job.id,
                "status": job.status,
                "job_type": job.job_type,
                "phase": job.phase if hasattr(job, 'phase') else None,
                "progress_percentage": job.progress_percentage if hasattr(job, 'progress_percentage') else 0.0,
                "current_step": job.current_step if hasattr(job, 'current_step') else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "output_file": job.output_file,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Only send update if status/progress changed or on first message
            progress_changed = (last_progress is not None and 
                              status_data.get("progress_percentage") != last_progress)
            
            if job.status != last_status or progress_changed or (datetime.now() - last_update).total_seconds() >= 1:
                yield f"data: {json.dumps(status_data)}\n\n"
                last_status = job.status
                last_progress = status_data.get("progress_percentage")
                last_update = datetime.now()
            
            # Stop streaming if job is done
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                yield f"event: done\ndata: {json.dumps(status_data)}\n\n"
                break
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
            break
    
    db_session.close()


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """
    Stream real-time job progress via Server-Sent Events (SSE).
    
    Usage in JavaScript:
    ```javascript
    const eventSource = new EventSource(`/api/v1/jobs/${jobId}/stream`);
    
    eventSource.onmessage = (event) => {
        const jobStatus = JSON.parse(event.data);
        console.log('Job status:', jobStatus);
        
        if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
            eventSource.close();
        }
    };
    
    eventSource.addEventListener('done', (event) => {
        console.log('Job finished');
        eventSource.close();
    });
    ```
    """
    # Verify job exists and belongs to user
    job = db_session.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StreamingResponse(
        job_progress_stream(job_id, user_id, db_session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        }
    )


@router.get("/jobs/{job_id}/status")
def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    """
    Get current job status (non-streaming alternative to SSE).
    Useful for polling or fetching current state without persistent connection.
    Returns progress information including phase, percentage, and current step.
    """
    job = db_session.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.status,
        "job_type": job.job_type,
        "phase": job.phase if hasattr(job, 'phase') else None,
        "progress_percentage": job.progress_percentage if hasattr(job, 'progress_percentage') else 0.0,
        "current_step": job.current_step if hasattr(job, 'current_step') else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "output_file": job.output_file,
        "credit_cost": job.credit_cost,
        "input_file": job.input_file,
        "job_metadata": job.job_metadata,
    }
