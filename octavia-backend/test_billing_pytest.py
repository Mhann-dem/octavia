#!/usr/bin/env python3
"""
Pytest-based end-to-end billing test with mocked Polar client.
Tests: signup → pricing → checkout → webhook → balance → estimate → transactions
"""
import json
import os
import tempfile
import time
import wave
import struct
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs
import pytest
from starlette.testclient import TestClient

from app.main import app
from app import db

# Set test environment variables for Polar
os.environ["POLAR_PRODUCT_ID"] = "test-product-id"
os.environ["POLAR_PRICE_ID_STARTER"] = "test-price-starter"
os.environ["POLAR_PRICE_ID_BASIC"] = "test-price-basic"
os.environ["POLAR_PRICE_ID_PRO"] = "test-price-pro"
os.environ["POLAR_PRICE_ID_ENTERPRISE"] = "test-price-enterprise"


@pytest.fixture(scope="function")
def client():
    """Create a fresh test client for each test."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    """Reset database tables before each test."""
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    yield


@pytest.fixture
def mock_polar_client():
    """Mock the Polar client to avoid real API calls."""
    with patch('app.billing_routes.get_polar_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Track generated order IDs for consistent webhook testing
        order_ids = {}
        
        # Mock checkout creation - generate consistent order IDs
        def create_checkout_impl(**kwargs):
            # Generate a unique order ID based on customer email
            email = kwargs.get('customer_email', 'test@example.com')
            if email not in order_ids:
                order_ids[email] = f"polar-order-{int(time.time()*1000)}-{len(order_ids)}"
            order_id = order_ids[email]
            
            return {
                "url": "https://checkout.polar.sh/test-checkout-url",
                "order_id": order_id,
                "checkout_url": "https://checkout.polar.sh/test-checkout-url"
            }
        
        mock_client.create_checkout_session.side_effect = create_checkout_impl
        
        # Mock webhook signature verification (always succeed in test)
        mock_client.verify_webhook_signature.return_value = True
        
        # Mock webhook parsing
        def parse_webhook_impl(payload):
            return {
                "event_type": payload.get("type"),
                "data": payload.get("data"),
                "timestamp": payload.get("timestamp")
            }
        mock_client.parse_webhook.side_effect = parse_webhook_impl
        
        yield mock_client


def signup_and_login(client, email: str, password: str):
    """Helper function to signup, verify, and login a user."""
    # Signup
    resp = client.post("/signup", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Signup failed with {resp.status_code}: {resp.text}")
    
    signup_data = resp.json()
    verify_url = signup_data.get("verify_url", "")
    
    # Extract verify token from URL
    try:
        parsed = urlparse(verify_url)
        token = parse_qs(parsed.query).get("token", [None])[0]
    except Exception as e:
        raise RuntimeError(f"Could not extract verify token: {e}")
    
    if not token:
        raise RuntimeError("No verify token in signup response")
    
    # Verify email
    resp = client.get(f"/verify?token={token}")
    if resp.status_code != 200:
        raise RuntimeError(f"Verify failed with {resp.status_code}: {resp.text}")
    
    # Login
    resp = client.post("/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed with {resp.status_code}: {resp.text}")
    
    access_token = resp.json().get("access_token")
    if not access_token:
        raise RuntimeError("No access token in login response")
    
    # Fetch pricing to initialize default tiers
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = client.get("/api/v1/billing/pricing", headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to initialize pricing tiers: {resp.text}")
    
    return access_token



class TestBillingE2E:
    """End-to-end billing flow tests."""
    
    def test_01_signup_and_get_initial_balance(self, client, mock_polar_client):
        """Test 1: User signup and check initial balance (0 credits)."""
        email = f"test_{int(time.time())}@example.com"
        password = "BillingTest123!"
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check initial balance
        resp = client.get("/api/v1/billing/balance", headers=headers)
        assert resp.status_code == 200
        balance = resp.json()
        assert balance["balance"] == 0, "New user should have 0 credits"
        print(f"✓ User created with initial balance: {balance['balance']}")
    
    def test_02_get_pricing_tiers(self, client, mock_polar_client):
        """Test 2: Retrieve available pricing tiers."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get pricing
        resp = client.get("/api/v1/billing/pricing", headers=headers)
        assert resp.status_code == 200
        pricing = resp.json()
        tiers = pricing["tiers"]
        assert len(tiers) > 0, "Should have at least one pricing tier"
        
        # Verify tier structure
        for tier in tiers:
            assert "package" in tier
            assert "credits" in tier
            assert "price_usd" in tier
            assert tier["credits"] > 0
            assert tier["price_usd"] > 0
        
        print(f"✓ Retrieved {len(tiers)} pricing tiers")
        for tier in tiers:
            print(f"  - {tier['package']}: {tier['credits']} credits for ${tier['price_usd']}")
    
    def test_03_checkout_creation(self, client, mock_polar_client):
        """Test 3: Create a checkout session."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create checkout
        resp = client.post("/api/v1/billing/checkout", 
            json={"package": "starter"},
            headers=headers
        )
        assert resp.status_code == 200, f"Checkout failed: {resp.text}"
        checkout = resp.json()
        assert "checkout_url" in checkout
        assert "order_id" in checkout
        assert checkout["credits"] == 100
        assert checkout["amount_usd"] == 5.0
        
        print(f"✓ Checkout created: order_id={checkout['order_id']}, credits={checkout['credits']}")
    
    def test_04_webhook_payment_confirmation(self, client, mock_polar_client):
        """Test 4: Webhook payment confirmation adds credits to user."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create checkout
        resp = client.post("/api/v1/billing/checkout", 
            json={"package": "starter"},
            headers=headers
        )
        checkout_resp = resp.json()
        polar_order_id = checkout_resp["polar_order_id"]
        credits_expected = 100
        
        # Send webhook: payment confirmed
        webhook_payload = {
            "type": "order.confirmed",
            "data": {
                "id": polar_order_id,
                "status": "paid"
            },
            "timestamp": time.time()
        }
        resp = client.post("/api/v1/billing/webhook/polar", 
            json=webhook_payload,
            headers={"x-polar-signature": "mock-signature"}
        )
        assert resp.status_code == 200
        
        # Check balance after webhook
        resp = client.get("/api/v1/billing/balance", headers=headers)
        assert resp.status_code == 200
        balance = resp.json()["balance"]
        assert balance == credits_expected, f"Expected {credits_expected} credits, got {balance}"
        
        print(f"✓ Webhook processed: credits added = {balance}")
    
    def test_05_credit_estimate(self, client, mock_polar_client):
        """Test 5: Estimate credit cost for a transcription job."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Create temp audio file
        tmpdir = tempfile.gettempdir()
        audio_file = os.path.join(tmpdir, f"test_audio_{int(time.time())}.wav")
        
        with wave.open(audio_file, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            silence = struct.pack('<h', 0) * (16000 * 5)  # 5 seconds
            wav_file.writeframes(silence)
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Estimate credits
        resp = client.post("/api/v1/estimate",
            json={
                "job_type": "transcribe",
                "input_file_path": audio_file,
                "duration_override": 5  # 5 minutes = 50 credits
            },
            headers=headers
        )
        assert resp.status_code == 200, f"Estimate failed: {resp.text}"
        estimate = resp.json()
        assert estimate["job_type"] == "transcribe"
        assert estimate["estimated_credits"] > 0
        assert estimate["current_balance"] == 0
        assert estimate["sufficient_balance"] == False
        
        print(f"✓ Credit estimate: {estimate['estimated_credits']} credits for transcription")
    
    def test_06_transaction_history(self, client, mock_polar_client):
        """Test 6: Check transaction history after payment."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Signup, verify, and login
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create checkout
        resp = client.post("/api/v1/billing/checkout", 
            json={"package": "starter"},
            headers=headers
        )
        polar_order_id = resp.json()["polar_order_id"]
        
        # Send webhook
        webhook_payload = {
            "type": "order.confirmed",
            "data": {"id": polar_order_id, "status": "paid"},
            "timestamp": time.time()
        }
        client.post("/api/v1/billing/webhook/polar", 
            json=webhook_payload,
            headers={"x-polar-signature": "mock-signature"}
        )
        
        # Get transaction history
        resp = client.get("/api/v1/billing/transactions", headers=headers)
        assert resp.status_code == 200
        history = resp.json()
        transactions = history.get("transactions", [])
        assert len(transactions) > 0, "Should have at least one transaction"
        
        # Verify transaction details
        txn = transactions[0]
        assert txn["transaction_type"] == "purchase"
        assert txn["amount"] == 100
        assert txn["balance_before"] == 0
        assert txn["balance_after"] == 100
        
        print(f"✓ Transaction history: {len(transactions)} transaction(s)")
        print(f"  - Type: {txn['transaction_type']}, Amount: {txn['amount']} credits")
    
    def test_07_complete_billing_flow(self, client, mock_polar_client):
        """Test 7: Complete end-to-end flow."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        print("\n" + "="*80)
        print("COMPLETE BILLING E2E FLOW")
        print("="*80)
        
        # Phase 1: Signup, verify, and login
        print("\n[1] Signup & Verify & Login")
        token = signup_and_login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✓ Authenticated")
        
        # Phase 2: Check initial balance
        print("[2] Check initial balance")
        resp = client.get("/api/v1/billing/balance", headers=headers)
        initial_balance = resp.json()["balance"]
        assert initial_balance == 0
        print(f"✓ Initial balance: {initial_balance} credits")
        
        # Phase 3: Get pricing
        print("[3] Get pricing tiers")
        resp = client.get("/api/v1/billing/pricing", headers=headers)
        tiers = resp.json()["tiers"]
        print(f"✓ Available packages: {len(tiers)}")
        
        # Phase 4: Create checkout
        print("[4] Create checkout session")
        resp = client.post("/api/v1/billing/checkout",
            json={"package": "starter"},
            headers=headers
        )
        checkout_resp = resp.json()
        polar_order_id = checkout_resp["polar_order_id"]
        credits_expected = 100
        print(f"✓ Checkout created: order_id={checkout_resp['order_id'][:8]}...")
        
        # Phase 5: Simulate webhook
        print("[5] Simulate Polar webhook (payment confirmation)")
        webhook_payload = {
            "type": "order.confirmed",
            "data": {"id": polar_order_id, "status": "paid"},
            "timestamp": time.time()
        }
        resp = client.post("/api/v1/billing/webhook/polar",
            json=webhook_payload,
            headers={"x-polar-signature": "mock-signature"}
        )
        assert resp.status_code == 200
        print(f"✓ Webhook processed")
        
        # Phase 7: Verify credits added
        print("[7] Verify credits added")
        resp = client.get("/api/v1/billing/balance", headers=headers)
        new_balance = resp.json()["balance"]
        assert new_balance == credits_expected
        print(f"✓ Credits added: {initial_balance} → {new_balance}")
        
        # Phase 8: Check transaction history
        print("[8] Check transaction history")
        resp = client.get("/api/v1/billing/transactions", headers=headers)
        transactions = resp.json()["transactions"]
        assert len(transactions) > 0
        print(f"✓ Transaction history: {len(transactions)} entries")
        
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
