"""Test Pydantic serialization of JobOut."""
from app.upload_schemas import JobOut
from app.job_model import Job
from app import db
from datetime import datetime

# Get a translation job from the database
session = db.SessionLocal()
job = session.query(Job).filter(Job.job_type == "translate").order_by(Job.created_at.desc()).first()

if job:
    print("Job from DB:")
    print(f"  id: {job.id}")
    print(f"  job_metadata: {repr(job.job_metadata)}")
    
    # Try to serialize with Pydantic
    print("\nSerializing with Pydantic:")
    job_out = JobOut.model_validate(job)
    print(f"JobOut.job_metadata: {repr(job_out.job_metadata)}")
    
    print("\nSerialized to dict:")
    job_dict = job_out.model_dump()
    print(f"Keys in dict: {list(job_dict.keys())}")
    print(f"job_metadata in dict: {job_dict.get('job_metadata')}")
    
    print("\nSerialized to JSON:")
    import json
    job_json = json.loads(job_out.model_dump_json())
    print(f"Keys in JSON: {list(job_json.keys())}")
    print(f"job_metadata in JSON: {job_json.get('job_metadata')}")
else:
    print("No translation jobs found")

session.close()
