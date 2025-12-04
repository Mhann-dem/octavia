"""End-to-end test: Upload audio -> Transcribe -> Translate -> Synthesize"""
import requests
import json
import time
from pathlib import Path
import uuid

BASE_URL = "http://localhost:8002"
TEST_EMAIL = f"synthesizer+{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_AUDIO_FILE = "test_audio.wav"

# Counters for verification
tests_run = 0
tests_passed = 0

def test_step(step_num, description, condition, details=""):
    """Log test result"""
    global tests_run, tests_passed
    tests_run += 1
    status = "[PASS]" if condition else "[FAIL]"
    print(f"\n[Step {step_num}] {status}: {description}")
    if details:
        print(f"    Details: {details}")
    if condition:
        tests_passed += 1
    return condition

print("=" * 70)
print("TEST: SYNTHESIS WORKFLOW (Upload -> Transcribe -> Translate -> Synthesize)")
print("=" * 70)

# Step 1: Signup
print("\n[Phase 1] Authentication")
signup_response = requests.post(
    f"{BASE_URL}/signup",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)
test_step(1, "User signup",
    signup_response.status_code == 200,
    f"Status {signup_response.status_code}")

# Step 2: Verify email
signup_data = signup_response.json() if signup_response.status_code == 200 else {}
verify_url = signup_data.get("verify_url")
from urllib.parse import urlparse, parse_qs
token = None
if verify_url:
    parsed = urlparse(verify_url)
    token = parse_qs(parsed.query).get("token", [None])[0]

verify_response = requests.get(
    f"{BASE_URL}/verify",
    params={"token": token}
)
test_step(2, "Email verification",
    verify_response.status_code == 200,
    f"Status {verify_response.status_code}")

# Step 3: Login
login_response = requests.post(
    f"{BASE_URL}/login",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)
test_step(3, "User login",
    login_response.status_code == 200,
    f"Status {login_response.status_code}")

login_data = login_response.json() if login_response.status_code == 200 else {}
access_token = login_data.get("access_token")
test_step(4, "Access token received",
    access_token is not None and len(access_token) > 0,
    f"Token length: {len(access_token) if access_token else 0}")

# Step 5: Create test audio file
print("\n[Phase 2] File Upload")
test_audio_path = Path(TEST_AUDIO_FILE)
if not test_audio_path.exists():
    # Create a simple WAV file using soundfile
    try:
        import soundfile as sf
        import numpy as np
        # 1 second of 440Hz sine wave at 16kHz
        sample_rate = 16000
        duration = 1  # seconds
        freq = 440  # Hz (A4 note)
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = 0.3 * np.sin(2 * np.pi * freq * t)
        sf.write(TEST_AUDIO_FILE, audio_data, sample_rate)
        test_step(5, "Test audio file created",
            test_audio_path.exists(),
            f"File: {test_audio_path.absolute()}")
    except Exception as e:
        test_step(5, "Test audio file created", False, f"Error: {str(e)}")
else:
    test_step(5, "Test audio file exists", True, f"Using: {test_audio_path.absolute()}")

# Step 6: Upload audio file
headers = {"Authorization": f"Bearer {access_token}"}
with open(TEST_AUDIO_FILE, "rb") as f:
    upload_response = requests.post(
        f"{BASE_URL}/api/v1/upload",
        headers=headers,
        files={"file": f},
        params={"file_type": "audio"}
    )

test_step(6, "Audio file upload",
    upload_response.status_code == 200,
    f"Status {upload_response.status_code}")

upload_data = upload_response.json() if upload_response.status_code == 200 else {}
file_id = upload_data.get("file_id")
storage_path = upload_data.get("storage_path")
test_step(7, "Upload response contains file_id",
    file_id is not None,
    f"File ID: {file_id}")

test_step(8, "Upload response contains storage_path",
    storage_path is not None,
    f"Path: {storage_path}")

# Step 9: Create transcription job
print("\n[Phase 3] Transcription")
transcribe_request = {
    "file_id": file_id,
    "storage_path": storage_path,
    "language": "auto"
}
transcribe_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/transcribe",
    headers=headers,
    json=transcribe_request
)
test_step(9, "Create transcription job",
    transcribe_response.status_code == 200,
    f"Status {transcribe_response.status_code}")

transcribe_data = transcribe_response.json() if transcribe_response.status_code == 200 else {}
transcribe_job_id = transcribe_data.get("id")
test_step(10, "Transcription job ID received",
    transcribe_job_id is not None,
    f"Job ID: {transcribe_job_id}")

# Step 10: Process transcription job
process_transcribe_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/{transcribe_job_id}/process",
    headers=headers
)
test_step(11, "Process transcription job",
    process_transcribe_response.status_code == 200,
    f"Status {process_transcribe_response.status_code}")

transcribe_result = process_transcribe_response.json() if process_transcribe_response.status_code == 200 else {}
transcribe_status = transcribe_result.get("status")
transcribe_output = transcribe_result.get("output_file")
test_step(12, "Transcription job completed",
    transcribe_status == "completed",
    f"Status: {transcribe_status}")

