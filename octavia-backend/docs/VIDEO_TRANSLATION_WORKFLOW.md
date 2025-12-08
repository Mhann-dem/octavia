# Video Translation Workflow - Implementation Summary

## Overview
The video translation feature allows users to upload videos, select source and target languages, and have them translated with dubbed audio in real-time. The system is fully integrated between frontend and backend.

## Workflow Steps

### 1. Frontend (octavia-web)

#### Video Upload Page (`app/dashboard/video/page.tsx`)
- **File Upload Mode**: Drag-and-drop or click to select video files
- **URL Paste Mode**: Paste direct video URLs from YouTube or other sources
- **Language Selection**: Choose source and target languages
- **State Management**: 
  - `selectedFile`: File object when uploading
  - `videoUrl`: URL when pasting
  - `sourceLanguage` / `targetLanguage`: Language codes (en, es, fr, de, etc.)
  - `isLoading`: Loading state during upload
  - `error`: Error messages displayed to user

#### Translation Flow (from video/page.tsx)
1. User selects video file or pastes URL
2. User chooses source and target languages
3. Click "Start Translation" button triggers:
   - **Step 1**: Upload file to backend (if file mode)
     - POST to `/api/v1/upload?file_type=video`
     - Returns `storage_path` for the uploaded file
   - **Step 2**: Create job record
     - POST to `/api/v1/jobs/video-translate/create`
     - Payload includes: `storage_path`, `source_language`, `target_language`
     - Returns: `job_id`, status, metadata
   - **Step 3**: Queue for processing
     - POST to `/api/v1/jobs/{job_id}/process`
     - Starts async Celery task
   - **Step 4**: Redirect to progress page
     - Route: `/dashboard/video/progress?job_id={job_id}`

#### Progress Page (`app/dashboard/video/progress/page.tsx`)
- Real-time job monitoring with 2-second auto-refresh
- Displays:
  - Overall progress percentage
  - Current phase (TRANSCRIBING, TRANSLATING, SYNTHESIZING, etc.)
  - Current step description
  - Animated progress bar
  - Started/completed timestamps
  - Error messages if job fails
- Auto-stops refreshing when job completes or fails
- Download button appears when translation is complete
- Action buttons to translate another video or go back to hub

---

## Backend Implementation

### 1. Upload Endpoint (`app/upload_routes.py`)
**Endpoint**: `POST /api/v1/upload`
- Parameters:
  - `file`: Video file (multipart form data)
  - `file_type`: "video"
- Returns:
  - `file_id`: Unique file identifier
  - `storage_path`: Path where file is stored
  - `filename`: Original filename
  - `size_bytes`: File size

### 2. Create Job Endpoint (`app/upload_routes.py`)
**Endpoint**: `POST /api/v1/jobs/video-translate/create`
- Request Schema: `VideoTranslateRequest`
  ```json
  {
    "file_id": "unique-id",
    "storage_path": "uploads/user-id/video/filename.mp4",
    "source_language": "en",
    "target_language": "es",
    "model_size": "base"
  }
  ```
- Creates Job record in database with:
  - `job_type`: "video_translate"
  - `status`: "pending"
  - `input_file`: storage_path
  - `job_metadata`: JSON with language settings
- Returns: Job object with ID and initial status

### 3. Process Job Endpoint (`app/upload_routes.py`)
**Endpoint**: `POST /api/v1/jobs/{job_id}/process`
- Validates job exists and is in PENDING or FAILED state
- Validates user has sufficient credits
- Queues Celery task: `process_video_translation`
- Task parameters:
  - `job_id`: Job identifier
  - `user_id`: User identifier
  - `input_file_path`: Full path to video file
  - `source_lang`: Source language code
  - `target_lang`: Target language code
  - `model_size`: Whisper model size
- Returns: (202 Accepted) with updated job status

### 4. Get Job Status Endpoint (`app/upload_routes.py`)
**Endpoint**: `GET /api/v1/jobs/{job_id}`
- Returns current job status with:
  - `status`: "pending" | "processing" | "completed" | "failed"
  - `progress_percentage`: 0-100
  - `phase`: Current processing phase
  - `current_step`: Human-readable current step
  - `started_at`: ISO timestamp when processing started
  - `completed_at`: ISO timestamp when completed
  - `output_file`: Path to translated video (when completed)
  - `error_message`: Error details (if failed)

---

## Celery Task: `process_video_translation`

**Location**: `app/celery_tasks.py`

### Task Flow
1. **Initialization** (0%)
   - Set job status to PROCESSING
   - Set phase to TRANSCRIBING
   
2. **Transcription** (0-30%)
   - Extract audio from video
   - Transcribe with Whisper model
   - Detect speech segments
   
3. **Translation** (30-60%)
   - Translate transcribed text
   - Use GPT-4 or Claude for context-aware translation
   
