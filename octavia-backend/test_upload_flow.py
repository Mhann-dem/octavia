#!/usr/bin/env python3
"""Test file upload and job creation endpoints."""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://localhost:8001"

# Test data
TEST_EMAIL = "uploadtest@example.com"
TEST_PASSWORD = "TestPassword123!"

def make_request(method, endpoint, data=None, headers=None, file_data=None, file_name=None):
    """Make HTTP request and return JSON response."""
    url = BASE_URL + endpoint
    if headers is None:
        headers = {}
    
    if data and not file_data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            try:
                return response.status, json.loads(response.read().decode('utf-8'))
            except:
                return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {"error": str(e)}

def test_upload_flow():
    """Test signup -> upload -> job creation flow."""
    
    print("=" * 70)
    print("TESTING FILE UPLOAD AND JOB FLOW")
    print("=" * 70)
    
    # 1. Signup
    print(f"\n1. SIGNUP")
    status, resp = make_request("POST", "/signup", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if status != 200:
        print(f"   ✗ Signup failed: {status}")
        return False
    
    user_id = resp["user"]["id"]
    verify_url = resp.get("verify_url", "")
    
    if not verify_url:
        print("   ✗ No verify_url returned")
        return False
    
    # Extract token
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(verify_url)
        token = parse_qs(parsed.query).get("token", [None])[0]
    except:
        print("   ✗ Could not extract token")
        return False
    
    print(f"   ✓ User created: {user_id}")
    
    # 2. Verify email
    print(f"\n2. VERIFY EMAIL")
    status, resp = make_request("GET", f"/verify?token={token}")
    if status != 200:
        print(f"   ✗ Verify failed: {status}")
        return False
    print(f"   ✓ Email verified")
    
    # 3. Login
    print(f"\n3. LOGIN")
    status, resp = make_request("POST", "/login", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if status != 200:
        print(f"   ✗ Login failed: {status}")
        return False
    
    access_token = resp["access_token"]
    print(f"   ✓ Logged in, access_token: {access_token[:20]}...")
    
    # 4. Upload file
    print(f"\n4. UPLOAD FILE")
    auth_header = f"Bearer {access_token}"
    
    # Create a test audio file (small MP3 header)
    test_audio = b'\xFF\xFB\x90\x00' + b'\x00' * 1000  # Minimal MP3 header + padding
    
    # Use multipart form-data for file upload
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="test.mp3"\r\n'
        f'Content-Type: audio/mpeg\r\n\r\n'
    ).encode() + test_audio + f'\r\n--{boundary}--\r\n'.encode()
    
    url = BASE_URL + "/api/v1/upload?file_type=audio"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            upload_resp = json.loads(response.read().decode('utf-8'))
            print(f"   ✓ File uploaded")
            print(f"     - File ID: {upload_resp['file_id']}")
            print(f"     - Size: {upload_resp['size_bytes']} bytes")
            print(f"     - Storage path: {upload_resp['storage_path']}")
            file_id = upload_resp['file_id']
    except urllib.error.HTTPError as e:
        error = e.read().decode('utf-8')
        print(f"   ✗ Upload failed: {e.code} - {error}")
        return False
    
    # 5. Create transcription job
    print(f"\n5. CREATE TRANSCRIPTION JOB")
    status, resp = make_request("POST", "/api/v1/jobs/transcribe", {
        "file_id": file_id,
        "language": "en"
    }, {"Authorization": auth_header, "Content-Type": "application/json"})
    
    if status != 200:
        print(f"   ✗ Job creation failed: {status}")
        print(f"     Response: {resp}")
        return False
    
    job_id = resp["id"]
    print(f"   ✓ Job created")
    print(f"     - Job ID: {job_id}")
    print(f"     - Status: {resp['status']}")
    print(f"     - Job Type: {resp['job_type']}")
    
    # 6. Get job status
    print(f"\n6. GET JOB STATUS")
    status, resp = make_request("GET", f"/api/v1/jobs/{job_id}", 
        headers={"Authorization": auth_header})
    
    if status != 200:
        print(f"   ✗ Get job failed: {status}")
        return False
    
    print(f"   ✓ Job retrieved")
    print(f"     - Status: {resp['status']}")
    print(f"     - Created at: {resp['created_at']}")
    
    # 7. List jobs
    print(f"\n7. LIST JOBS")
    status, resp = make_request("GET", "/api/v1/jobs",
        headers={"Authorization": auth_header})
    
    if status != 200:
        print(f"   ✗ List jobs failed: {status}")
        return False
    
    print(f"   ✓ Jobs listed")
    print(f"     - Total jobs: {len(resp)}")
    if resp:
        print(f"     - Latest job: {resp[0]['job_type']} ({resp[0]['status']})")
    
    print("\n" + "=" * 70)
    print("✓ FILE UPLOAD & JOB FLOW TEST PASSED")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_upload_flow()
    sys.exit(0 if success else 1)