test_step(13, "Transcription output file generated",
    transcribe_output is not None,
    f"Output: {transcribe_output}")

# Step 11: Create translation job
print("\n[Phase 4] Translation")
translate_request = {
    "job_id": transcribe_job_id,
    "source_language": "en",
    "target_language": "es"
}
translate_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/translate/create",
    headers=headers,
    json=translate_request
)
test_step(14, "Create translation job",
    translate_response.status_code == 200,
    f"Status {translate_response.status_code}")

translate_data = translate_response.json() if translate_response.status_code == 200 else {}
translate_job_id = translate_data.get("id")
test_step(15, "Translation job ID received",
    translate_job_id is not None,
    f"Job ID: {translate_job_id}")

# Step 12: Process translation job
process_translate_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/{translate_job_id}/process",
    headers=headers
)
test_step(16, "Process translation job",
    process_translate_response.status_code == 200,
    f"Status {process_translate_response.status_code}")

translate_result = process_translate_response.json() if process_translate_response.status_code == 200 else {}
translate_status = translate_result.get("status")
translate_output = translate_result.get("output_file")
test_step(17, "Translation job completed",
    translate_status == "completed",
    f"Status: {translate_status}")

test_step(18, "Translation output file generated",
    translate_output is not None,
    f"Output: {translate_output}")

# Step 13: Create synthesis job
print("\n[Phase 5] Synthesis")
synthesize_request = {
    "job_id": translate_job_id,
    "voice_id": "default",
    "speed": 1.0
}
synthesize_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/synthesize/create",
    headers=headers,
    json=synthesize_request
)
test_step(19, "Create synthesis job",
    synthesize_response.status_code == 200,
    f"Status {synthesize_response.status_code}")

synthesize_data = synthesize_response.json() if synthesize_response.status_code == 200 else {}
synthesize_job_id = synthesize_data.get("id")
test_step(20, "Synthesis job ID received",
    synthesize_job_id is not None,
    f"Job ID: {synthesize_job_id}")

# Step 14: Process synthesis job
process_synthesize_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/{synthesize_job_id}/process",
    headers=headers
)
test_step(21, "Process synthesis job",
    process_synthesize_response.status_code == 200,
    f"Status {process_synthesize_response.status_code}")

synthesize_result = process_synthesize_response.json() if process_synthesize_response.status_code == 200 else {}
synthesize_status = synthesize_result.get("status")
synthesize_output = synthesize_result.get("output_file")
test_step(22, "Synthesis job completed",
    synthesize_status == "completed",
    f"Status: {synthesize_status}")

test_step(23, "Synthesis output file generated",
    synthesize_output is not None,
    f"Output: {synthesize_output}")

# Step 15: Verify synthesis output file exists
print("\n[Phase 6] Verification")
if synthesize_output:
    output_path = Path(synthesize_output)
    output_exists = output_path.exists()
    test_step(24, "Synthesis output file physically exists",
        output_exists,
        f"Path: {output_path}")
    
    if output_exists:
        file_size = output_path.stat().st_size
        test_step(25, "Synthesis output file has content",
            file_size > 0,
            f"Size: {file_size} bytes")

# Step 16: Verify job metadata
synthesize_metadata = synthesize_result.get("job_metadata")
test_step(26, "Synthesis job metadata present",
    synthesize_metadata is not None,
    f"Metadata: {synthesize_metadata}")

if synthesize_metadata:
    try:
        metadata_obj = json.loads(synthesize_metadata) if isinstance(synthesize_metadata, str) else synthesize_metadata
        has_language = "language" in metadata_obj
        has_text_length = "text_length" in metadata_obj
        has_synthesis_engine = "synthesis_engine" in metadata_obj
        
        test_step(27, "Synthesis metadata contains language",
            has_language,
            f"Language: {metadata_obj.get('language')}")
        
        test_step(28, "Synthesis metadata contains text_length",
            has_text_length,
            f"Text length: {metadata_obj.get('text_length')}")
        
        test_step(29, "Synthesis metadata contains synthesis_engine",
            has_synthesis_engine,
            f"Engine: {metadata_obj.get('synthesis_engine')}")
    except Exception as e:
        test_step(27, "Parse synthesis metadata", False, str(e))

# Step 17: List jobs
list_response = requests.get(
    f"{BASE_URL}/api/v1/jobs",
    headers=headers
)
test_step(30, "List jobs endpoint",
    list_response.status_code == 200,
    f"Status {list_response.status_code}")

jobs_list = list_response.json() if list_response.status_code == 200 else []
test_step(31, "Jobs list contains at least 3 jobs (transcribe, translate, synthesize)",
    len(jobs_list) >= 3,
    f"Jobs found: {len(jobs_list)}")

# Summary
print("\n" + "=" * 70)
print(f"TEST SUMMARY: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("RESULT: ALL TESTS PASSED [SUCCESS]")
else:
    print(f"RESULT: {tests_run - tests_passed} TESTS FAILED")
print("=" * 70)
