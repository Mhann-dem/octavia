# Video Translation - Quick Start Guide

## What Was Implemented

A complete video translation workflow connecting frontend (Next.js) with backend (FastAPI + Celery).

## How to Use

### 1. Start the Backend Services

In terminal 1 (Backend API):
```bash
cd octavia-backend
python -m uvicorn app.main:app --reload --port 8001
```

In terminal 2 (Celery Worker):
```bash
cd octavia-backend
USE_FAKE_REDIS=true python -m celery -A app.celery_tasks worker --loglevel=info
```

In terminal 3 (Optional - Celery Beat for scheduled tasks):
```bash
cd octavia-backend
USE_FAKE_REDIS=true python -m celery -A app.celery_tasks beat --loglevel=info
```

### 2. Start the Frontend

In terminal 4:
```bash
cd octavia-web
npm run dev
```

### 3. Use the Application

1. Navigate to `http://localhost:3000`
2. Create an account at `/signup`
3. Login with your credentials at `/login`
4. Go to Dashboard → Video Translation
5. Upload a video file or paste a URL
6. Select source and target languages
7. Click "Start Translation"
8. Monitor progress on the progress page

## API Endpoints

### Upload Video File
```bash
curl -X POST "http://127.0.0.1:8001/api/v1/upload?file_type=video" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/video.mp4"
```

Response:
```json
{
  "file_id": "abc123",
  "filename": "video.mp4",
  "file_type": "video",
  "storage_path": "uploads/user123/video/abc123_video.mp4",
  "size_bytes": 5242880
}
```

### Create Translation Job
```bash
curl -X POST "http://127.0.0.1:8001/api/v1/jobs/video-translate/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "abc123",
    "storage_path": "uploads/user123/video/abc123_video.mp4",
    "source_language": "en",
    "target_language": "es",
    "model_size": "base"
  }'
```

Response:
```json
{
  "id": "job-uuid",
  "user_id": "user123",
  "job_type": "video_translate",
  "status": "pending",
  "input_file": "uploads/user123/video/abc123_video.mp4",
  "output_file": null,
  "created_at": "2025-12-08T10:30:00",
  "completed_at": null
}
```

### Queue Job for Processing
```bash
curl -X POST "http://127.0.0.1:8001/api/v1/jobs/job-uuid/process" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Job Status
```bash
curl -X GET "http://127.0.0.1:8001/api/v1/jobs/job-uuid" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "id": "job-uuid",
  "user_id": "user123",
  "job_type": "video_translate",
  "status": "processing",
  "input_file": "uploads/user123/video/abc123_video.mp4",
  "phase": "TRANSLATING",
  "progress_percentage": 45.5,
  "current_step": "Translating dialogue...",
  "started_at": "2025-12-08T10:31:00",
  "completed_at": null
}
```

## Testing

Run the automated test script:
```bash
python octavia-backend/scripts/test_video_translation.py --email test@example.com --video-path test.mp4
```

This will:
1. Create a test user (if doesn't exist)
2. Upload a video
3. Create a translation job
4. Queue it for processing
5. Poll status until completion
6. Print the job URL for frontend monitoring

## File Structure

```
octavia-backend/
├── app/
│   ├── upload_routes.py      # Upload & job creation endpoints
│   ├── sse_routes.py         # Progress streaming endpoints
│   ├── celery_tasks.py       # Background task definitions
│   ├── job_model.py          # Job database model
│   ├── workers.py            # Processing logic (transcribe, translate, synthesize)
│   └── upload_schemas.py     # Request/response schemas
├── scripts/
│   └── test_video_translation.py  # Testing script
└── docs/
    └── VIDEO_TRANSLATION_WORKFLOW.md  # Detailed documentation

octavia-web/
├── app/
│   └── dashboard/
│       └── video/
│           ├── page.tsx           # Video upload page
│           └── progress/
│               └── page.tsx       # Progress monitoring page
└── lib/
    ├── auth.ts              # Authentication utilities
    ├── withAuth.tsx         # Auth protection wrapper
    └── utils.ts             # Helper functions
```

## Environment Variables

### Backend (.env or exported)
```bash
NEXT_PUBLIC_APP_URL=http://localhost:3000
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
DATABASE_URL=sqlite:///./dev.db
USE_FAKE_REDIS=true
CELERY_BROKER_URL=memory://
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## Key Files Changed

### Backend
- `app/upload_schemas.py`: Added `VideoTranslateRequest` schema
- `app/upload_routes.py`: Added `/jobs/video-translate/create` endpoint
- `app/celery_tasks.py`: `process_video_translation` task (already exists)

### Frontend
- `app/dashboard/video/page.tsx`: Implemented file upload, URL paste, language selection
- `app/dashboard/video/progress/page.tsx`: Implemented real-time progress monitoring

## Workflow Summary

1. User uploads video → `/api/v1/upload` → returns `storage_path`
2. Frontend creates job → `/api/v1/jobs/video-translate/create` → returns `job_id`
3. Frontend queues job → `/api/v1/jobs/{job_id}/process` → Celery starts task
4. Celery worker processes video (transcribe → translate → synthesize → assemble)
5. Frontend polls `/api/v1/jobs/{job_id}` every 2 seconds for progress
6. When complete, user can download translated video

## Debugging

### Check Celery Task Status
```bash
# In Python shell
from app.core.database import SessionLocal
from app.job_model import Job

db = SessionLocal()
job = db.query(Job).filter(Job.id == "job-uuid").first()
print(f"Status: {job.status}")
print(f"Progress: {job.progress_percentage}%")
print(f"Phase: {job.phase}")
print(f"Step: {job.current_step}")
print(f"Error: {job.error_message}")
```

### Check Celery Worker Logs
```bash
# Look for task execution logs in terminal running Celery
# Should see: [tasks] process_video_translation[job-id] ...
```

### Check Frontend Network Requests
1. Open browser DevTools (F12)
2. Go to Network tab
3. Watch `/api/v1/jobs/...` requests
4. Check for 200 status and valid response data

## Common Issues & Solutions

### "Celery task not processing"
- **Cause**: Worker not running
- **Fix**: Start Celery worker with `USE_FAKE_REDIS=true python -m celery -A app.celery_tasks worker`

### "File not found" error
- **Cause**: Upload path not correct
- **Fix**: Check storage directory exists and has write permissions

### "Progress stuck at 0%"
- **Cause**: Task not started or worker crashed
- **Fix**: Check worker logs for errors, restart worker

### "Download endpoint returns 404"
- **Cause**: Output file not created
- **Fix**: Check if job actually completed (status = "completed"), check worker logs

## Next Steps

1. **Test with real videos**: Upload actual MP4 files to test quality
2. **Monitor performance**: Track processing times for different video sizes
3. **Add voice cloning**: Enable speaker voice preservation
4. **Implement caching**: Cache translated segments for faster re-processing
5. **Add quality presets**: Let users choose speed vs quality
6. **WebSocket updates**: Replace polling with real-time WebSocket progress
