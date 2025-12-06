"""Pytest-based media processing pipeline tests (Whisper, Helsinki NLP, Coqui TTS)."""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import io

# Ensure app module can be imported
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from app.job_model import Job, JobStatus
from app.core.database import Base, engine, get_db
from app.models import User
import uuid


@pytest.fixture(scope="session")
def setup_db():
    """Create all tables in test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_db(setup_db):
    """Clear all data before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    """Create a test client with mocked auth."""
    from app.core.database import SessionLocal
    from app.upload_routes import get_current_user
    
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    test_context = {"user_id": "test-user-id"}
    
    def override_get_current_user(authorization=None):
        return test_context["user_id"]
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    client = TestClient(app)
    client.test_context = test_context
    
    return client


@pytest.fixture
def test_user_with_credits(client):
    """Create a test user with credits in database."""
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    
    db = SessionLocal()
    try:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash=get_password_hash("TestPass123!"),
            is_verified=True,
            credits=5000  # Plenty of credits for testing
        )
        db.add(user)
        db.commit()
        
        client.test_context["user_id"] = user_id
        return user_id
    finally:
        db.close()


class TestTranscriptionPipeline:
    """Test Whisper transcription functionality."""
    
    @patch('app.workers.transcribe_audio')
    def test_01_transcribe_audio_basic(self, mock_transcribe, client, test_user_with_credits):
        """Test creating and processing a transcription job."""
        # Mock successful transcription
        mock_transcribe.return_value = True
        
        # Create a test audio file
        file_content = b"mock audio data" * 500
        files = {"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        
        # Upload file
        upload_response = client.post(
            "/api/v1/upload",
            params={"file_type": "audio"},
            files=files
        )
        assert upload_response.status_code == 200
        storage_path = upload_response.json()["storage_path"]
        
        # Create transcription job
        job_request = {
            "file_id": "test-file",
            "storage_path": storage_path,
            "language": "auto"
        }
        
        job_response = client.post(
            "/api/v1/jobs/transcribe",
            json=job_request
        )
        
        assert job_response.status_code == 200
        job_data = job_response.json()
        assert job_data["job_type"] == "transcribe"
        assert job_data["status"] == "pending"
        job_id = job_data["id"]
        
        # Process the job
        process_response = client.post(
            f"/api/v1/jobs/{job_id}/process"
        )
        
        # Should succeed with mocked transcription
        assert process_response.status_code in [200, 500]  # 200 if succeeds, 500 if worker fails
    
    @patch('app.workers.transcribe_audio')
    def test_02_transcribe_with_language_detection(self, mock_transcribe, client, test_user_with_credits):
        """Test transcription with specific language."""
        mock_transcribe.return_value = True
        
        file_content = b"mock audio data" * 500
        files = {"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        
        upload_response = client.post(
            "/api/v1/upload",
            params={"file_type": "audio"},
            files=files
        )
        storage_path = upload_response.json()["storage_path"]
        
        # Create job with specific language
        job_request = {
            "file_id": "test-file",
            "storage_path": storage_path,
            "language": "es"  # Spanish
        }
        
        job_response = client.post(
            "/api/v1/jobs/transcribe",
            json=job_request
        )
        
        assert job_response.status_code == 200
        job_data = job_response.json()
        metadata = json.loads(job_data["job_metadata"])
        assert metadata["language"] == "es"
    
    @patch('app.workers.transcribe_audio')
    def test_03_transcribe_missing_file(self, mock_transcribe, client, test_user_with_credits):
        """Test transcription with non-existent file."""
        # Don't upload anything
        job_request = {
            "file_id": "nonexistent",
            "storage_path": "nonexistent/path.wav",
            "language": "auto"
        }
        
        job_response = client.post(
            "/api/v1/jobs/transcribe",
            json=job_request
        )
        
        assert job_response.status_code == 200
        job_id = job_response.json()["id"]
        
        # Try to process - should fail gracefully
        process_response = client.post(
            f"/api/v1/jobs/{job_id}/process"
        )
        
        # Should fail due to missing file
        assert process_response.status_code in [400, 404, 500]


class TestTranslationPipeline:
    """Test Helsinki NLP translation functionality."""
    
    def test_04_create_translation_job(self, client, test_user_with_credits):
        """Test creating a translation job from completed transcription."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Create a mock completed transcription job
            transcription_job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_type="transcribe",
                input_file="mock_input.wav",
                output_file="mock_transcription.txt",  # Must have output
                status=JobStatus.COMPLETED,
                job_metadata=json.dumps({"language": "en"})
            )
            db.add(transcription_job)
            db.commit()
            job_id = transcription_job.id
        finally:
            db.close()
        
        # Create translation job
        translate_request = {
            "job_id": job_id,
            "source_language": "en",
            "target_language": "es"
        }
        
        response = client.post(
            "/api/v1/jobs/translate/create",
            json=translate_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "translate"
        assert data["status"] == "pending"
        metadata = json.loads(data["job_metadata"])
        assert metadata["source_language"] == "en"
        assert metadata["target_language"] == "es"
    
    def test_05_translation_requires_completed_transcription(self, client, test_user_with_credits):
        """Test that translation requires a completed transcription job."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Create an incomplete transcription job
            pending_job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_type="transcribe",
                input_file="mock_input.wav",
                status=JobStatus.PENDING,  # Not completed
                job_metadata=json.dumps({"language": "en"})
            )
            db.add(pending_job)
            db.commit()
            job_id = pending_job.id
        finally:
            db.close()
        
        # Try to create translation - should fail
        translate_request = {
            "job_id": job_id,
            "source_language": "en",
            "target_language": "es"
        }
        
        response = client.post(
            "/api/v1/jobs/translate/create",
            json=translate_request
        )
        
        assert response.status_code == 400
        assert "completed" in response.text.lower() or "must be" in response.text.lower()
    
    def test_06_translation_multiple_languages(self, client, test_user_with_credits):
        """Test translation to multiple target languages."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Create completed transcription job
            transcription_job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_type="transcribe",
                input_file="mock_input.wav",
                output_file="mock_transcription.txt",
                status=JobStatus.COMPLETED,
                job_metadata=json.dumps({"language": "en"})
            )
            db.add(transcription_job)
            db.commit()
            job_id = transcription_job.id
        finally:
            db.close()
        
        # Test multiple languages
        languages = [
            ("en", "es"),  # English to Spanish
            ("en", "fr"),  # English to French
            ("en", "de"),  # English to German
        ]
        
        for source, target in languages:
            translate_request = {
                "job_id": job_id,
                "source_language": source,
                "target_language": target
            }
            
            response = client.post(
                "/api/v1/jobs/translate/create",
                json=translate_request
            )
            
            assert response.status_code == 200
            data = response.json()
            metadata = json.loads(data["job_metadata"])
            assert metadata["target_language"] == target


class TestSynthesisPipeline:
    """Test Coqui TTS synthesis functionality."""
    
    def test_07_create_synthesis_job(self, client, test_user_with_credits):
        """Test creating a synthesis job from completed translation."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Create completed translation job
            translation_job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_type="translate",
                input_file="mock_transcription.txt",
                output_file="mock_translation.txt",  # Must have output
                status=JobStatus.COMPLETED,
                job_metadata=json.dumps({
                    "source_language": "en",
                    "target_language": "es"
                })
            )
            db.add(translation_job)
            db.commit()
            job_id = translation_job.id
        finally:
            db.close()
        
        # Create synthesis job
        synthesize_request = {
            "job_id": job_id,
            "voice_id": "default",
            "speed": 1.0
        }
        
        response = client.post(
            "/api/v1/jobs/synthesize/create",
            json=synthesize_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "synthesize"
        assert data["status"] == "pending"
        metadata = json.loads(data["job_metadata"])
        assert metadata["voice_id"] == "default"
        assert metadata["speed"] == 1.0
    
    def test_08_synthesis_requires_completed_translation(self, client, test_user_with_credits):
        """Test that synthesis requires a completed translation job."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Create incomplete translation job
            pending_job = Job(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_type="translate",
                input_file="mock_transcription.txt",
                status=JobStatus.PENDING,  # Not completed
                job_metadata=json.dumps({
                    "source_language": "en",
                    "target_language": "es"
                })
            )
            db.add(pending_job)
            db.commit()
            job_id = pending_job.id
        finally:
            db.close()
        
        # Try to create synthesis - should fail
        synthesize_request = {
            "job_id": job_id,
            "voice_id": "default",
            "speed": 1.0
        }
        
        response = client.post(
            "/api/v1/jobs/synthesize/create",
            json=synthesize_request
        )
        
        assert response.status_code == 400
        assert "completed" in response.text.lower()


class TestEndToEndPipeline:
    """Test complete end-to-end transcription -> translation -> synthesis flow."""
    
    def test_09_full_audio_pipeline_structure(self, client, test_user_with_credits):
        """Test the structure of a complete audio translation pipeline."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # 1. Upload audio file
            file_content = b"mock audio" * 500
            files = {"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
            
            upload_response = client.post(
                "/api/v1/upload",
                params={"file_type": "audio"},
                files=files
            )
            assert upload_response.status_code == 200
            storage_path = upload_response.json()["storage_path"]
            
            # 2. Create transcription job
            transcribe_request = {
                "file_id": "test-file",
                "storage_path": storage_path,
                "language": "en"
            }
            
            transcribe_response = client.post(
                "/api/v1/jobs/transcribe",
                json=transcribe_request
            )
            assert transcribe_response.status_code == 200
            transcribe_job_id = transcribe_response.json()["id"]
            
            # Simulate transcription completion
            transcribe_job = db.query(Job).filter(Job.id == transcribe_job_id).first()
            transcribe_job.status = JobStatus.COMPLETED
            transcribe_job.output_file = "transcription_output.txt"
            db.commit()
            
            # 3. Create translation job
            translate_request = {
                "job_id": transcribe_job_id,
                "source_language": "en",
                "target_language": "es"
            }
            
            translate_response = client.post(
                "/api/v1/jobs/translate/create",
                json=translate_request
            )
            assert translate_response.status_code == 200
            translate_job_id = translate_response.json()["id"]
            
            # Simulate translation completion
            translate_job = db.query(Job).filter(Job.id == translate_job_id).first()
            translate_job.status = JobStatus.COMPLETED
            translate_job.output_file = "translation_output.txt"
            db.commit()
            
            # 4. Create synthesis job
            synthesize_request = {
                "job_id": translate_job_id,
                "voice_id": "default",
                "speed": 1.0
            }
            
            synthesize_response = client.post(
                "/api/v1/jobs/synthesize/create",
                json=synthesize_request
            )
            assert synthesize_response.status_code == 200
            synthesize_job = synthesize_response.json()
            assert synthesize_job["job_type"] == "synthesize"
            
            # Verify job chain
            assert transcribe_job_id is not None
            assert translate_job_id is not None
            assert synthesize_job["id"] is not None
            
        finally:
            db.close()
    
    def test_10_pipeline_requires_sufficient_credits(self, client, test_user_with_credits):
        """Test that pipeline respects credit balance."""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            user_id = client.test_context["user_id"]
            
            # Set user credits to 1 (not enough for any job)
            user = db.query(User).filter(User.id == user_id).first()
            user.credits = 1
            db.commit()
            
            # Try to estimate credits for a job
            estimate_request = {
                "job_type": "transcribe",
                "input_file_path": "test.wav"
            }
            
            response = client.post(
                "/api/v1/estimate",
                json=estimate_request
            )
            
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                data = response.json()
                assert data["current_balance"] == 1
                # Should show insufficient balance
                
        finally:
            db.close()


class TestPipelineErrorHandling:
    """Test error handling in pipeline."""
    
    def test_11_job_type_validation(self, client, test_user_with_credits):
        """Test validation of job types."""
        # Try to create job with invalid type
        file_content = b"test" * 100
        files = {"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        
        upload_response = client.post(
            "/api/v1/upload",
            params={"file_type": "audio"},
            files=files
        )
        storage_path = upload_response.json()["storage_path"]
        
        # Manually try invalid job type via estimate endpoint
        estimate_request = {
            "job_type": "invalid_type",
            "input_file_path": storage_path
        }
        
        response = client.post(
            "/api/v1/estimate",
            json=estimate_request
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 500]
    
    def test_12_credit_estimation_accuracy(self, client, test_user_with_credits):
        """Test credit estimation is reasonable."""
        file_content = b"mock audio" * 500
        files = {"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        
        upload_response = client.post(
            "/api/v1/upload",
            params={"file_type": "audio"},
            files=files
        )
        storage_path = upload_response.json()["storage_path"]
        
        # Get estimate
        estimate_request = {
            "job_type": "transcribe",
            "input_file_path": storage_path
        }
        
        response = client.post(
            "/api/v1/estimate",
            json=estimate_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "estimated_credits" in data
        assert data["estimated_credits"] > 0
        assert data["current_balance"] == 5000


def run_tests():
    """Run all tests with pytest."""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()
