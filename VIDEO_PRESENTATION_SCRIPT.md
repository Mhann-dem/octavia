# Octavia Audio Translation Feature - 10 Minute Presentation Script

## Opening (30 seconds)
**Show your face, introduce yourself**

"Hi, I'm [Your Name]. I've just completed the audio translation feature for Octavia, LunarTech's cloud-native video translation platform. Over the next 10 minutes, I'll walk you through the architecture, demonstrate the working application, and explain the design decisions that make this feature scalable and maintainable."

---

## Section 1: Problem Statement (1 minute)

**Show the Octavia GitHub repo on screen**

"Octavia is designed to break down language barriers while preserving cinematic quality. The original platform supported video translation—extracting audio, transcribing it, translating the text, and synthesizing new audio in the target language.

However, many users need to translate **just the audio**—podcasts, audiobooks, voice messages—without the overhead of video processing. So I built the Audio Translation feature to:

1. **Reduce processing time** — Skip video extraction, merge steps
2. **Lower compute costs** — Smaller ML models needed
3. **Improve UX** — Faster feedback for audio-only workflows
4. **Maintain consistency** — Follow the established video translation pattern

This feature demonstrates architectural thinking, API design, and full-stack integration."

---

## Section 2: Architecture Overview (2 minutes)

**Show architecture diagram or whiteboard sketch**

"The audio translation pipeline follows a 4-step process, mirroring video translation but optimized for audio:

### Frontend (Next.js 15 + React)
- **Audio Upload Page** (`/dashboard/audio`)
  - Dual upload modes: drag-and-drop file + URL paste
  - Language selection (8+ languages)
  - Voice synthesis options (gender, style)
  
- **Progress Tracking Page** (`/dashboard/audio/progress`)
  - Real-time job status polling every 3 seconds
  - Visual progress indicators
  - Download button when complete

### Backend (FastAPI + Celery + Whisper + Helsinki NLP)

**Three Key Components:**

1. **API Layer** (`/api/v1/jobs/audio-translate/create`)
   - Accepts upload + language config
   - Creates Job record in database
   - Validates user credits before processing

2. **Job Queue** (Celery)
   - `process_audio_translation()` task
   - Async job processing with real-time progress
   - Credit deduction on completion
   - Error handling & automatic cleanup

3. **Processing Pipeline** (`audio_translate_pipeline()`)
   - **Step 1**: Load audio (WAV, 16kHz sample rate)
   - **Step 2**: Transcribe with OpenAI Whisper (auto language detection)
   - **Step 3**: Translate with Helsinki NLP transformers
   - **Step 4**: Synthesize with pyttsx3 (fallback handling)

### Data Flow:
User → Frontend → Upload Storage → Create Job → Queue Task → Worker Processing → Update Job Status → Download Result

All integrated with:
- JWT authentication
- Credit-based billing system
- Multi-user support
- Local + S3 storage ready
"

---

## Section 3: Code Walkthrough (3 minutes)

**Screen share: Show key files**

### 3.1 Frontend Upload Page (1 minute)
**Open `octavia-web/app/dashboard/audio/page.tsx`**

"The frontend uses React hooks to manage file upload and language selection. Key features:

- `useState` tracks selected file, languages, errors
- `handleTranslate()` orchestrates the three-step process:
  1. POST `/api/v1/upload` with FormData
  2. POST `/api/v1/jobs/audio-translate/create` with storage_path
  3. POST `/api/v1/jobs/{job_id}/process` to queue
- Error handling shows user-friendly messages
- Redirects to progress page with job_id parameter

The pattern is identical to video translation—this ensures consistency and maintainability."

### 3.2 Backend Job Creation (1 minute)
**Open `octavia-backend/app/upload_routes.py` → `create_audio_translate_job()`**

"The backend endpoint:
- Accepts `AudioTranslateRequest` schema (file_id, storage_path, source/target languages)
- Creates a `Job` record with type `audio_translate`
- Stores language config as JSON metadata
- Returns job ID and initial status

This follows the same pattern as video, transcription, translation, and synthesis jobs—keeping the codebase DRY and scalable."

### 3.3 Celery Task + Worker Pipeline (1 minute)
**Open `octavia-backend/app/celery_tasks.py` → `process_audio_translation()`**

"The Celery task:
- Receives job_id, user_id, and file paths
- Updates job status to PROCESSING
- Calls `audio_translate_pipeline()` in the worker
- On success: marks job COMPLETED, deducts credits, logs transaction
- On failure: marks job FAILED, logs error, cleans temp files

Then in `workers.py`, the pipeline does the heavy lifting:
1. Load audio with librosa at 16kHz
2. Transcribe with Whisper (supports auto language detection)
3. Translate with Helsinki NLP (uses pre-trained transformer models)
4. Synthesize with pyttsx3 and fallback on error
5. Return synthesized audio file path

The error handling is graceful—if synthesis fails, we return the original audio instead of crashing."

---

## Section 4: Live Demo (2.5 minutes)

**Start the backend and frontend locally**

### Demo Steps:

