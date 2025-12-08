"""Helper: create a test user (if missing) and a Job row in dev.db, printing job id and a JWT.

Usage:
    python scripts/create_test_job.py --email test@example.com --job-type transcribe --input-file uploads/example.mp4

The script prints a JWT you can use with `?token=...` for EventSource or as `Authorization: Bearer ...`.
"""
import argparse
import uuid
from datetime import timedelta

from app.db import SessionLocal
from app.models import User
from app.job_model import Job, JobStatus
from app.core.security import create_access_token, get_password_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="test-user-frontend@example.com")
    parser.add_argument("--job-type", default="transcribe")
    parser.add_argument("--input-file", default="uploads/test_input.mp4")
    parser.add_argument("--credits", type=int, default=1000)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if not user:
            print(f"Creating test user {args.email}")
            user = User(
                id=str(uuid.uuid4()),
                email=args.email,
                password_hash=get_password_hash("test-password"),
                credits=args.credits,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # ensure user has enough credits
            if (user.credits or 0) < args.credits:
                user.credits = args.credits
                db.commit()

        # create job
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            user_id=user.id,
            job_type=args.job_type,
            input_file=args.input_file,
            status=JobStatus.PENDING,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        token = create_access_token({"sub": user.id, "type": "access"}, expires_delta=timedelta(days=7))

        print("\nCreated test job:")
        print(f"  job_id: {job.id}")
        print(f"  user_id: {user.id}")
        print("\nUse this token for EventSource (dev-only):")
        print(f"  ?token={token}")
        print("or as Authorization header:")
        print(f"  Authorization: Bearer {token}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
