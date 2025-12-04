"""Debug: Check if job_metadata is being stored in the database."""
from app import db
from app.job_model import Job

session = db.SessionLocal()
jobs = session.query(Job).filter(Job.job_type == "translate").all()

print(f"Found {len(jobs)} translation jobs")
for job in jobs[-1:]:  # Show last one
    print(f"\nJob ID: {job.id}")
    print(f"Job metadata attribute: {getattr(job, 'job_metadata', 'NOT FOUND')}")
    print(f"Job metadata value: {job.job_metadata}")
    print(f"All attributes: {dir(job)}")

session.close()
