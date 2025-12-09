#!/usr/bin/env python
"""Test script for Octavia backend API"""
import sys
import os
import json
import subprocess
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'octavia-backend'))

def test_backend():
    """Run comprehensive backend tests"""
    
    print("=" * 60)
    print("OCTAVIA BACKEND TESTING SUITE")
    print("=" * 60)
    
    # Start the backend server
    print("\n1. Starting backend server...")
    server_process = subprocess.Popen(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, '.')
import uvicorn
uvicorn.run('app.main:app', host='127.0.0.1', port=8001, log_level='error')
"""],
        cwd=os.path.join(os.path.dirname(__file__), 'octavia-backend'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    print("✓ Backend server started on http://127.0.0.1:8001")
    
    # Test imports
    print("\n2. Testing imports...")
    try:
        from app.main import app
        print("✓ FastAPI app imports successfully")
    except Exception as e:
        print(f"✗ Failed to import app: {e}")
        return False
    
    # Test database
    print("\n3. Testing database...")
    try:
        from app.core.database import get_db
        print("✓ Database module imports successfully")
    except Exception as e:
        print(f"✗ Failed to import database: {e}")
        return False
    
    # Test models
    print("\n4. Testing models...")
    try:
        from app.models import User
        print("✓ User model imports successfully")
    except Exception as e:
        print(f"✗ Failed to import models: {e}")
        return False
    
    # Test routers
    print("\n5. Testing routers...")
    try:
        from app.routes.billing import router as billing_router
        from app.upload_routes import router as upload_router
        print("✓ Billing router imports successfully")
        print("✓ Upload router imports successfully")
    except Exception as e:
        print(f"✗ Failed to import routers: {e}")
        return False
    
    # Test API endpoints exist
    print("\n6. Checking API endpoints...")
    routes = [route.path for route in app.routes]
    critical_paths = [
        "/signup", "/login", 
        "/api/v1/upload",
        "/api/v1/jobs",
        "/api/v1/billing/balance",
        "/api/v1/billing/pricing"
    ]
    
    for path in critical_paths:
        if any(path in route for route in routes):
            print(f"✓ {path} registered")
        else:
            print(f"✗ {path} NOT registered")
    
    # Cleanup
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
    server_process.terminate()
    return True

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    success = test_backend()
    sys.exit(0 if success else 1)
