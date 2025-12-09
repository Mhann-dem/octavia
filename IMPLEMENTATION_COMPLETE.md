# Video Translation - Download & Credit System Complete ✅

**Date:** December 8, 2025  
**Status:** Video translation now fully integrated with download and credit deduction

---

## What's Been Implemented

### 1. Backend Download Endpoint ✅
**File:** `octavia-backend/app/upload_routes.py`

Added `GET /api/v1/jobs/{job_id}/download` endpoint that:
- Validates job ownership and completion status
- Retrieves output file from storage
- Returns file with proper headers for browser download
- Handles errors gracefully (job not found, incomplete, missing output)

```python
@router.get("/jobs/{job_id}/download")
async def download_job_output(job_id: str, user_id: str, ...):
    """Download the output file for a completed job."""
```

### 2. Credit Deduction on Job Completion ✅
**File:** `octavia-backend/app/celery_tasks.py`

Enhanced `process_video_translation()` task to:
- Calculate credit cost based on video duration
- Deduct credits from user account when job completes
- Log transaction to `CreditTransaction` table
- Handle edge cases (insufficient credits, user not found)
- Gracefully handle credit deduction errors without failing the job

```python
if success:
    # Calculate and deduct credits
    credit_cost = CreditCalculator.calculate_credits(
        job_type="video_translate",
        input_file_path=input_file_path
    )
    user.credits -= credit_cost
    transaction = CreditTransaction(...)
```

### 3. Frontend Download Handler ✅
**File:** `octavia-web/app/dashboard/video/progress/page.tsx`

Updated progress page with:
- `handleDownload()` function that:
  - Fetches file from backend endpoint
  - Extracts filename from response headers
  - Creates blob and triggers browser download
  - Handles errors with user-friendly messages
- Download button that calls the handler
- Automatic cleanup of object URLs

```typescript
const handleDownload = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/download`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    const blob = await response.blob();
    // Trigger download...
};
```

---

## Complete Video Translation Workflow

### Step-by-Step Flow

1. **Upload** (Frontend)
   - User drags/drops or pastes video URL
   - Video uploaded to `POST /api/v1/upload?file_type=video`
   - Returns `storage_path` and `file_id`

2. **Create Job** (Frontend)
   - Creates job via `POST /api/v1/jobs/video-translate/create`
   - Returns `job_id`
   - Stores language settings in job metadata

3. **Queue Processing** (Frontend)
   - Calls `POST /api/v1/jobs/{job_id}/process`
   - Job queued to Celery worker

4. **Process** (Backend Worker)
   - `process_video_translation()` task executes
   - Updates progress every 2-3 seconds:
     - `phase`: TRANSCRIBING → TRANSLATING → SYNTHESIZING → COMPLETED
     - `progress_percentage`: 0% → 100%
     - `current_step`: "Initializing..." → "Translation completed"

5. **Track Progress** (Frontend)
   - Fetches job status every 2 seconds via `GET /api/v1/jobs/{job_id}`
   - Displays real-time progress bar, phase, and current step
   - Auto-stops refresh when job completes/fails

6. **Deduct Credits** (Backend)
   - On job completion, calculates cost based on video duration
   - Deducts credits from user account
   - Creates transaction record for audit trail
   - Updates UI with "credits deducted" message

7. **Download Result** (Frontend)
   - "Download" button appears when job completed
   - Calls `GET /api/v1/jobs/{job_id}/download`
   - Browser automatically downloads output file
   - Filename extracted from response headers

---

## Database Changes

### Updated Job Model
- `output_file`: Stores path to translated video file
- `progress_percentage`: 0-100% completion
- `phase`: TRANSCRIBING, TRANSLATING, SYNTHESIZING, COMPLETED, FAILED
- `current_step`: Human-readable status message
- `started_at`: When job processing began
- `error_message`: If job failed

### Credit System Tables (Already Exist)
- `CreditTransaction`: Logs all credit movements
  - `user_id`, `type` (deduction/addition), `credits_amount`
  - `reason`, `balance_after`, `timestamp`

---

## API Reference

### Upload Video
```bash
POST /api/v1/upload?file_type=video
Content-Type: multipart/form-data

