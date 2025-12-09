# Implementation Guide: Audio Translation & Remaining Features

**Date:** December 8, 2025  
**Status:** Ready for implementation

---

## Quick Implementation Pattern

All remaining translation features follow the **same pattern** as video translation:

```
Upload File → Create Job → Queue for Processing → Track Progress → Download Result
```

### Code Template for Each Feature

**1. Frontend Page Structure**
```typescript
// Same as video translation page:
- useState for selectedFile, language selections, loading, error
- handleFileSelect() for file uploads
- handleTranslate() to call backend endpoints
- Redirect to progress page with job_id

// Progress page:
- Fetch job status every 2 seconds
- Display progress bar, phase, current step
- Download button when completed
- Auto-stop refresh when done
```

**2. Backend Endpoint Pattern**
```python
@router.post("/jobs/{feature}/create")
def create_job(request: FeatureRequest, user_id: str, db_session: Session):
    job = Job(
        user_id=user_id,
        job_type="{feature}",  # audio_translate, subtitle_gen, etc.
        input_file=request.storage_path,
        status="pending"
    )
    db_session.add(job)
    db_session.commit()
    return JobOut(...)
```

**3. Celery Task Pattern**
```python
@app.task(bind=True, name="app.celery_tasks.process_{feature}")
def process_feature(self, job_id: str, user_id: str, input_file_path: str, ...):
    # Update progress
    job.progress_percentage = X%
    job.phase = "PHASE_NAME"
    job.current_step = "Human readable message"
    
    # Call worker function
    success = workers.{feature}_pipeline(...)
    
    # On success: deduct credits, set output_file
    # On failure: set error_message
```

---

## Feature 1: Audio Translation ⏳ 

**Time Estimate:** 1-2 hours

### Files to Modify

1. **Frontend Upload Page**
   - File: `octavia-web/app/dashboard/audio/page.tsx`
   - Copy structure from `app/dashboard/video/page.tsx`
   - Change endpoints to `/jobs/audio-translate/create`
   - Keep language selectors (already there)
   - Add audio file type validation (mp3, wav, flac)

2. **Frontend Progress Page**
   - File: `octavia-web/app/dashboard/audio/progress/page.tsx`
   - Copy from video progress page
   - No changes needed (generic for all job types)

3. **Backend Endpoint**
   - File: `octavia-backend/app/upload_routes.py`
   - Add if missing: `@router.post("/jobs/audio-translate/create")`
   - Create AudioTranslateRequest schema
   - Create Job with job_type="audio_translate"

4. **Backend Schema**
   - File: `octavia-backend/app/upload_schemas.py`
   - Add `AudioTranslateRequest` class:
     ```python
     class AudioTranslateRequest(BaseModel):
         file_id: str
         storage_path: str
         source_language: str
         target_language: str
         model_size: str = "base"
     ```

5. **Celery Task**
   - File: `octavia-backend/app/celery_tasks.py`
   - Add if missing: `process_audio_translation()` task
   - Call `workers.audio_translate_pipeline()`
   - Deduct credits on completion (same as video)

### Code Snippets

**Frontend Upload Page Changes:**
```typescript
// In handleTranslate():
const response = await fetch(`${API_BASE_URL}/api/v1/jobs/audio-translate/create`, {
  // ... same as video
});
```

**Backend Endpoint:**
```python
@router.post("/jobs/audio-translate/create", response_model=upload_schemas.JobOut)
def create_audio_translate_job(
    request: upload_schemas.AudioTranslateRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    job = Job(
        user_id=user_id,
        job_type="audio_translate",
        input_file=request.storage_path,
        status="pending",
        job_metadata=json.dumps({
            "source_language": request.source_language,
            "target_language": request.target_language,
            "model_size": request.model_size,
        }),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job
```

**Celery Task:**
```python
@app.task(bind=True, name="app.celery_tasks.process_audio_translation")
def process_audio_translation(self, job_id: str, user_id: str, input_file_path: str,
                               source_lang: str, target_lang: str, model_size: str = "base"):
    """Same pattern as video translation but for audio."""
    # ... (copy from process_video_translation and rename)
```

---

## Feature 2: Subtitle Generation ⏳

**Time Estimate:** 1-2 hours

### Key Difference
- Only needs **source language** (auto-detects and transcribes)
- No target language needed
- Output is SRT/VTT subtitle file

### Files to Modify

1. **Frontend Upload**
   - File: `octavia-web/app/dashboard/subtitles/page.tsx`
   - Remove target language selector
   - Keep source language (or auto-detect option)
   - Button text: "Generate Subtitles"