1. **Show running services**
   - Backend: `uvicorn app.main:app --reload` on port 8001
   - Frontend: `npm run dev` on port 3000

2. **Upload audio file**
   - Navigate to `/dashboard/audio`
   - Drag and drop a test MP3 file (or paste a URL)
   - Select: English → Spanish
   - Click "Start Audio Translation"
   - Show the upload completing

3. **Show job creation**
   - Explain that `/api/v1/upload` stores the file
   - Then `/api/v1/jobs/audio-translate/create` creates the job record
   - Then `/api/v1/jobs/{job_id}/process` queues the Celery task

4. **Show progress tracking**
   - Auto-redirect to `/dashboard/audio/progress?job_id=xyz`
   - Show real-time polling every 3 seconds
   - Explain the progress states: queued → processing → completed
   - Display job metadata (job ID, start time, duration)

5. **Show completed job**
   - When status = "completed", download button appears
   - Show the downloaded translated audio file

**Talking points during demo:**
- "The frontend is responsive—works on mobile"
- "Progress updates every 3 seconds without manual refresh"
- "Error handling is built-in—if synthesis fails, we gracefully fallback"
- "Credits were deducted from the user's account on completion"
- "All job data is persisted—you can return later and resume"

---

## Section 5: Design Decisions & Trade-Offs (1.5 minutes)

**Show whiteboard or slides**

### Why follow the video translation pattern?

1. **Consistency**: Developers familiar with video translation instantly understand audio
2. **Maintainability**: Code duplication is minimal; changes apply to both
3. **Scalability**: Same job queue system handles any media type
4. **Testing**: Test patterns are identical across features

### Language Model Choices:

- **Whisper**: Industry-standard speech-to-text, handles accent variation
- **Helsinki NLP**: Lightweight, supports 100+ language pairs, runs locally
- **pyttsx3**: Offline TTS, no API keys, fallback-friendly

### Frontend Choices:

- **Next.js 15**: Server-side rendering, optimized images, API routes
- **Framer Motion**: Smooth animations, Liquid Glass aesthetic
- **Real-time polling**: Simple to implement, works without WebSocket setup
- **Dual upload modes**: Accommodates users with files and URLs

### Storage:

- **Local storage** for dev, **S3-ready** for production
- **Temporary files** cleaned up after processing
- **Output files** stored permanently for 30 days (configurable)

---

## Section 6: Testing & Quality (0.5 minutes)

"To ensure quality:

- ✅ Frontend pages compile without errors (TypeScript)
- ✅ All API endpoints tested and working
- ✅ Celery tasks tested with fake Redis (no external deps needed)
- ✅ Error cases handled: invalid files, insufficient credits, transcription failures
- ✅ Logging throughout for debugging

For this assignment, local testing validates the core flow. In production, we'd add:
- Unit tests for each component
- Integration tests for the full pipeline
- Load tests for concurrent users
- E2E tests with Playwright"

---

## Section 7: Reflection & Next Steps (0.5 minutes)

**Show your face again**

"This audio translation feature showcases the skills needed at LunarTech:

1. **Full-stack thinking**: I designed the frontend to match the backend API, not the other way around
2. **AI integration**: I leveraged Whisper and transformers, even though I'm not an ML engineer
3. **System design**: I reused patterns from video translation to keep the codebase clean
4. **Attention to UX**: The progress page provides real-time feedback and graceful error handling
5. **Documentation**: I documented the feature so the next engineer can extend it

If selected, I'm excited to:
- Build more translation features (subtitles, real-time streaming)
- Optimize ML models for production (quantization, caching)
- Improve the Liquid Glass UI with micro-interactions
- Work alongside AI engineers to push the platform forward

Thank you!"

---

## Appendix: Key Files to Show

1. **Frontend Upload**: `octavia-web/app/dashboard/audio/page.tsx`
2. **Frontend Progress**: `octavia-web/app/dashboard/audio/progress/page.tsx`
3. **Backend Schema**: `octavia-backend/app/upload_schemas.py` (AudioTranslateRequest)
4. **Backend Endpoint**: `octavia-backend/app/upload_routes.py` (create_audio_translate_job)
5. **Celery Task**: `octavia-backend/app/celery_tasks.py` (process_audio_translation)
6. **Worker Pipeline**: `octavia-backend/app/workers.py` (audio_translate_pipeline)
7. **GitHub Commits**: Show your Git log with meaningful commit messages

---

## Timing Breakdown
- Opening: 0:30
- Problem: 1:00
- Architecture: 2:00
- Code Walkthrough: 3:00
- Demo: 2:30
- Design Decisions: 1:30
- Testing: 0:30
- Reflection: 0:30
- **Total: ~10 minutes**

---

## Tips for Recording
1. **Be conversational**: Imagine explaining to a senior engineer
2. **Show, don't tell**: Keep code/UI on screen while explaining
3. **Highlight wins**: Show error handling, progress tracking, clean APIs
4. **Mention constraints**: "I kept pyttsx3 for offline TTS to avoid API dependencies"
5. **Be authentic**: Share what you learned and what you'd do differently
6. **End strong**: Reiterate why this matters (language barrier breaking, scalability)
