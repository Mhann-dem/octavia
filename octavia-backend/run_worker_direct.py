"""Direct worker test: create job in DB for an existing uploaded file and run transcribe_audio directly.
This avoids HTTP server issues and shows worker logs/errors.
"""
import os
from pathlib import Path
from app.db import get_db
from app.job_model import Job, JobStatus
from app import workers
import uuid
import json

# Find a recently uploaded file
uploads_dir = Path.cwd() / "uploads" / "users"
if not uploads_dir.exists():
    raise SystemExit("No uploads/users directory found")

# pick the first user and first audio file
user_dirs = list(uploads_dir.iterdir())
if not user_dirs:
    raise SystemExit("No user dirs in uploads/users")

user_dir = user_dirs[-1]
audio_dir = user_dir / "audio"
if not audio_dir.exists():
    raise SystemExit(f"No audio dir for user {user_dir}")

files = list(audio_dir.glob("*"))
if not files:
    raise SystemExit(f"No files in {audio_dir}")

file_path = files[-1]
print("Found file:", file_path)

# Create job record
db = next(get_db())
job_id = str(uuid.uuid4())
job = Job(
    id=job_id,
    user_id=str(user_dir.name),
    job_type="transcribe",
    input_file=str(Path('uploads') / 'users' / user_dir.name / 'audio' / file_path.name),
    status=JobStatus.PENDING,
    job_metadata=json.dumps({"language": None, "model_size": "tiny"}),
)

db.add(job)
db.commit()
print("Created job", job_id)

# Run worker
success = workers.transcribe_audio(db, job_id, job.input_file, language=None, model_size="tiny")
print("Transcription success:", success)
if success:
    updated = db.query(Job).filter(Job.id == job_id).first()
    print("Job status:", updated.status, "output_file:", updated.output_file)
else:
    updated = db.query(Job).filter(Job.id == job_id).first()
    print("Job failed, error:", updated.error_message if updated else 'no job')
