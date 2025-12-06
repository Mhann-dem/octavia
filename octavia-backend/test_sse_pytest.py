"""Test SSE (Server-Sent Events) endpoints for real-time job progress."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db, SessionLocal
from app.job_model import Job, JobStatus
from app import models
from app.upload_routes import get_current_user


# Use the app's own database
TestingSessionLocal = SessionLocal


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = lambda: "test-user-sse"
client = TestClient(app)


class TestSSEProgress:
    """Test real-time job progress via SSE."""

    def setup_method(self):
        """Set up test fixtures."""
        import uuid
        
        # Create test user with unique email
        test_email = f"sse-test-{uuid.uuid4().hex[:8]}@example.com"
        db = TestingSessionLocal()
        
        # Clear existing test user if present
        existing = db.query(models.User).filter(models.User.id == "test-user-sse").first()
        if existing:
            db.delete(existing)
            db.commit()
        
        # Delete orphaned jobs
        db.query(Job).filter(Job.user_id == "test-user-sse").delete()
        db.commit()
        
        # Create new test user
        user = models.User(
            id="test-user-sse",
            email=test_email,
            password_hash="hashed_password",
            is_verified=True,
            credits=10000,
            role="user"
        )
        db.add(user)
        db.commit()
        db.close()

    def test_get_job_status_endpoint(self):
        """Test GET /jobs/{job_id}/status endpoint."""
        db = TestingSessionLocal()
        
        # Create a test job
        job = Job(
            id="job-status-test",
            user_id="test-user-sse",
            job_type="transcribe",
            input_file="uploads/test.mp3",
            status=JobStatus.PROCESSING,
            job_metadata=json.dumps({"language": "en"}),
            credit_cost="100",
        )
        db.add(job)
        db.commit()
        db.close()
        
        # Get job status
        response = client.get("/api/v1/jobs/job-status-test/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-status-test"
        assert data["status"] == "processing"
        assert data["job_type"] == "transcribe"
        assert data["credit_cost"] == "100"

    def test_get_job_status_nonexistent_job(self):
        """Test GET /jobs/{job_id}/status with nonexistent job."""
        response = client.get("/api/v1/jobs/nonexistent-job/status")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_job_status_other_user_job(self):
        """Test that users can only see their own job status."""
        db = TestingSessionLocal()
        
        # Create job for different user
        job = Job(
            id="job-other-user",
            user_id="other-user-id",
            job_type="translate",
            input_file="uploads/test.txt",
            status=JobStatus.COMPLETED,
        )
        db.add(job)
        db.commit()
        db.close()
        
        # Try to get status (should fail)
        response = client.get("/api/v1/jobs/job-other-user/status")
        
        assert response.status_code == 404

    def test_stream_job_progress_completed_job(self):
        """Test SSE stream for completed job."""
        db = TestingSessionLocal()
        
        # Create a completed job
        job = Job(
            id="job-stream-completed",
            user_id="test-user-sse",
            job_type="transcribe",
            input_file="uploads/test.mp3",
            output_file="uploads/test.txt",
            status=JobStatus.COMPLETED,
            job_metadata=json.dumps({"language": "en"}),
        )
        db.add(job)
        db.commit()
        db.close()
        
        # Stream progress (should get completed status and close)
        response = client.get(
            "/api/v1/jobs/job-stream-completed/stream",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        # Response should have SSE headers
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_stream_job_progress_processing_job(self):
        """Test SSE stream for processing job."""
        db = TestingSessionLocal()
        
        # Create a processing job
        job = Job(
            id="job-stream-processing",
            user_id="test-user-sse",
            job_type="synthesize",
            input_file="uploads/test.txt",
            status=JobStatus.PROCESSING,
            celery_task_id="celery-123",
        )
        db.add(job)
        db.commit()
        db.close()
        
        # Stream progress
        response = client.get(
            "/api/v1/jobs/job-stream-processing/stream",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Should be streaming (200 OK)
        assert response.status_code == 200

    def test_stream_job_progress_failed_job(self):
        """Test SSE stream for failed job."""
        db = TestingSessionLocal()
        
        # Create a failed job
        job = Job(
            id="job-stream-failed",
            user_id="test-user-sse",
            job_type="translate",
            input_file="uploads/test.txt",
            status=JobStatus.FAILED,
            error_message="Transcription service unavailable",
        )
        db.add(job)
        db.commit()
        db.close()
        
        # Stream progress (should get failed status)
        response = client.get(
            "/api/v1/jobs/job-stream-failed/stream",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_stream_job_progress_nonexistent_job(self):
        """Test SSE stream for nonexistent job."""
        response = client.get("/api/v1/jobs/nonexistent/stream")
        
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
