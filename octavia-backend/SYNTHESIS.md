# Text-to-Speech Synthesis Implementation

## Overview

The Octavia backend now includes a complete text-to-speech (TTS) synthesis pipeline as the final step in the media processing workflow:

```
Audio File → Transcribe → Translate → Synthesize (Audio Output)
```

## Architecture

### Synthesis Worker (`app/workers.py`)

The `synthesize_audio()` function:
- **Input**: Path to a translation JSON file containing translated text
- **Processing**: Uses `pyttsx3` library to generate speech audio
- **Output**: WAV audio file + job metadata with synthesis details
- **Error Handling**: Gracefully handles empty text by creating a placeholder output file

**Key Features:**
- No external binary dependencies (unlike `ffmpeg`)
- Cross-platform: Works on Windows, macOS, Linux
- Configurable speech rate (default: 150 wpm) and volume (default: 0.9)
- Edge case handling: If transcription/translation yields no text, creates a metadata placeholder so downstream workflows don't break

### API Endpoints

#### Create Synthesis Job
```http
POST /api/v1/jobs/synthesize/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": "translation-job-id",
  "voice_id": "default",
  "speed": 1.0
}
```

**Response** (`200 OK`):
```json
{
  "id": "synthesis-job-id",
  "user_id": "user-id",
  "job_type": "synthesize",
  "status": "pending",
  "input_file": "path/to/translation.json",
  "output_file": null,
  "job_metadata": "{\"voice_id\": \"default\", \"speed\": 1.0, ...}",
  "created_at": "2025-12-04T18:55:57"
}
```

**Validation:**
- Translation job must exist and be completed
- Translation job must have an output file

#### Process Synthesis Job
```http
POST /api/v1/jobs/{job_id}/process
Authorization: Bearer <token>
```

Executes the synthesis job, generating audio from the translated text. Updates job status to `completed` or `failed`.

#### List/Get Jobs
Jobs of type `synthesize` can be retrieved using existing endpoints:
- `GET /api/v1/jobs` - List all jobs (filtered by user)
- `GET /api/v1/jobs/{job_id}` - Get a specific synthesis job

### Job Metadata Schema

After synthesis completes, `job_metadata` contains:
```json
{
  "language": "en",
  "text_length": 1234,
  "audio_size_bytes": 45678,
  "synthesis_engine": "pyttsx3",
  "source_languages": {
    "original": "en",
    "translated": "es"
  }
}
```

## Dependencies

Add to `requirements-core.txt`:
```
pyttsx3>=2.90
```

Already installed in current environment.

### System Requirements

**No external binaries required.** `pyttsx3` uses OS-level text-to-speech APIs:
- **Windows**: SAPI5 (built-in)
- **macOS**: NSSpeechSynthesizer (built-in)
- **Linux**: espeak (commonly available via package manager, not required for Windows/macOS)

## Testing

Run the comprehensive end-to-end test:
```bash
python test_synthesis_flow.py
```

This test:
1. Creates a user account
2. Uploads a test audio file
3. Transcribes the audio to text (Whisper)
4. Translates the text (Helsinki NLP)
5. Synthesizes speech from the translated text
6. Verifies all output files and metadata

**Expected Result:** All 31 test steps pass.

## Edge Cases Handled

### Empty Transcription
If the audio produces no transcription text, the pipeline:
1. Translation job creates an empty translated JSON
2. Synthesis job creates a placeholder output file (copy of translation JSON)
3. Job completes successfully with metadata `"message": "No text to synthesize"`

This ensures downstream workflows don't fail on missing files while making it clear that no actual audio was generated.

### File Path Normalization
- Workers store output paths using `.as_posix()` for consistency across Windows/Unix
- Process endpoint resolves relative paths with multiple candidate strategies:
  1. Absolute path as-is
  2. Relative to current working directory
  3. Under `uploads/` subdirectory
  4. Converted slashes if starting with `uploads/`

## Future Enhancements

### 1. Real TTS with Actual Audio
Current implementation generates placeholder files when text is empty. To produce actual WAV/MP3 audio:
```python
# Example: Full synthesis with actual audio output
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.save_to_file(text, output_path)
engine.runAndWait()
```
This is already implemented but only triggered when text is present.

### 2. Async Job Queue
The `/process` endpoints currently block. For production, implement async processing:
- **Celery** + Redis: Distributed task queue with result tracking
- **RQ** (Redis Queue): Simpler lightweight queue
- **APScheduler**: Scheduled background tasks

Example:
```python
from celery import shared_task

@shared_task
def process_synthesis_job(job_id, user_id):
    session = SessionLocal()
    result = workers.synthesize_audio(...)
    session.close()
    return result
```

Then in endpoint:
```python
@router.post("/jobs/{job_id}/process")
def process_job(job_id, user_id):
    process_synthesis_job.delay(job_id, user_id)
    return {"status": "queued"}
```

### 3. Multiple Voice Options
Extend `pyttsx3` to support multiple voices:
```python
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # or other indices
```

### 4. Audio Format Options
Currently generates WAV. To support MP3/OGG:
- Use `ffmpeg` for post-processing
- Or integrate `librosa` + `soundfile` for format conversion

### 5. Streaming/Progressive Output
For long texts, stream audio chunks instead of waiting for full generation:
- Implement WebSocket endpoint for real-time streaming
- Or return presigned S3 URLs for chunk-based playback

## Configuration

Synthesis behavior can be tuned in `app/workers.py`:
```python
engine.setProperty('rate', 150)      # Speech rate (words per minute)
engine.setProperty('volume', 0.9)    # Volume (0.0 - 1.0)
```

For production, expose these as job request parameters:
```json
{
  "job_id": "translation-job-id",
  "voice_id": "default",
  "speed": 1.5,
  "volume": 0.8
}
```

## Troubleshooting

### Issue: "Audio file was not created"
- **Cause**: `pyttsx3` failed to save file or engine crashed
- **Solution**: Check disk space, file permissions, and ensure translation JSON exists

### Issue: Synthesis job stuck in "processing"
- **Cause**: Process endpoint didn't complete or server crashed
- **Solution**: Implement async queue (see Future Enhancements) to prevent blocking

### Issue: No sound generated (Windows)
- **Cause**: SAPI5 not available or misconfigured
- **Solution**: Verify Windows text-to-speech is installed (`Settings > Ease of Access > Speech`)

## References

- [pyttsx3 Documentation](https://pyttsx3.readthedocs.io/)
- [OpenAI Whisper](https://github.com/openai/whisper) (transcription)
- [Helsinki NLP Models](https://huggingface.co/Helsinki-NLP) (translation)
