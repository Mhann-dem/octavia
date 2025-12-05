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
import pytest
from starlette.testclient import TestClient

from app.main import app
from app import db


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
        
        # Mock checkout creation
        mock_client.create_checkout_session.return_value = {
            "url": "https://checkout.polar.sh/test-checkout-url",
            "order_id": "test-order-12345",
            "checkout_url": "https://checkout.polar.sh/test-checkout-url"
        }
        
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


class TestBillingE2E:
    """End-to-end billing flow tests."""
    
    def test_01_signup_and_get_initial_balance(self, client, mock_polar_client):
        """Test 1: User signup and check initial balance (0 credits)."""
        email = f"test_{int(time.time())}@example.com"
        password = "BillingTest123!"
        
        # Signup
        resp = client.post("/signup", json={
            "email": email,
            "password": password
        })
        assert resp.status_code == 200, f"Signup failed: {resp.text}"
        user = resp.json()["user"]
        user_id = user["id"]
        assert user["email"] == email
        
        # Login
        resp = client.post("/login", json={
            "email": email,
            "password": password
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        
        # Check initial balance
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/billing/balance", headers=headers)
        assert resp.status_code == 200
        balance = resp.json()
        assert balance["balance"] == 0, "New user should have 0 credits"
        print(f"✓ User {user_id} created with initial balance: {balance['balance']}")
    
    def test_02_get_pricing_tiers(self, client, mock_polar_client):
        """Test 2: Retrieve available pricing tiers."""
        email = f"test_{int(time.time())}@example.com"
        password = "TestPass123!"
        
        # Signup and login
        client.post("/signup", json={"email": email, "password": password})
        resp = client.post("/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
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
        
        # Setup: signup and login
        client.post("/signup", json={"email": email, "password": password})
        resp = client.post("/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
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
        
        # Setup: signup, login, create checkout
        client.post("/signup", json={"email": email, "password": password})
        resp = client.post("/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.post("/api/v1/billing/checkout", 
            json={"package": "starter"},
            headers=headers
        )
        order_id = resp.json()["order_id"]
        credits_expected = 100
        
        # Send webhook: payment confirmed
        webhook_payload = {
            "type": "order.confirmed",
            "data": {
                "id": order_id,
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
        
        # Setup: signup and login
        client.post("/signup", json={"email": email, "password": password})
        resp = client.post("/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
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
        
        # Setup: signup, login, checkout, webhook
        client.post("/signup", json={"email": email, "password": password})
        resp = client.post("/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = client.post("/api/v1/billing/checkout", 
            json={"package": "starter"},
            headers=headers
        )
        order_id = resp.json()["order_id"]
        
        # Send webhook
        webhook_payload = {
            "type": "order.confirmed",
            "data": {"id": order_id, "status": "paid"},
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
        
        # Phase 1: Signup
        print("\n[1] Signup")
        resp = client.post("/signup", json={
            "email": email,
            "password": password
        })
        assert resp.status_code == 200
        user_id = resp.json()["user"]["id"]
        print(f"✓ User created: {user_id}")
        
        # Phase 2: Login
        print("[2] Login")
        resp = client.post("/login", json={
            "email": email,
            "password": password
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✓ Authenticated")
        
        # Phase 3: Check initial balance
        print("[3] Check initial balance")
        resp = client.get("/api/v1/billing/balance", headers=headers)
        initial_balance = resp.json()["balance"]
        assert initial_balance == 0
        print(f"✓ Initial balance: {initial_balance} credits")
        
        # Phase 4: Get pricing
        print("[4] Get pricing tiers")
        resp = client.get("/api/v1/billing/pricing", headers=headers)
        tiers = resp.json()["tiers"]
        print(f"✓ Available packages: {len(tiers)}")
        
        # Phase 5: Create checkout
        print("[5] Create checkout session")
        resp = client.post("/api/v1/billing/checkout",
            json={"package": "starter"},
            headers=headers
        )
        order_id = resp.json()["order_id"]
        credits_expected = 100
        print(f"✓ Checkout created: {order_id}")
        
        # Phase 6: Simulate webhook
        print("[6] Simulate Polar webhook (payment confirmation)")
        webhook_payload = {
            "type": "order.confirmed",
            "data": {"id": order_id, "status": "paid"},
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