2. **Backend Endpoint**
   - File: `octavia-backend/app/upload_routes.py`
   - Add: `POST /jobs/subtitle-gen/create`
   - Schema: Only `file_id`, `storage_path`, optional `source_language`

3. **Celery Task**
   - File: `octavia-backend/app/celery_tasks.py`
   - Add: `process_subtitle_generation()`
   - Calls: `workers.generate_subtitles()`
   - Output: SRT or VTT file

### Code Pattern
```python
class SubtitleGenRequest(BaseModel):
    file_id: str
    storage_path: str
    source_language: Optional[str] = None  # Auto-detect if not provided

@router.post("/jobs/subtitle-gen/create")
def create_subtitle_gen_job(request: SubtitleGenRequest, ...):
    job = Job(
        job_type="subtitle_generation",
        job_metadata=json.dumps({
            "source_language": request.source_language or "auto"
        })
    )
```

---

## Feature 3: Subtitle Translation ⏳

**Time Estimate:** 2-3 hours (slightly more complex due to file handling)

### Key Difference
- Uploads SRT/VTT file (not video/audio)
- Translates subtitle text while preserving timestamps
- Output: Translated SRT/VTT file

### Files to Modify

1. **Frontend Upload**
   - File: `octavia-web/app/dashboard/subtitles/translate/page.tsx`
   - File type selector: Only SRT, VTT, ASS, SSA
   - Language selectors: Source and target

2. **Backend Endpoint**
   - File: `octavia-backend/app/upload_routes.py`
   - Add: `POST /jobs/subtitle-translate/create`
   - Validate file extension (srt, vtt, ass, ssa)

3. **Celery Task**
   - File: `octavia-backend/app/celery_tasks.py`
   - Add: `process_subtitle_translation()`
   - Parse SRT/VTT, translate text, preserve timestamps

---

## Feature 4: Subtitle to Audio ⏳

**Time Estimate:** 1-2 hours

### Key Difference
- Uploads SRT/VTT subtitle file
- Synthesizes speech from subtitle text
- Only needs target language (language of subtitles)
- Output: Audio file (MP3/WAV)

### Code Pattern
```python
class SubtitleToAudioRequest(BaseModel):
    file_id: str
    storage_path: str
    language: str  # Language of the subtitles
    voice_choice: Optional[str] = None

@router.post("/jobs/subtitle-to-audio/create")
def create_subtitle_to_audio_job(request: SubtitleToAudioRequest, ...):
    job = Job(
        job_type="subtitle_to_audio",
        job_metadata=json.dumps({
            "language": request.language,
            "voice": request.voice_choice or "default"
        })
    )
```

---

## Feature 5: Job History - Fetch & Display ⏳

**Time Estimate:** 2-3 hours

### What Needs to Change

1. **Frontend Page**
   - File: `octavia-web/app/dashboard/history/page.tsx`
   - Replace mock `jobs` array with API call
   - Implement filtering by status, date, job type
   - Add sorting (newest first, etc.)
   - Add pagination if needed

2. **Code Changes**
```typescript
// Replace mock data with:
const [jobs, setJobs] = useState<Job[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const fetchJobs = async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs?limit=50`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const data = await response.json();
    setJobs(data);
  };
  fetchJobs();
}, []);

