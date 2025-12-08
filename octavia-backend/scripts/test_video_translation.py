#!/usr/bin/env python
"""
Test script to verify video translation endpoint is working.
Usage: python scripts/test_video_translation.py --email user@example.com --video-path /path/to/video.mp4
"""

import sys
import json
import requests
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models import User

API_BASE_URL = "http://127.0.0.1:8001"


def get_or_create_test_user(email: str, password: str = "TestPassword123!") -> tuple[str, str]:
    """Get existing user or create a new one, return (user_id, token)."""
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"✓ Found existing user: {email}")
            token = create_access_token({"sub": str(user.id), "type": "access"})
            return str(user.id), token
        else:
            print(f"✗ User {email} not found")
            print("Please sign up first via the frontend or use scripts/create_test_job.py")
            sys.exit(1)
    finally:
        db.close()


def test_video_upload(token: str, video_path: str) -> dict:
    """Upload a video file."""
    print(f"\n1. Uploading video: {video_path}")
    
    with open(video_path, "rb") as f:
        files = {"file": (Path(video_path).name, f, "video/mp4")}
        params = {"file_type": "video"}
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/upload",
            files=files,
            params=params,
            headers=headers,
        )
    
    if response.status_code != 200:
        print(f"✗ Upload failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    print(f"✓ Upload successful!")
    print(f"  File ID: {data['file_id']}")
    print(f"  Storage Path: {data['storage_path']}")
    return data


def test_create_job(token: str, storage_path: str) -> dict:
    """Create a video translation job."""
    print(f"\n2. Creating video translation job")
    
    payload = {
        "file_id": "test_video",
        "storage_path": storage_path,
        "source_language": "en",
        "target_language": "es",
        "model_size": "base",
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/video-translate/create",
        json=payload,
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"✗ Job creation failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    print(f"✓ Job created!")
    print(f"  Job ID: {data['id']}")
    print(f"  Status: {data['status']}")
    return data


def test_process_job(token: str, job_id: str) -> dict:
    """Queue the job for processing."""
    print(f"\n3. Queuing job for processing")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/{job_id}/process",
        headers=headers,
    )
    
    if response.status_code not in (200, 202):
        print(f"✗ Job processing failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    print(f"✓ Job queued for processing!")
    print(f"  Status: {data['status']}")
    return data


def test_get_job_status(token: str, job_id: str) -> dict:
    """Get current job status."""
    print(f"\n4. Getting job status")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE_URL}/api/v1/jobs/{job_id}",
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"✗ Get status failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    print(f"✓ Job status retrieved!")
    print(f"  Status: {data['status']}")
    print(f"  Progress: {data.get('progress_percentage', 0)}%")
    print(f"  Phase: {data.get('phase', 'Unknown')}")
    print(f"  Current Step: {data.get('current_step', 'N/A')}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Test video translation endpoint")
    parser.add_argument("--email", default="test@example.com", help="User email")
    parser.add_argument("--video-path", default="test_video.mp4", help="Path to video file")
    args = parser.parse_args()
    
    # Check if video file exists
    if not Path(args.video_path).exists():
        print(f"✗ Video file not found: {args.video_path}")
        print("\nTo test with a real video:")
        print("  1. Create a small test video or download a sample")
        print("  2. Run: python scripts/test_video_translation.py --video-path /path/to/video.mp4")
        print("\nFor now, using a dummy file test instead...")
        # Create a small dummy file
        Path(args.video_path).write_bytes(b"dummy video content")
    
    # Get or create user
    print("Getting user credentials...")
    user_id, token = get_or_create_test_user(args.email)
    print(f"✓ User ID: {user_id}")
    print(f"✓ Token: {token[:20]}...")
    
    # Run tests
    try:
        upload_result = test_video_upload(token, args.video_path)
        job_result = test_create_job(token, upload_result["storage_path"])
        process_result = test_process_job(token, job_result["id"])
        status_result = test_get_job_status(token, job_result["id"])
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        print(f"\nJob ID: {job_result['id']}")
        print(f"Monitor progress at: http://localhost:3000/dashboard/video/progress?job_id={job_result['id']}")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