Returns:
{
  "file_id": "uuid",
  "filename": "video.mp4",
  "storage_path": "users/user123/video/uuid_video.mp4",
  "size_bytes": 5242880
}
```

### Create Translation Job
```bash
POST /api/v1/jobs/video-translate/create
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "file_id": "uuid",
  "storage_path": "users/user123/video/uuid_video.mp4",
  "source_language": "en",
  "target_language": "es",
  "model_size": "base"
}

Returns:
{
  "id": "job-id",
  "status": "pending",
  "progress_percentage": 0,
  "phase": "PENDING"
}
```

### Queue Job for Processing
```bash
POST /api/v1/jobs/{job_id}/process
Authorization: Bearer {token}

Returns:
{
  "task_id": "celery-task-id",
  "status": "queued"
}
```

### Get Job Status
```bash
GET /api/v1/jobs/{job_id}
Authorization: Bearer {token}

Returns:
{
  "id": "job-id",
  "status": "processing",
  "progress_percentage": 45,
  "phase": "TRANSLATING",
  "current_step": "Translating chunk 12 of 50...",
  "started_at": "2025-12-08T10:30:00",
  "output_file": null  // Set when completed
}
```

### Download Completed Video
```bash
GET /api/v1/jobs/{job_id}/download
Authorization: Bearer {token}

Returns:
- File blob (application/octet-stream)
- Filename in Content-Disposition header
```

---

## Credit Calculation

Credits are deducted based on video duration:

| Video Duration | Credits Deducted |
|---|---|
| < 5 minutes | 10 credits |
| 5-15 minutes | 25 credits |
| 15-30 minutes | 50 credits |
| 30-60 minutes | 100 credits |
| > 60 minutes | 150 credits |

Reference: `app/credit_calculator.py`

---

## Testing Checklist

- [ ] Upload a 2-minute test video
- [ ] Verify job created with correct metadata
- [ ] Watch progress tracking update in real-time
- [ ] Verify credits deducted from account on completion
- [ ] Click download button and verify file downloads
- [ ] Check transaction history shows deduction
- [ ] Test with insufficient credits (should fail before processing)
- [ ] Test with different languages (en→es, en→fr, etc.)
- [ ] Test with 30-minute video (performance test)

---

## Known Limitations

1. **Video Assembly**: FFmpeg reassembly works but output quality depends on codec preservation
2. **TTS Quality**: Using pyttsx3 (basic quality). Upgrade to Coqui XTTS v2 recommended
3. **Large Files**: Max 500MB upload size. Increase if needed
4. **File Cleanup**: Completed files not automatically deleted. Recommend periodic cleanup job
5. **Storage**: Using local filesystem. Recommend S3 or similar for production

---

## Next Steps

1. **Wire remaining features** (Audio, Subtitles, etc.) - Use same pattern as video
2. **Test end-to-end** with real videos and monitor credit deduction
3. **Performance test** with longer videos (30+ minutes)
4. **Upgrade TTS engine** to Coqui XTTS v2 for better voice quality
5. **Setup PostgreSQL** for production database
6. **Deploy to production** - Vercel (frontend), Railway/Render (backend)

---

## Files Modified

1. `octavia-backend/app/upload_routes.py`
   - Added FileResponse import
   - Added `GET /jobs/{job_id}/download` endpoint

2. `octavia-backend/app/celery_tasks.py`
   - Added logging import
   - Enhanced `process_video_translation()` with credit deduction logic
   - Added credit transaction logging

3. `octavia-web/app/dashboard/video/progress/page.tsx`
   - Added `handleDownload()` function
   - Updated download button to use new handler
   - Added error handling for download failures

---

**Status:** Ready for end-to-end testing!  
**Estimated Time to Next Feature:** 2-3 hours per feature  
**Recommended Priority:** Audio Translation (uses same pattern as video)
