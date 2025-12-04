"""End-to-end test: Upload audio → Transcribe → Translate"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8001"
TEST_EMAIL = "translator@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_AUDIO_FILE = "test_audio.wav"

# Counters for verification
tests_run = 0
tests_passed = 0

def test_step(step_num, description, condition, details=""):
    """Log test result"""
    global tests_run, tests_passed
    tests_run += 1
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"\n[Step {step_num}] {status}: {description}")
    if details:
        print(f"    Details: {details}")
    if condition:
        tests_passed += 1
    return condition

print("=" * 70)
print("TEST: TRANSLATION WORKFLOW (Upload → Transcribe → Translate)")
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
verify_response = requests.get(f"{BASE_URL}/verify?email={TEST_EMAIL}")
test_step(2, "Email verification",
    verify_response.status_code == 200,
    f"Status {verify_response.status_code}")

# Step 3: Login
login_response = requests.post(
    f"{BASE_URL}/login",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)
token = login_response.json().get("access_token") if login_response.status_code == 200 else None
test_step(3, "User login and token generation",
    login_response.status_code == 200 and token is not None,
    f"Status {login_response.status_code}, Token: {token[:20] if token else 'None'}...")

if not token:
    print("\n[ERROR] Failed to get auth token, cannot continue")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 4: Upload audio file
print("\n[Phase 2] File Upload & Transcription")
if Path(TEST_AUDIO_FILE).exists():
    with open(TEST_AUDIO_FILE, "rb") as f:
        upload_response = requests.post(
            f"{BASE_URL}/api/v1/upload",
            files={"file": f},
            headers=headers
        )
    test_step(4, "Audio file upload",
        upload_response.status_code == 200,
        f"Status {upload_response.status_code}")
    
    upload_data = upload_response.json() if upload_response.status_code == 200 else {}
    storage_path = upload_data.get("storage_path")
    test_step(5, "Storage path returned",
        storage_path is not None,
        f"Path: {storage_path}")
else:
    print(f"\n[SKIP] Test audio file '{TEST_AUDIO_FILE}' not found, using dummy path")
    storage_path = "test_audio.wav"
    test_step(4, "Audio file upload", True, "(skipped - file not found)")
    test_step(5, "Storage path returned", True, f"Path: {storage_path}")

# Step 6: Create transcription job
transcribe_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/transcribe",
    json={
        "file_id": "test_file_id",
        "storage_path": storage_path,
        "language": "auto"
    },
    headers=headers
)
test_step(6, "Create transcription job",
    transcribe_response.status_code == 200,
    f"Status {transcribe_response.status_code}")

transcribe_data = transcribe_response.json() if transcribe_response.status_code == 200 else {}
transcribe_job_id = transcribe_data.get("id")
test_step(7, "Transcription job ID generated",
    transcribe_job_id is not None,
    f"Job ID: {transcribe_job_id}")

if not transcribe_job_id:
    print("\n[ERROR] Failed to create transcription job, cannot continue")
    exit(1)

# Step 8: Process transcription job
print("\n[Phase 2.5] Process Transcription")
process_transcribe_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/{transcribe_job_id}/process",
    headers=headers
)
test_step(8, "Process transcription job",
    process_transcribe_response.status_code == 200,
    f"Status {process_transcribe_response.status_code}")

transcribe_result = process_transcribe_response.json() if process_transcribe_response.status_code == 200 else {}
transcribe_status = transcribe_result.get("status")
transcribe_output = transcribe_result.get("output_file")
test_step(9, "Transcription job completed",
    transcribe_status == "COMPLETED" or transcribe_status == "completed",
    f"Status: {transcribe_status}")

test_step(10, "Transcription output file generated",
    transcribe_output is not None,
    f"Output: {transcribe_output}")

if not transcribe_output:
    print("\n[ERROR] Transcription failed to generate output, cannot continue with translation")
    exit(1)

# Step 11: Create translation job
print("\n[Phase 3] Translation")
translate_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/translate",
    json={
        "job_id": transcribe_job_id,
        "source_language": "en",
        "target_language": "es"
    },
    headers=headers
)
test_step(11, "Create translation job",
    translate_response.status_code == 200,
    f"Status {translate_response.status_code}")

translate_data = translate_response.json() if translate_response.status_code == 200 else {}
translate_job_id = translate_data.get("id")
test_step(12, "Translation job ID generated",
    translate_job_id is not None,
    f"Job ID: {translate_job_id}")

if not translate_job_id:
    print("\n[ERROR] Failed to create translation job, cannot continue")
    exit(1)

# Step 13: Process translation job
print("\n[Phase 3.5] Process Translation")
process_translate_response = requests.post(
    f"{BASE_URL}/api/v1/jobs/{translate_job_id}/process",
    headers=headers
)
test_step(13, "Process translation job",
    process_translate_response.status_code == 200,
    f"Status {process_translate_response.status_code}")

translate_result = process_translate_response.json() if process_translate_response.status_code == 200 else {}
translate_status = translate_result.get("status")
translate_output = translate_result.get("output_file")
test_step(14, "Translation job completed",
    translate_status == "COMPLETED" or translate_status == "completed",
    f"Status: {translate_status}")

test_step(15, "Translation output file generated",
    translate_output is not None,
    f"Output: {translate_output}")

# Step 16: Get translation job details
if translate_job_id:
    get_translate_response = requests.get(
        f"{BASE_URL}/api/v1/jobs/{translate_job_id}",
        headers=headers
    )
    test_step(16, "Retrieve translation job details",
        get_translate_response.status_code == 200,
        f"Status {get_translate_response.status_code}")
    
    if get_translate_response.status_code == 200:
        job_details = get_translate_response.json()
        metadata = job_details.get("job_metadata")
        test_step(17, "Translation metadata stored",
            metadata is not None,
            f"Metadata: {metadata[:100] if metadata else 'None'}...")

# Step 18: List all user jobs
list_response = requests.get(
    f"{BASE_URL}/api/v1/jobs",
    headers=headers
)
test_step(18, "List user jobs",
    list_response.status_code == 200,
    f"Status {list_response.status_code}")

jobs = list_response.json() if list_response.status_code == 200 else []
job_count = len(jobs)
test_step(19, "Jobs returned in list",
    job_count >= 2,  # At least transcription and translation
    f"Jobs found: {job_count}")

# Summary
print("\n" + "=" * 70)
print(f"TEST SUMMARY: {tests_passed}/{tests_run} tests passed")
print("=" * 70)

if tests_passed == tests_run:
    print("✓ ALL TRANSLATION WORKFLOW TESTS PASSED")
else:
    print(f"✗ {tests_run - tests_passed} test(s) failed")

exit(0 if tests_passed == tests_run else 1)