4. **Audio Synthesis** (60-90%)
   - Generate translated speech
   - Use Coqui TTS or similar
   - Match original speaker characteristics if enabled
   
5. **Video Assembly** (90-100%)
   - Replace original audio with dubbed audio
   - Synchronize with video timeline
   - Apply lip-sync correction (optional)
   - Save output video

### Progress Updates
- Job record updated every 2-3 seconds with:
  - `progress_percentage`: Current completion %
  - `phase`: Current phase name
  - `current_step`: Detailed description
  - Database commit after each update

---

## Database Schema

### Job Model (app/job_model.py)
```python
class Job(Base):
    __tablename__ = "jobs"
    
    id: str (primary key)
    user_id: str (foreign key)
    job_type: str ("video_translate", "transcribe", "translate", "synthesize")
    status: str ("pending", "processing", "completed", "failed")
    input_file: str (storage path)
    output_file: Optional[str] (result path)
    error_message: Optional[str]
    job_metadata: str (JSON with language settings)
    created_at: datetime
    completed_at: Optional[datetime]
    
    # Progress tracking fields
    phase: Optional[str] (JobPhase enum)
    progress_percentage: float (0-100)
    current_step: Optional[str]
    started_at: Optional[datetime]
```

---

## Error Handling

### Frontend Error Cases
- Invalid file type: Show error message
- Upload failure: Display server error
- Job creation failure: Show error and allow retry
- Network errors: Connection timeout messages
- Job processing failure: Display error message from backend

### Backend Error Cases
- File not found: Set job to FAILED with error message
- Transcription failure: Catch exception, log, set FAILED
- Translation failure: Continue with fallback or error
- Synthesis failure: Mark as FAILED
- Invalid job state: HTTP 400 with descriptive message

---

## Testing

### Manual Testing via Frontend
1. Navigate to `/dashboard/video`
2. Upload a video file (MP4, AVI, MOV, etc.)
3. Select source and target languages
4. Click "Start Translation"
5. Watch progress on `/dashboard/video/progress?job_id=...`

### Programmatic Testing
```bash
python scripts/test_video_translation.py --email user@example.com --video-path path/to/video.mp4
```

This script:
1. Creates/gets test user
2. Uploads video file
3. Creates job
4. Queues for processing
5. Monitors status
6. Provides job URL for frontend monitoring

---

## API URLs Summary

| Operation | Method | Endpoint | Auth |
|-----------|--------|----------|------|
| Upload video | POST | `/api/v1/upload?file_type=video` | Bearer token |
| Create job | POST | `/api/v1/jobs/video-translate/create` | Bearer token |
| Process job | POST | `/api/v1/jobs/{job_id}/process` | Bearer token |
| Get status | GET | `/api/v1/jobs/{job_id}` | Bearer token |
| SSE stream | GET | `/api/v1/jobs/{job_id}/stream` | Bearer token or `?token=` |
| Download result | GET | `/api/v1/download/{job_id}` | Bearer token |

---

## Security

### Authentication
- All endpoints require Bearer token in Authorization header
- Token generated via JWT at login
- Token validated before any job operation

### Authorization
- Users can only access their own jobs
- Jobs filtered by `user_id` in all queries
- File access restricted to uploading user

### File Storage
- Files stored in `uploads/{user_id}/{file_type}/` directory
- Unique file IDs prevent guessing paths
- Cleanup of old files handled by scheduled task

---

## Performance Considerations

### Video Translation Times
- Small video (< 5 min): 15-30 minutes
- Medium video (5-30 min): 30-90 minutes
- Large video (> 30 min): 2-6 hours

### Resource Usage
- RAM: 4GB+ recommended for large videos
- CPU: Utilizes all cores for transcription
- Disk: 3-5x the original video size for temporary files

### Scaling
- Celery queue supports multiple workers
- Distribute across multiple machines
- Use priority queues for paid users vs free tier

---

## Future Enhancements

1. **Batch Processing**: Queue multiple videos at once
2. **Progress WebSockets**: Real-time updates instead of polling
3. **Voice Cloning**: Replicate speaker's voice in translation
4. **Subtitle Generation**: Auto-generate subtitle files
5. **Lip-Sync**: Advanced video sync for dubbed audio
6. **Language Detection**: Auto-detect source language
7. **Preview**: Preview translation before final processing
8. **Quality Settings**: Allow users to select quality/speed tradeoff

---

## Troubleshooting

### Video upload fails
- Check file size (max 500MB)
- Verify video codec support
- Check backend storage permissions

### Job processing hangs
- Check Celery worker is running
- Verify Redis/broker connection
- Check system resources (disk space, RAM)

### Progress not updating
- Check frontend polling request
- Verify SSE endpoint is accessible
- Check database connection

### Video output quality issues
- Increase `model_size` parameter (base → medium → large)
- Enable advanced features (lip-sync, voice cloning)
- Check source video quality
