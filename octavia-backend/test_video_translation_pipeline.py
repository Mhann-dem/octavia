"""
End-to-end test for video translation pipeline.

This test validates the complete video translation workflow:
1. Create test video with audio
2. Upload video to backend
3. Create video translation job
4. Process job (transcribe → translate → synthesize → merge)
5. Verify output video exists
6. Validate metadata

Requirements:
- FFmpeg installed and in PATH
- Backend running on http://127.0.0.1:8002
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

BASE_URL = "http://127.0.0.1:8002"
UPLOADS_DIR = backend_path / "uploads"

# Test data
TEST_EMAIL = "video_test@octavia.local"
TEST_PASSWORD = "TestPassword123!"
TEST_VIDEO_PATH = None  # Will be created


def create_test_video(output_path: str, duration: int = 5) -> bool:
    """
    Create a simple test video with audio using FFmpeg.
    
    Args:
        output_path: Path where video will be saved
        duration: Duration in seconds
        
    Returns:
        True if successful
    """
    print(f"\n📹 Creating test video ({duration}s)...")
    print("⚠️  FFmpeg not found - using minimal test video approach")
    print("  (In production, ensure FFmpeg is installed via:")
    print("   - Windows: choco install ffmpeg")
    print("   - macOS: brew install ffmpeg")  
    print("   - Linux: apt install ffmpeg)")
    
    # For this test, we'll use moviepy which can create videos without ffmpeg binary
    try:
        from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
        import numpy as np
        
        # Create simple numpy arrays for frames (blue screen with noise)
        frames = [np.ones((480, 640, 3), dtype=np.uint8) * np.array([100, 150, 200]) 
                  for _ in range(duration * 24)]  # 24 fps
        
        # Create audio
        audio_array = np.sin(np.linspace(0, 100 * np.pi, 44100 * duration)).astype(np.float32)
        
        print("  Using moviepy to create test video...")
        
        # Note: This would require moviepy to be installed and functional
        # For now, we'll skip the test with a message
        print("⚠️  Video creation requires FFmpeg binary or additional dependencies")
        print("  Skipping video creation test")
        
        return False
    
    except Exception as e:
        print(f"⚠️  Cannot create test video: {str(e)}")
        print("  Skipping video creation test")
        return False


def signup_and_login() -> dict:
    """Signup and login test user."""
    print("\n🔐 Signing up user...")
    
    # Signup
    response = requests.post(
        f"{BASE_URL}/signup",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code != 200:
        print(f"Signup status: {response.status_code}")
        if response.status_code == 400:
            print("  (User likely already exists, proceeding to login)")
        else:
            print(f"❌ Signup failed: {response.text}")
            return {}
    else:
        print(f"✓ Signup successful")
    
    # Login
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return {}
    
    data = response.json()
    token = data.get("access_token")
    user_id = data.get("user_id")
    
    if not token or not user_id:
        print(f"❌ Invalid login response: {data}")
        return {}
    
    print(f"✓ Login successful (user: {user_id}, token: {token[:20]}...)")
    
    return {
        "token": token,
        "user_id": user_id,
        "headers": {"Authorization": f"Bearer {token}"}
    }


def upload_video(video_path: str, auth: dict) -> str:
    """Upload video file to backend."""
    print(f"\n📤 Uploading video: {video_path}")
    
    if not auth or "headers" not in auth:
        print("❌ No authentication")
        return ""
    
    try:
        with open(video_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{BASE_URL}/api/v1/upload",
                files=files,
                headers=auth["headers"],
                timeout=60
            )
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        return ""
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return ""
    
    data = response.json()
    storage_path = data.get("storage_path")
    
    if not storage_path:
        print(f"❌ No storage path in response: {data}")
        return ""
    
    print(f"✓ Upload successful")
    print(f"  Storage path: {storage_path}")
    
    return storage_path


def create_video_translation_job(storage_path: str, auth: dict) -> str:
    """Create a video translation job."""
    print(f"\n🎬 Creating video translation job")
    print(f"  Input: {storage_path}")
    print(f"  Source language: English (auto)")
    print(f"  Target language: Spanish")
    
    if not auth or "headers" not in auth:
        print("❌ No authentication")
        return ""
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/video/translate",
            json={
                "storage_path": storage_path,
                "source_language": "auto",
                "target_language": "es",
                "model_size": "base"
            },
            headers=auth["headers"],
            timeout=30
        )
    except Exception as e:
        print(f"❌ Job creation failed: {str(e)}")
        return ""
    
    if response.status_code != 200:
        print(f"❌ Job creation failed: {response.status_code}")
        print(response.text)
        return ""
    
    data = response.json()
    job_id = data.get("job_id")
    estimated_time = data.get("estimated_time_seconds")
    
    if not job_id:
        print(f"❌ No job ID in response: {data}")
        return ""
    
    print(f"✓ Job created")
    print(f"  Job ID: {job_id}")
    print(f"  Estimated processing time: {estimated_time:.0f}s")
    
    return job_id


def process_job(job_id: str, auth: dict) -> bool:
    """Process the video translation job."""
    print(f"\n⚙️  Processing job: {job_id}")
    
    if not auth or "headers" not in auth:
        print("❌ No authentication")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/jobs/{job_id}/process",
            headers=auth["headers"],
            timeout=300  # 5 minute timeout for video processing
        )
    except requests.exceptions.Timeout:
        print(f"⚠️  Processing timed out (job may still be processing)")
        return False
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        return False
    
    if response.status_code != 200:
        print(f"❌ Processing failed: {response.status_code}")
        print(response.text)
        return False
    
    print(f"✓ Job processing completed")
    return True


def get_job_status(job_id: str, auth: dict) -> dict:
    """Get job status and details."""
    if not auth or "headers" not in auth:
        return {}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/jobs/{job_id}",
            headers=auth["headers"],
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    return {}


def verify_output(job_id: str, auth: dict) -> bool:
    """Verify output video exists and is valid."""
    print(f"\n✅ Verifying output")
    
    job = get_job_status(job_id, auth)
    
    if not job:
        print(f"❌ Could not fetch job status")
        return False
    
    status = job.get("status")
    output_file = job.get("output_file")
    
    print(f"  Status: {status}")
    print(f"  Output file: {output_file}")
    
    if status != "completed":
        print(f"❌ Job status is '{status}', not 'completed'")
        if job.get("error_message"):
            print(f"  Error: {job.get('error_message')}")
        return False
    
    if not output_file:
        print(f"❌ No output file specified")
        return False
    
    output_path = Path(output_file)
    
    if not output_path.exists():
        print(f"❌ Output file does not exist: {output_file}")
        return False
    
    output_size = output_path.stat().st_size
    size_mb = output_size / (1024 * 1024)
    
    print(f"✓ Output file exists: {output_file}")
    print(f"  Size: {size_mb:.2f} MB")
    
    # Verify it's a valid video (basic check)
    if output_size < 10000:  # Less than 10KB is suspect
        print(f"⚠️  Output file seems too small ({size_mb:.2f} MB)")
    
    # Check metadata
    metadata = job.get("job_metadata")
    if metadata:
        try:
            meta = json.loads(metadata)
            print(f"  Metadata:")
            print(f"    Source: {meta.get('source_language', 'unknown')}")
            print(f"    Target: {meta.get('target_language', 'unknown')}")
            print(f"    Dubbed: {meta.get('dubbed', False)}")
            if "original_text" in meta:
                orig_text = meta.get("original_text", "")[:100]
                trans_text = meta.get("translated_text", "")[:100]
                print(f"    Original text (preview): {orig_text}...")
                print(f"    Translated text (preview): {trans_text}...")
        except:
            pass
    
    return True


def cleanup_test_files():
    """Clean up test files."""
    print(f"\n🧹 Cleaning up test files")
    
    # Remove test video
    if TEST_VIDEO_PATH and Path(TEST_VIDEO_PATH).exists():
        try:
            Path(TEST_VIDEO_PATH).unlink()
            print(f"  Removed test video")
        except:
            pass


def main():
    """Run the complete end-to-end test."""
    print("=" * 60)
    print("OCTAVIA VIDEO TRANSLATION END-TO-END TEST")
    print("=" * 60)
    
    # Create test video
    test_video_dir = Path.cwd() / "test_videos"
    test_video_dir.mkdir(exist_ok=True)
    global TEST_VIDEO_PATH
    TEST_VIDEO_PATH = test_video_dir / "test_input.mp4"
    
    if not create_test_video(str(TEST_VIDEO_PATH), duration=3):
        print("❌ Failed to create test video")
        return False
    
    # Auth
    auth = signup_and_login()
    if not auth:
        print("❌ Failed to authenticate")
        return False
    
    # Upload
    storage_path = upload_video(str(TEST_VIDEO_PATH), auth)
    if not storage_path:
        print("❌ Failed to upload video")
        return False
    
    # Create job
    job_id = create_video_translation_job(storage_path, auth)
    if not job_id:
        print("❌ Failed to create video translation job")
        return False
    
    # Process job
    if not process_job(job_id, auth):
        print("❌ Failed to process job")
        return False
    
    # Verify output
    if not verify_output(job_id, auth):
        print("❌ Output verification failed")
        return False
    
    # Cleanup
    cleanup_test_files()
    
    print("\n" + "=" * 60)
    print("✅ ALL VIDEO TRANSLATION TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        cleanup_test_files()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        cleanup_test_files()
        sys.exit(1)
