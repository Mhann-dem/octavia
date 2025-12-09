#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""End-to-End Testing for Octavia Frontend & Backend"""
import sys
import os
import json
import requests
import time
import subprocess
from datetime import datetime

# Fix unicode on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup
BACKEND_URL = "http://127.0.0.1:8001"
FRONTEND_URL = "http://localhost:3000"
TEST_USER_EMAIL = f"test_{int(time.time())}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"

class OctaviaE2ETester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def log_test(self, name, passed, details=""):
        """Log test result"""
        status = "[PASS]" if passed else "[FAIL]"
        self.tests.append({"name": name, "passed": passed, "details": details})
        print(f"\n{status}: {name}")
        if details:
            print(f"  -> {details}")
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_health_check(self):
        """Test 1: Backend Health Check"""
        try:
            response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
            passed = response.status_code == 200
            self.log_test("Backend Health Check", passed, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("Backend Health Check", False, str(e))
            return False
    
    def test_signup(self):
        """Test 2: User Signup"""
        try:
            payload = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            response = requests.post(f"{BACKEND_URL}/signup", json=payload, timeout=10)
            passed = response.status_code == 200
            
            if passed:
                data = response.json()
                self.user_id = data.get("id")
                self.log_test("User Signup", True, f"User created: {TEST_USER_EMAIL}")
            else:
                self.log_test("User Signup", False, f"Status: {response.status_code}, Response: {response.text[:100]}")
            return passed
        except Exception as e:
            self.log_test("User Signup", False, str(e))
            return False
    
    def test_login(self):
        """Test 3: User Login"""
        try:
            payload = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            response = requests.post(f"{BACKEND_URL}/login", json=payload, timeout=10)
            passed = response.status_code == 200
            
            if passed:
                data = response.json()
                self.token = data.get("access_token")
                self.log_test("User Login", True, f"Token obtained: {self.token[:20]}...")
            else:
                self.log_test("User Login", False, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("User Login", False, str(e))
            return False
    
    def test_billing_balance(self):
        """Test 4: Get Billing Balance"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{BACKEND_URL}/api/v1/billing/balance", headers=headers, timeout=10)
            passed = response.status_code == 200
            
            if passed:
                data = response.json()
                balance = data.get("balance", 0)
                self.log_test("Get Billing Balance", True, f"Balance: {balance} credits")
            else:
                self.log_test("Get Billing Balance", False, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("Get Billing Balance", False, str(e))
            return False
    
    def test_billing_pricing(self):
        """Test 5: Get Pricing Tiers"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{BACKEND_URL}/api/v1/billing/pricing", headers=headers, timeout=10)
            passed = response.status_code == 200
            
            if passed:
                data = response.json()
                tiers = data.get("tiers", [])
                self.log_test("Get Pricing Tiers", True, f"Found {len(tiers)} pricing tiers")
            else:
                self.log_test("Get Pricing Tiers", False, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("Get Pricing Tiers", False, str(e))
            return False
    
    def test_list_jobs(self):
        """Test 6: List Jobs"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{BACKEND_URL}/api/v1/jobs", headers=headers, timeout=10)
            passed = response.status_code == 200
            
            if passed:
                data = response.json()
                jobs = data.get("jobs", [])
                self.log_test("List Jobs", True, f"Found {len(jobs)} jobs")
            else:
                self.log_test("List Jobs", False, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("List Jobs", False, str(e))
            return False
    
    def test_frontend_accessibility(self):
        """Test 7: Frontend Accessibility"""
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            passed = response.status_code == 200
            self.log_test("Frontend Accessibility", passed, f"Status: {response.status_code}")
            return passed
        except:
            self.log_test("Frontend Accessibility", False, "Frontend not running on port 3000")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("OCTAVIA END-TO-END TESTING SUITE")
        print("=" * 70)
        print(f"Test Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Frontend URL: {FRONTEND_URL}")
        
        # Run tests
        self.test_health_check()
        self.test_signup()
        self.test_login()
        self.test_billing_balance()
        self.test_billing_pricing()
        self.test_list_jobs()
        self.test_frontend_accessibility()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"[PASS] Passed: {self.passed}")
        print(f"[FAIL] Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100) if (self.passed + self.failed) > 0 else 0:.1f}%")
        print("=" * 70)
        
        return self.failed == 0

if __name__ == "__main__":
    tester = OctaviaE2ETester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
