"""Test the transcription workflow end-to-end."""
import requests
import json
import time
import uuid
from pathlib import Path

BASE_URL = "http://localhost:8001"

# Test credentials with random email
TEST_EMAIL = f"test_whisper_{str(uuid.uuid4())[:8]}@example.com"
TEST_PASSWORD = "TestPass123!"

def test_transcription_workflow():
    print("\n" + "="*60)
    print("TESTING TRANSCRIPTION WORKFLOW")
    print("="*60)
    
    session = requests.Session()
    
    # 1. Create test audio file (simple WAV format)
    print("\n1. Creating test audio file...")
    
    # Create a minimal WAV file (440 Hz sine wave, 2 seconds)
    # WAV header for 44100 Hz, 16-bit mono
    import struct
    
    sample_rate = 44100
    duration = 2  # seconds
    frequency = 440  # Hz
    
    samples = []
    for i in range(sample_rate * duration):
        sample = int(32767 * 0.3 * __import__('math').sin(2 * __import__('math').pi * frequency * i / sample_rate))
        samples.append(sample)
    
    # WAV header
    num_samples = len(samples)
    byte_rate = sample_rate * 2  # 16-bit
    
    wav_data = b'RIFF'
    wav_data += struct.pack('<I', 36 + num_samples * 2)
    wav_data += b'WAVE'
    wav_data += b'fmt '
    wav_data += struct.pack('<I', 16)  # subchunk1 size
    wav_data += struct.pack('<H', 1)   # audio format (PCM)
    wav_data += struct.pack('<H', 1)   # num channels
    wav_data += struct.pack('<I', sample_rate)
    wav_data += struct.pack('<I', byte_rate)
    wav_data += struct.pack('<H', 2)   # block align
    wav_data += struct.pack('<H', 16)  # bits per sample
    wav_data += b'data'
    wav_data += struct.pack('<I', num_samples * 2)
    
    for sample in samples:
        wav_data += struct.pack('<h', sample)
    
    # Save test audio file
    test_audio_path = Path("test_audio.wav")
    with open(test_audio_path, 'wb') as f:
        f.write(wav_data)
    
    print(f"   ✓ Created test audio file: {test_audio_path} ({len(wav_data)} bytes)")
    
    # 2. Signup
    print("\n2. Signup...")
    signup_response = session.post(
        f"{BASE_URL}/signup",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    print(f"   Status: {signup_response.status_code}")
    if signup_response.status_code != 200:
        print(f"   ERROR: {signup_response.text}")
        return False
    
    signup_data = signup_response.json()
    user_id = signup_data["user"]["id"]
    verify_url = signup_data.get("verify_url", "")
    print(f"   User ID: {user_id}")
    
    # 3. Verify email
    print("\n3. Verify email...")
    # Extract the token from the verify URL
    verify_token = verify_url.split("token=")[-1] if "token=" in verify_url else ""
    if not verify_token:
        print(f"   ERROR: Could not extract verification token from URL: {verify_url}")
        return False
    
    # Use the backend verify endpoint directly
    verify_response = session.get(f"{BASE_URL}/verify?token={verify_token}")
    print(f"   Status: {verify_response.status_code}")
    if verify_response.status_code != 200:
        print(f"   ERROR: {verify_response.text}")
        return False
    print("   ✓ Email verified")
    
    # 4. Login
    print("\n4. Login...")
    login_response = session.post(
        f"{BASE_URL}/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    print(f"   Status: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"   ERROR: {login_response.text}")
        return False
    
    login_data = login_response.json()
    access_token = login_data["access_token"]
    print(f"   ✓ Logged in, token: {access_token[:20]}...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 5. Upload audio file
    print("\n5. Upload audio file...")
    with open(test_audio_path, 'rb') as f:
        upload_response = session.post(
            f"{BASE_URL}/api/v1/upload?file_type=audio",
            files={"file": ("test_audio.wav", f, "audio/wav")},
            headers=headers
        )
    
    print(f"   Status: {upload_response.status_code}")
    if upload_response.status_code != 200:
        print(f"   ERROR: {upload_response.text}")
        return False
    
    upload_data = upload_response.json()
    file_id = upload_data["file_id"]
    storage_path = upload_data["storage_path"]
    print(f"   ✓ File uploaded")
    print(f"   File ID: {file_id}")
    print(f"   Storage path: {storage_path}")
    
    # 6. Create transcription job
    print("\n6. Create transcription job...")
    job_response = session.post(
        f"{BASE_URL}/api/v1/jobs/transcribe",
        json={"file_id": file_id, "storage_path": storage_path, "language": None},
        headers=headers
    )
    
    print(f"   Status: {job_response.status_code}")
    if job_response.status_code != 200:
        print(f"   ERROR: {job_response.text}")
        return False
    
    job_data = job_response.json()
    job_id = job_data["id"]
    print(f"   ✓ Job created")
    print(f"   Job ID: {job_id}")
    print(f"   Status: {job_data['status']}")
    
    # 7. Process job (run transcription)
    print("\n7. Processing transcription job...")
    print("   (This may take a minute or two for first run - downloading Whisper model...)")
    
    process_response = session.post(
        f"{BASE_URL}/api/v1/jobs/{job_id}/process",
        headers=headers
    )
    
    print(f"   Status: {process_response.status_code}")
    if process_response.status_code != 200:
        print(f"   ERROR: {process_response.text}")
        return False
    
    process_data = process_response.json()
    print(f"   ✓ Processing complete")
    print(f"   Job status: {process_data['status']}")
    print(f"   Output file: {process_data.get('output_file', 'N/A')}")
    
    if process_data['status'] == 'completed' and process_data.get('output_file'):
        # 8. Read transcription results
        print("\n8. Reading transcription results...")
        output_file = process_data['output_file']
        
        if Path(output_file).exists():
            with open(output_file, 'r') as f:
                transcript = json.load(f)
            
            print(f"   ✓ Transcription file found")
            print(f"   Detected language: {transcript.get('language', 'unknown')}")
            print(f"   Transcription text: {transcript.get('text', '(empty)')[:100]}...")
            print(f"   Audio duration: {transcript.get('duration', 0):.2f}s")
            print(f"   Model size: {transcript.get('model_size', 'unknown')}")
        else:
            print(f"   ERROR: Output file not found at {output_file}")
            return False
    else:
        print(f"   ERROR: Job failed with status: {process_data.get('status')}")
        if process_data.get('error_message'):
            print(f"   Error: {process_data['error_message']}")
        return False
    
    # 9. Get job status again to verify
    print("\n9. Verifying job status...")
    verify_job_response = session.get(
        f"{BASE_URL}/api/v1/jobs/{job_id}",
        headers=headers
    )
    
    print(f"   Status: {verify_job_response.status_code}")
    if verify_job_response.status_code != 200:
        print(f"   ERROR: {verify_job_response.text}")
        return False
    
    verify_job_data = verify_job_response.json()
    print(f"   ✓ Job verification")
    print(f"   Final status: {verify_job_data['status']}")
    
    # 10. List all jobs
    print("\n10. Listing all user jobs...")
    list_response = session.get(
        f"{BASE_URL}/api/v1/jobs",
        headers=headers
    )
    
    print(f"   Status: {list_response.status_code}")
    if list_response.status_code != 200:
        print(f"   ERROR: {list_response.text}")
        return False
    
    jobs_list = list_response.json()
    print(f"   ✓ Retrieved {len(jobs_list)} job(s)")
    for job in jobs_list:
        print(f"     - Job {job['id']}: {job['job_type']} ({job['status']})")
    
    # Cleanup
    print("\n11. Cleanup...")
    test_audio_path.unlink()
    print(f"   ✓ Removed test audio file")
    
    print("\n" + "="*60)
    print("✓ TRANSCRIPTION WORKFLOW TEST PASSED")
    print("="*60 + "\n")
    return True


if __name__ == "__main__":
    try:
        success = test_transcription_workflow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
