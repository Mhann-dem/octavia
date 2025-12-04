"""
Test video upload and metadata extraction.
Tests the video translation foundation stage.
"""
import os
import sys
import json
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://127.0.0.1:8002"

# Test data
test_email = "video_test@example.com"
test_password = "test_password_123"
auth_token = None
user_id = None


def test_1_signup():
    """Test user signup."""
    print("\n[1/5] Testing signup...")
    response = requests.post(
        f"{BASE_URL}/signup",
        json={"email": test_email, "password": test_password}
    )
    assert response.status_code == 200, f"Signup failed: {response.text}"
    print("✓ Signup successful")


def test_2_verify():
    """Test email verification (auto-verify in test mode)."""
    print("\n[2/5] Testing verification...")
    # Get verification token from database (in test mode, we'll just skip verification)
    # For now, we'll proceed with login
    print("✓ Verification skipped (auto-verified in test)")


def test_3_login():
    """Test user login."""
    global auth_token, user_id
    print("\n[3/5] Testing login...")
    response = requests.post(
        f"{BASE_URL}/login",
        json={"email": test_email, "password": test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    auth_token = response.json()["access_token"]
    print(f"✓ Login successful, token: {auth_token[:20]}...")


def test_4_create_test_video():
    """Create a small test video file."""
    print("\n[4/5] Creating test video file...")
    
    # Create a minimal MP4 file (100 bytes of valid MP4 header)
    test_video_path = "test_video.mp4"
    
    # MP4 file signature (minimal valid file)
    mp4_header = bytes([
        0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
        0x69, 0x73, 0x6f, 0x6d, 0x00, 0x00, 0x02, 0x00,
        0x69, 0x73, 0x6f, 0x6d, 0x69, 0x73, 0x6f, 0x32,
        0x6d, 0x70, 0x34, 0x31, 0x00, 0x00, 0x00, 0x08,
        0x77, 0x69, 0x64, 0x65
    ]) + b'\x00' * 100  # Pad to make it larger
    
    with open(test_video_path, 'wb') as f:
        f.write(mp4_header)
    
    print(f"✓ Created test video: {test_video_path} ({len(mp4_header)} bytes)")
    return test_video_path


def test_5_upload_video(video_path):
    """Test video upload with metadata extraction."""
    print("\n[5/5] Testing video upload...")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    with open(video_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{BASE_URL}/api/v1/videos/upload",
            files=files,
            headers=headers
        )
    
    if response.status_code != 200:
        print(f"✗ Upload failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    print(f"✓ Video upload successful")
    print(f"  - File ID: {data['file_id']}")
    print(f"  - Filename: {data['filename']}")
    print(f"  - Size: {data['size_bytes']} bytes")
    print(f"  - Storage path: {data['storage_path']}")
    print(f"  - Metadata:")
    for key, value in data['metadata'].items():
        print(f"    - {key}: {value}")
    
    return data['file_id']


def main():
    """Run all tests."""
    print("=" * 60)
    print("VIDEO TRANSLATION FOUNDATION TEST SUITE")
    print("=" * 60)
    
    # Clean up any previous test video
    if Path("test_video.mp4").exists():
        Path("test_video.mp4").unlink()
    
    try:
        # Run auth tests
        test_1_signup()
        test_2_verify()
        test_3_login()
        
        # Create and upload test video
        video_path = test_4_create_test_video()
        file_id = test_5_upload_video(video_path)
        
        if file_id:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED!")
            print("=" * 60)
            print(f"\nVideo file ID for next step: {file_id}")
            print("Next: Create video translation job with this file ID")
        else:
            print("\n✗ Video upload test failed")
            return 1
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if Path("test_video.mp4").exists():
            Path("test_video.mp4").unlink()


if __name__ == "__main__":
    exit(main())
