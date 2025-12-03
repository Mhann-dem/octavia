#!/usr/bin/env python3
import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3000"

def make_request(method, endpoint, data=None):
    """Make HTTP request and return JSON response."""
    url = BASE_URL + endpoint
    headers = {"Content-Type": "application/json"}
    
    if data:
        data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {"error": str(e)}

def test_auth_flow():
    """Test complete signup -> verify -> login flow."""
    email = "testuser@example.com"
    password = "SecurePassword123!"
    
    print("=" * 60)
    print("TESTING AUTH FLOW")
    print("=" * 60)
    
    # 1. Signup
    print(f"\n1. SIGNUP (email={email})")
    status, resp = make_request("POST", "/signup", {"email": email, "password": password})
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(resp, indent=2)}")
    
    if status != 200:
        print("   ✗ SIGNUP FAILED")
        return False
    
    user = resp.get("user", {})
    user_id = user.get("id")
    verify_url = resp.get("verify_url")
    
    if not user_id or not verify_url:
        print("   ✗ No user_id or verify_url in response")
        return False
    
    print(f"   ✓ User created: {user_id}")
    
    # Extract token from verify_url
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(verify_url)
        token = parse_qs(parsed.query).get("token", [None])[0]
    except:
        print("   ✗ Could not extract token from verify_url")
        return False
    
    if not token:
        print("   ✗ No token in verify_url")
        return False
    
    print(f"   ✓ Extracted verify token: {token[:20]}...")
    
    # 2. Verify
    print(f"\n2. VERIFY (token={token[:20]}...)")
    status, resp = make_request("GET", f"/verify?token={token}", None)
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(resp, indent=2)}")
    
    if status != 200:
        print("   ✗ VERIFY FAILED")
        return False
    
    print("   ✓ Email verified")
    
    # 3. Login
    print(f"\n3. LOGIN (email={email})")
    status, resp = make_request("POST", "/login", {"email": email, "password": password})
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(resp, indent=2)}")
    
    if status != 200:
        print("   ✗ LOGIN FAILED")
        return False
    
    access_token = resp.get("access_token")
    if not access_token:
        print("   ✗ No access_token in response")
        return False
    
    print(f"   ✓ Login successful")
    print(f"   ✓ Access token: {access_token[:20]}...")
    
    print("\n" + "=" * 60)
    print("✓ AUTH FLOW TEST PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_auth_flow()
    sys.exit(0 if success else 1)
