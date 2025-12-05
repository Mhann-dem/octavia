"""
End-to-end test for video translation pipeline.
Tests the complete flow: video upload → extract → transcribe → translate → synthesize → merge

Usage:
    python test_video_translation_flow.py

Requirements:
    - Backend server running on http://127.0.0.1:8002
    - FFmpeg installed and accessible
    - Test video file (will create one if not present)
"""

import requests
import time
import json
from pathlib import Path
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8002"
TEST_EMAIL = f"video_test_{int(time.time())}@example.com"
TEST_PASSWORD = "testpass123"
TEST_VIDEO_PATH = "test_video.mp4"

# Global session
session = requests.Session()
user_token = None


def log_step(step_num, total, message):
    """Print a formatted test step."""
    print(f"\n{'='*60}")
    print(f"Step {step_num}/{total}: {message}")
    print('='*60)


def log_success(message):
    """Print success message."""
    print(f"✅ {message}")


def log_error(message):
    """Print error message."""
    print(f"❌ {message}")
    sys.exit(1)


def create_test_video():
    """Create a test video file with audio using FFmpeg."""
    log_step(0, 35, "Creating test video file")
    
    try:
        import ffmpeg
        
        # Create a 5-second test video with audio
        # Video: Color bars
        # Audio: Sine wave tone
        video_path = Path(TEST_VIDEO_PATH)
        
        if video_path.exists():
            log_success(f"Test video already exists: {video_path}")
            return str(video_path)
        
        print("Generating test video with FFmpeg...")
        
        # Generate video with color bars and audio tone
        video = ffmpeg.input('testsrc=duration=5:size=640x480:rate=30', f='lavfi')
        audio = ffmpeg.input('sine=frequency=440:duration=5', f='lavfi')
        
        out = ffmpeg.output(
            video,
            audio,
            str(video_path),
            vcodec='libx264',
            acodec='aac',
            pix_fmt='yuv420p'
        )
        
        ffmpeg.run(out, overwrite_output=True, quiet=True)
        
        if not video_path.exists():
            log_error("Failed to create test video")
        
        log_success(f"Test video created: {video_path} ({video_path.stat().st_size} bytes)")
        return str(video_path)
        
    except Exception as e:
        log_error(f"Failed to create test video: {str(e)}")


