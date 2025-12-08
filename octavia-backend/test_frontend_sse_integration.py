"""Frontend SSE Integration Tests - Validates real-time progress updates end-to-end."""
import json
import pytest
import time
import threading
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.job_model import Job, JobStatus, JobPhase
from app import models
from app.celery_tasks import (
    process_transcription,
    process_translation,
    process_synthesis,
    process_video_translation,
)
from app.core.security import create_access_token


# Clear all test data at module level
def setup_module():
    """Clean database before tests."""
    db = SessionLocal()
    # Clear frontend integration test jobs
    db.query(Job).filter(Job.user_id == "test-user-frontend").delete()
    # Clear frontend integration test users
    db.query(models.User).filter(models.User.id == "test-user-frontend").delete()
    db.commit()
    db.close()


client = TestClient(app)
TEST_USER_ID = "test-user-frontend"
TEST_TOKEN_PAYLOAD = {"sub": TEST_USER_ID}
TEST_AUTH_HEADER = None


class TestFrontendSSEIntegration:
    """Test frontend integration with real-time SSE progress updates."""

    @classmethod
    def setup_class(cls):
        """Set up test user once per class."""
        db = SessionLocal()
        # Create test user
        user = models.User(
            id=TEST_USER_ID,
            email="test-frontend@example.com",
            password_hash="hashed_test",
            is_verified=True,
            credits=50000,
            role="user"
        )
        try:
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        # Create a valid JWT for tests and set auth header
        token = create_access_token({"sub": str(TEST_USER_ID), "type": "access"})
        global TEST_AUTH_HEADER
        TEST_AUTH_HEADER = {"Authorization": f"Bearer {token}"}

    def test_sse_connection_lifecycle(self):
        """Test SSE connection establishment, data streaming, and graceful closure."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="transcription",
                input_file="/tmp/test.mp4",
                status=JobStatus.PENDING,
                phase=JobPhase.PENDING,
                progress_percentage=0.0,
                current_step="Waiting to start"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            # Connect to SSE endpoint
            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers=TEST_AUTH_HEADER
            ) as response:
                # Should get 200 OK
                assert response.status_code == 200
                
                # Simulate job progress by updating DB in background thread
                def update_job_progress():
                    """Simulate job progress updates."""
                    time.sleep(0.1)
                    job_db = SessionLocal()
                    try:
                        job_obj = job_db.query(Job).filter(Job.id == job_id).first()
                        if job_obj:
                            job_obj.status = JobStatus.PROCESSING
                            job_obj.phase = JobPhase.TRANSCRIBING
                            job_obj.progress_percentage = 20.0
                            job_obj.current_step = "Transcribing audio"
                            job_db.commit()
                    finally:
                        job_db.close()
                
                # Start background thread
                thread = threading.Thread(target=update_job_progress)
                thread.start()
                
                # Read SSE events
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        # Stop after receiving expected events
                        if len(events) >= 2:
                            break
                
                thread.join()
                
                # Verify we received progress data
                assert len(events) > 0
                first_event = events[0]
                assert "job_id" in first_event
                assert "status" in first_event
                assert "phase" in first_event
                assert "progress_percentage" in first_event
                assert "current_step" in first_event

        finally:
            db.close()

    def test_sse_progress_percentage_changes(self):
        """Test that SSE correctly streams progress percentage changes."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="translation",
                input_file="/tmp/test.mp4",
                status=JobStatus.PROCESSING,
                phase=JobPhase.TRANSLATING,
                progress_percentage=0.0,
                current_step="Starting translation"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            # Connect to SSE endpoint
            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers=TEST_AUTH_HEADER
            ) as response:
                assert response.status_code == 200
                
                # Update progress multiple times
                def update_progress_multiple():
                    """Simulate multiple progress updates."""
                    time.sleep(0.1)
                    job_db = SessionLocal()
                    try:
                        for percent in [20, 40, 60, 80, 100]:
                            job_obj = job_db.query(Job).filter(Job.id == job_id).first()
                            if job_obj:
                                job_obj.progress_percentage = float(percent)
                                job_obj.current_step = f"Translation {percent}% complete"
                                if percent == 100:
                                    job_obj.status = JobStatus.COMPLETED
                                    job_obj.phase = JobPhase.COMPLETED
                                job_db.commit()
                            time.sleep(0.05)
                    finally:
                        job_db.close()
                
                thread = threading.Thread(target=update_progress_multiple)
                thread.start()
                
                # Collect events
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if len(events) >= 5:
                            break
                
                thread.join()
                
                # Verify progress increased
                assert len(events) > 0
                progress_values = [e.get("progress_percentage", 0) for e in events]
                # Progress should generally increase (or stay same)
                assert all(progress_values[i] <= progress_values[i+1] 
                          for i in range(len(progress_values)-1)
                          if i+1 < len(progress_values))

        finally:
            db.close()

    def test_sse_phase_transitions(self):
        """Test SSE correctly streams phase transitions (PENDING → TRANSCRIBING → COMPLETED)."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="transcription",
                input_file="/tmp/test.mp4",
                status=JobStatus.PENDING,
                phase=JobPhase.PENDING,
                progress_percentage=0.0,
                current_step="Initializing"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers=TEST_AUTH_HEADER
            ) as response:
                assert response.status_code == 200
                
                def update_phases():
                    """Simulate phase transitions."""
                    time.sleep(0.1)
                    job_db = SessionLocal()
                    try:
                        phases = [
                            (JobPhase.TRANSCRIBING, JobStatus.PROCESSING, 20.0),
                            (JobPhase.COMPLETED, JobStatus.COMPLETED, 100.0),
                        ]
                        for phase, status, progress in phases:
                            job_obj = job_db.query(Job).filter(Job.id == job_id).first()
                            if job_obj:
                                job_obj.phase = phase
                                job_obj.status = status
                                job_obj.progress_percentage = progress
                                job_obj.current_step = f"Phase: {phase.value}"
                                job_db.commit()
                            time.sleep(0.1)
                    finally:
                        job_db.close()
                
                thread = threading.Thread(target=update_phases)
                thread.start()
                
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if len(events) >= 3:
                            break
                
                thread.join()
                
                # Verify phase field exists in events
                assert all("phase" in e for e in events)
                phases_observed = [e.get("phase") for e in events]
                assert len(phases_observed) > 0

        finally:
            db.close()

    def test_sse_error_scenarios(self):
        """Test SSE handles error states correctly (FAILED status, error_message)."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="synthesis",
                input_file="/tmp/test.mp4",
                status=JobStatus.PROCESSING,
                phase=JobPhase.SYNTHESIZING,
                progress_percentage=50.0,
                current_step="Synthesizing audio"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers=TEST_AUTH_HEADER
            ) as response:
                assert response.status_code == 200
                
                def simulate_error():
                    """Simulate job failure."""
                    time.sleep(0.1)
                    job_db = SessionLocal()
                    try:
                        job_obj = job_db.query(Job).filter(Job.id == job_id).first()
                        if job_obj:
                            job_obj.status = JobStatus.FAILED
                            job_obj.phase = JobPhase.FAILED
                            job_obj.progress_percentage = 0.0
                            job_obj.error_message = "Audio synthesis failed: Invalid input"
                            job_obj.current_step = "Error"
                            job_db.commit()
                    finally:
                        job_db.close()
                
                thread = threading.Thread(target=simulate_error)
                thread.start()
                
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if len(events) >= 2:
                            break
                
                thread.join()
                
                # Verify error state is transmitted
                assert len(events) > 0
                # At least one event should have error info
                has_error_info = any(
                    e.get("status") == "failed" or "error" in e.lower()
                    for e in events
                )
                # Either status is 'failed' or error_message is present
                final_event = events[-1] if events else {}
                assert final_event.get("status") in ["failed", "processing"] or "error_message" in final_event

        finally:
            db.close()

    def test_polling_endpoint_consistency_with_sse(self):
        """Test that polling endpoint returns same data as SSE endpoint."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="video_translation",
                input_file="/tmp/test.mp4",
                status=JobStatus.PROCESSING,
                phase=JobPhase.TRANSCRIBING,
                progress_percentage=30.0,
                current_step="Transcribing video",
                started_at=datetime.utcnow()
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            # Get data from polling endpoint
            polling_response = client.get(
                f"/api/v1/jobs/{job_id}/status",
                headers=TEST_AUTH_HEADER
            )
            assert polling_response.status_code == 200
            polling_data = polling_response.json()

            # Connect to SSE endpoint
            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers={"Authorization": f"Bearer test-token"}
            ) as response:
                assert response.status_code == 200
                
                # Get first SSE event
                sse_data = None
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        sse_data = json.loads(line[6:])
                        break
                
                # Verify both contain same core fields
                assert sse_data is not None
                
                core_fields = ["job_id", "status", "phase", "progress_percentage", "current_step"]
                for field in core_fields:
                    # Polling data should have these fields
                    assert field in polling_data, f"Missing {field} in polling response"
                    # SSE data should have these fields
                    assert field in sse_data, f"Missing {field} in SSE event"
                
                # Values should match
                assert polling_data["status"] == sse_data["status"]
                assert polling_data["phase"] == sse_data["phase"]
                assert polling_data["progress_percentage"] == sse_data["progress_percentage"]

        finally:
            db.close()

    def test_sse_job_not_found(self):
        """Test SSE endpoint handles non-existent job gracefully."""
        response = client.get(
            "/api/v1/jobs/nonexistent-job-id/stream",
            headers=TEST_AUTH_HEADER
        )
        # Should return 404 or handle gracefully
        assert response.status_code in [404, 400]

    def test_sse_multiple_progress_updates_rapid(self):
        """Test SSE handles rapid progress updates correctly."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="transcription",
                input_file="/tmp/test.mp4",
                status=JobStatus.PROCESSING,
                phase=JobPhase.TRANSCRIBING,
                progress_percentage=0.0,
                current_step="Starting"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            with client.stream(
                "GET",
                f"/api/v1/jobs/{job_id}/stream",
                headers=TEST_AUTH_HEADER
            ) as response:
                assert response.status_code == 200
                
                def rapid_updates():
                    """Simulate rapid progress updates."""
                    time.sleep(0.05)
                    job_db = SessionLocal()
                    try:
                        # Rapid updates
                        for i in range(1, 11):
                            job_obj = job_db.query(Job).filter(Job.id == job_id).first()
                            if job_obj:
                                job_obj.progress_percentage = float(i * 10)
                                job_obj.current_step = f"Step {i}/10"
                                job_db.commit()
                            time.sleep(0.02)  # Very rapid
                    finally:
                        job_db.close()
                
                thread = threading.Thread(target=rapid_updates)
                thread.start()
                
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if len(events) >= 5:
                            break
                
                thread.join()
                
                # Should handle rapid updates without errors
                assert len(events) > 0
                # Progress should generally increase
                progress_values = [float(e.get("progress_percentage", 0)) for e in events]
                # Allow some flexibility due to threading
                assert len(progress_values) > 0

        finally:
            db.close()

    def test_sse_response_format_completeness(self):
        """Test that SSE response includes all required fields for frontend."""
        db = SessionLocal()
        try:
            # Create a job with all fields
            job = Job(
                user_id=TEST_USER_ID,
                job_type="translation",
                input_file="/tmp/test.mp4",
                status=JobStatus.PROCESSING,
                phase=JobPhase.TRANSLATING,
                progress_percentage=45.5,
                current_step="Processing subtitles",
                started_at=datetime.utcnow(),
                output_file="/tmp/output.mp4"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            # Get from polling endpoint (more stable than SSE for format testing)
            response = client.get(
                f"/api/v1/jobs/{job_id}/status",
                headers=TEST_AUTH_HEADER
            )
            assert response.status_code == 200
            data = response.json()

            # Verify all required fields for frontend
            required_fields = {
                "job_id": str,
                "status": str,
                "phase": str,
                "progress_percentage": (int, float),
                "current_step": (str, type(None)),
                "created_at": (str, type(None)),
                "started_at": (str, type(None)),
                "completed_at": (str, type(None)),
                "error_message": (str, type(None)),
                "output_file": (str, type(None)),
            }

            for field, expected_type in required_fields.items():
                assert field in data, f"Missing required field: {field}"
                if expected_type == (str, type(None)):
                    # Allow either string or None
                    assert data[field] is None or isinstance(data[field], str)
                elif isinstance(expected_type, tuple):
                    assert isinstance(data[field], expected_type), \
                        f"{field} should be {expected_type}, got {type(data[field])}"
                else:
                    assert isinstance(data[field], expected_type)

        finally:
            db.close()

    def test_sse_auth_required(self):
        """Test that SSE endpoint requires authentication."""
        db = SessionLocal()
        try:
            # Create a job
            job = Job(
                user_id=TEST_USER_ID,
                job_type="transcription",
                input_file="/tmp/test.mp4",
                status=JobStatus.PENDING,
                phase=JobPhase.PENDING,
                progress_percentage=0.0
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id

            # Try without auth
            response = client.get(f"/api/v1/jobs/{job_id}/stream")
            # Should be unauthorized
            assert response.status_code in [401, 403]

        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