// Filter logic
const filtered = jobs.filter(job => 
  (filterStatus === "all" || job.status === filterStatus) &&
  (filterType === "all" || job.job_type === filterType)
);
```

3. **Backend Endpoint** (Already exists!)
   - File: `octavia-backend/app/upload_routes.py`
   - Use: `GET /api/v1/jobs?limit=50`
   - Already returns list of user's jobs ordered by creation date

---

## Feature 6: Billing - Balance & Checkout ⏳

**Time Estimate:** 1-2 hours

### What Needs to Change

1. **Frontend Page**
   - File: `octavia-web/app/dashboard/billing/page.tsx`
   - Replace mock data with API calls
   - Already has structure, just needs wiring

2. **Code Changes**
```typescript
useEffect(() => {
  const fetchData = async () => {
    // Fetch balance
    const balanceRes = await fetch(`${API_BASE_URL}/api/v1/billing/balance`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const balanceData = await balanceRes.json();
    setBalance(balanceData.balance);
    
    // Fetch pricing tiers
    const pricingRes = await fetch(`${API_BASE_URL}/api/v1/billing/pricing`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const pricingData = await pricingRes.json();
    setTiers(pricingData.tiers);
  };
  fetchData();
}, []);

// Handle checkout
const handleCheckout = async (tierId: string) => {
  const res = await fetch(`${API_BASE_URL}/api/v1/billing/checkout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ tier_id: tierId })
  });
  const data = await res.json();
  window.location.href = data.checkout_url;  // Redirect to Polar.sh
};
```

3. **Backend Endpoints** (Already exist!)
   - `GET /api/v1/billing/balance`
   - `GET /api/v1/billing/pricing`
   - `POST /api/v1/billing/checkout`

---

## Implementation Priority & Order

### Phase 1 (This Session - 3-4 hours)
1. ✅ **Video Translation Download** - DONE
2. ✅ **Credit Deduction** - DONE
3. **Audio Translation** (1-2 hrs) - Copy video pattern
4. **Subtitle Generation** (1-2 hrs) - Similar to audio but transcription only

### Phase 2 (Next Session - 4-5 hours)
5. **Subtitle Translation** (2-3 hrs) - Text-based translation
6. **Subtitle to Audio** (1-2 hrs) - TTS synthesis
7. **Job History** (2-3 hrs) - API integration

### Phase 3 (Following Session - 2-3 hours)
8. **Billing & Balance** (1-2 hrs) - Simple API wiring
9. **Profile Updates** (1-2 hrs) - User settings

### Phase 4+ (Optional Advanced)
10. **Team Management** (4 hrs)
11. **My Voices** (6 hrs)
12. **Settings** (2 hrs)
13. **Help & Support** (2 hrs)

---

## Testing Each Feature

### Standard Test for Each Translation Feature
```bash
1. Upload a test file
2. Select source and target language
3. Click translate button
4. Monitor progress page (should update every 2s)
5. When complete, download output
6. Verify output file is valid
7. Check user credits were deducted
8. Check job appears in history
```

### Test Files to Use
- **Audio:** 30-second MP3 sample (podcast intro)
- **Subtitles:** Simple 5-line SRT file
- **Video:** 4-minute MP4 (existing test)

---

## Environment Setup Required

### Backend (Already Done)
- ✅ FastAPI running on :8001
- ✅ SQLite database with migrations
- ✅ Celery worker ready to process tasks
- ✅ All endpoints defined

### Frontend (Already Done)
- ✅ Next.js running on :3000
- ✅ Auth system working
- ✅ API integration patterns established

### Only Need
- [ ] Start Celery worker to process jobs
- [ ] Ensure `USE_FAKE_REDIS=true` environment variable set
- [ ] Run migrations if not done

---

## Common Gotchas & Solutions

### Issue: Job stays in "pending" forever
**Cause:** Celery worker not running  
**Fix:** `USE_FAKE_REDIS=true python -m celery -A app.celery_tasks worker`

### Issue: File not found in download
**Cause:** Worker didn't set `output_file` field  
**Fix:** Check worker logs, ensure `workers.{feature}_pipeline()` sets output path

### Issue: Credits not deducted
**Cause:** Credit deduction code has error  
**Fix:** Check Celery worker logs, add more error handling

### Issue: File type validation fails
**Cause:** Uppercase file extension in upload  
**Fix:** Normalize extension to lowercase: `file.filename.lower().endswith('.mp4')`

### Issue: "Insufficient credits" before processing
**Cause:** Pre-validation checked but credits not actually deducted later  
**Fix:** This is correct behavior - prevent job if user can't afford it

---

## Performance Tips

1. **Large Files:** Test with progressively larger files
   - 1 minute (quick feedback)
   - 10 minutes (production realistic)
   - 30+ minutes (stress test)

2. **Parallel Processing:** Celery can handle multiple jobs
   - Set `worker_prefetch_multiplier=1` (already set)
   - Add more worker processes for scale

3. **Progress Updates:** Frontend polls every 2s
   - Increase if server load high
   - Decrease for more responsive feel

4. **Credit Calculation:** Based on duration
   - Adjust multipliers in `CreditCalculator` if needed
   - Log deductions for transparency

---

## Success Criteria

Each feature is "done" when:
- [ ] Frontend page wired to backend
- [ ] Upload works → creates job
- [ ] Job queued to worker
- [ ] Progress tracking shows real-time updates
- [ ] Job completion deducts credits
- [ ] Download available for completed jobs
- [ ] Job appears in history
- [ ] Error states handled gracefully

---

**Next Step:** Choose which feature to implement first and start with it!

Recommendation: **Audio Translation** (very similar to video, ~2 hours)

Command to start:
```bash
# In one terminal
python -m uvicorn app.main:app --reload --port 8001

# In another terminal
USE_FAKE_REDIS=true python -m celery -A app.celery_tasks worker --loglevel=info

# In third terminal
npm run dev  # Next.js dev server
```

Ready when you are! 🚀