def test_signup():
    """Test user signup."""
    log_step(1, 35, "User Signup")
    
    response = session.post(
        f"{BASE_URL}/signup",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    if response.status_code != 200:
        log_error(f"Signup failed: {response.status_code} - {response.text}")
    
    data = response.json()
    log_success(f"User created: {data['user']['email']}")
    
    return data


def test_verify(verify_url):
    """Test email verification."""
    log_step(2, 35, "Email Verification")
    
    # Extract token from verify_url
    token = verify_url.split("token=")[1]
    
    response = session.get(f"{BASE_URL}/verify", params={"token": token})
    
    if response.status_code != 200:
        log_error(f"Verification failed: {response.status_code} - {response.text}")
    
    log_success("Email verified")


def test_login():
    """Test user login."""
    log_step(3, 35, "User Login")
    
    response = session.post(
        f"{BASE_URL}/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    if response.status_code != 200:
        log_error(f"Login failed: {response.status_code} - {response.text}")
    
    data = response.json()
    token = data["access_token"]
    
    # Set authorization header for all future requests
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    log_success(f"Login successful, token: {token[:20]}...")
    return token


def test_upload_video(video_path):
    """Test video file upload."""
    log_step(4, 35, "Upload Video File")
    
    with open(video_path, 'rb') as f:
        files = {'file': (Path(video_path).name, f, 'video/mp4')}
        response = session.post(
            f"{BASE_URL}/api/v1/upload",
            files=files,
            params={'file_type': 'video'}
        )
    
    if response.status_code != 200:
        log_error(f"Upload failed: {response.status_code} - {response.text}")
    
    data = response.json()
    log_success(f"Video uploaded: {data['file_id']}")
    log_success(f"Storage path: {data['storage_path']}")
    log_success(f"Size: {data['size_bytes']} bytes")
    
    return data


def test_validate_video(storage_path):
    """Test video validation."""
    log_step(5, 35, "Validate Video File")
    
    response = session.get(
        f"{BASE_URL}/api/v1/video/validate",
        params={'storage_path': storage_path}
    )
    
    if response.status_code != 200:
        log_error(f"Validation failed: {response.status_code} - {response.text}")
    
    data = response.json()
    metadata = data['metadata']
    
    log_success(f"Video validated successfully")
    log_success(f"Duration: {metadata['duration']}s")
    log_success(f"Resolution: {metadata['width']}x{metadata['height']}")
    log_success(f"Codec: {metadata['video_codec']}")
    log_success(f"Has audio: {metadata['has_audio']}")
    
    return data


def test_create_video_translation_job(storage_path):
    """Test video translation job creation."""
    log_step(6, 35, "Create Video Translation Job")
    
    response = session.post(
        f"{BASE_URL}/api/v1/video/translate",
        json={
            "storage_path": storage_path,
            "source_language": "auto",
            "target_language": "es",
            "model_size": "base"
        }
    )
    
    if response.status_code != 200:
        log_error(f"Job creation failed: {response.status_code} - {response.text}")
    
    data = response.json()
    job_id = data['job_id']
    
    log_success(f"Video translation job created: {job_id}")
    log_success(f"Status: {data['status']}")
    log_success(f"Estimated time: {data.get('estimated_time_seconds', 'N/A')}s")
    
    return job_id


def test_process_video_job(job_id):
    """Test video translation job processing."""
    log_step(7, 35, "Process Video Translation Job")
    
    print("⏳ Processing video translation (this may take 1-2 minutes)...")
    print("   Step 1/5: Extracting audio from video...")
    print("   Step 2/5: Transcribing audio with Whisper...")
    print("   Step 3/5: Translating text...")
    print("   Step 4/5: Synthesizing new audio...")
    print("   Step 5/5: Merging audio back into video...")
    
    response = session.post(f"{BASE_URL}/api/v1/jobs/{job_id}/process")
    
    if response.status_code != 200:
        log_error(f"Processing failed: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if data['status'] != 'completed':
        log_error(f"Job not completed. Status: {data['status']}, Error: {data.get('error_message')}")
    
    log_success(f"Video translation processing complete")
    log_success(f"Job ID: {data['id']}")
    log_success(f"Status: {data['status']}")
    log_success(f"Output file: {data['output_file']}")
    
    return data


def test_verify_output_video(job_data):
    """Verify the output video file exists and is valid."""
    log_step(8, 35, "Verify Output Video")
    
    output_path = Path(job_data['output_file'])
    
    if not output_path.exists():
        log_error(f"Output video file not found: {output_path}")
    
    file_size = output_path.stat().st_size
    
    log_success(f"Output video exists: {output_path}")
    log_success(f"File size: {file_size} bytes")
    
    # Parse metadata if available
    if job_data.get('job_metadata'):
        metadata = json.loads(job_data['job_metadata'])
        log_success(f"Source language: {metadata.get('source_language')}")
        log_success(f"Target language: {metadata.get('target_language')}")
        log_success(f"Detected language: {metadata.get('detected_language')}")
        
        if 'intermediate_files' in metadata:
            print("\nIntermediate files:")
            for key, path in metadata['intermediate_files'].items():
                exists = "✅" if Path(path).exists() else "❌"
                print(f"  {exists} {key}: {path}")
    
    return True


def test_list_jobs():
    """Test listing all jobs."""
    log_step(9, 35, "List All Jobs")
    
    response = session.get(f"{BASE_URL}/api/v1/jobs")
    
    if response.status_code != 200:
        log_error(f"Job listing failed: {response.status_code} - {response.text}")
    
    jobs = response.json()
    log_success(f"Found {len(jobs)} jobs")
    
    for job in jobs:
        print(f"  - {job['job_type']}: {job['status']} (ID: {job['id'][:8]}...)")
    
    return jobs


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("VIDEO TRANSLATION PIPELINE TEST")
    print("="*60)
    
    try:
        # Setup
        video_path = create_test_video()
        
        # Authentication flow
        signup_data = test_signup()
        verify_url = signup_data['verify_url']
        test_verify(verify_url)
        token = test_login()
        
        # Video upload and validation
        upload_data = test_upload_video(video_path)
        storage_path = upload_data['storage_path']
        test_validate_video(storage_path)
        
        # Video translation
        job_id = test_create_video_translation_job(storage_path)
        job_data = test_process_video_job(job_id)
        test_verify_output_video(job_data)
        
        # List all jobs
        test_list_jobs()
        
        # Final summary
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print(f"\nOutput video: {job_data['output_file']}")
        print("\nYou can now play the dubbed video to hear the translated audio!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()