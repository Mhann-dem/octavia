"""Polar.sh payment integration for Octavia."""
import os
import json
import logging
import hashlib
import hmac
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class PolarClient:
    """Client for interacting with Polar.sh API."""
    
    BASE_URL = "https://api.polar.sh/api/v1"
    
    def __init__(self):
        """Initialize Polar client with credentials from environment."""
        self.access_token = os.environ.get("POLAR_ACCESS_TOKEN")
        self.webhook_secret = os.environ.get("POLAR_WEBHOOK_SECRET")
        self.organization_id = os.environ.get("POLAR_ORGANIZATION_ID")
        
        if not self.access_token:
            logger.warning("POLAR_ACCESS_TOKEN not set in environment")
        if not self.webhook_secret:
            logger.warning("POLAR_WEBHOOK_SECRET not set in environment")
        if not self.organization_id:
            logger.warning("POLAR_ORGANIZATION_ID not set in environment")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
    
    def create_checkout_session(
        self,
        product_id: str,
        product_price_id: str,
        customer_email: str,
        customer_name: str = "",
        success_url: str = "",
        cancel_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a checkout session for a customer.
        
        Args:
            product_id: Polar product ID
            product_price_id: Polar product price ID
            customer_email: Customer email
            customer_name: Customer name (optional)
            success_url: URL to redirect to on success
            cancel_url: URL to redirect to on cancellation
            metadata: Additional metadata to store with order
            
        Returns:
            Checkout session data with checkout_url, or None if failed
        """
        try:
            url = f"{self.BASE_URL}/checkouts"
            
            payload = {
                "product_id": product_id,
                "product_price_id": product_price_id,
                "customer_email": customer_email,
            }
            
            if customer_name:
                payload["customer_name"] = customer_name
            if success_url:
                payload["success_url"] = success_url
            if cancel_url:
                payload["cancel_url"] = cancel_url
            if metadata:
                payload["metadata"] = metadata
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code not in (200, 201):
                logger.error(f"Polar checkout creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
            
            return response.json()
        
        except Exception as e:
            logger.error(f"Error creating Polar checkout: {str(e)}")
            return None
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details from Polar.
        
        Args:
            order_id: Polar order ID
            
        Returns:
            Order data or None if failed
        """
        try:
            url = f"{self.BASE_URL}/orders/{order_id}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch order {order_id}: {response.status_code}")
                return None
            
            return response.json()
        
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
            return None
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from Polar.
        
        Args:
            payload: Raw webhook payload (request body)
            signature: Signature from Polar-Signature header
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.error("Cannot verify webhook: POLAR_WEBHOOK_SECRET not set")
            return False
        
        try:
            # Polar uses HMAC-SHA256 for signature verification
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode() if isinstance(payload, str) else payload,
                hashlib.sha256
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, signature)
        
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def parse_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and validate webhook payload from Polar.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Parsed webhook data or None if invalid
        """
        try:
            event_type = payload.get("type")
            data = payload.get("data")
            
            if not event_type or not data:
                logger.error("Invalid webhook payload structure")
                return None
            
            return {
                "event_type": event_type,
                "data": data,
                "timestamp": payload.get("timestamp"),
            }
        
        except Exception as e:
            logger.error(f"Error parsing webhook: {str(e)}")
            return None


def get_polar_client() -> PolarClient:
    """Get Polar client instance."""
    return PolarClient()


# Webhook event types
WEBHOOK_ORDER_CREATED = "order.created"
WEBHOOK_ORDER_UPDATED = "order.updated"
WEBHOOK_ORDER_CONFIRMED = "order.confirmed"
WEBHOOK_CHECKOUT_UPDATED = "checkout.updated"
WEBHOOK_SUBSCRIPTION_CREATED = "subscription.created"
WEBHOOK_SUBSCRIPTION_UPDATED = "subscription.updated"


def handle_payment_webhook(event_type: str, data: Dict[str, Any]) -> bool:
    """
    Handle incoming payment webhook from Polar.
    This is a placeholder - actual handling is done in routes.
    
    Args:
        event_type: Type of webhook event
        data: Event data
        
    Returns:
        True if handled successfully
    """
    logger.info(f"Received webhook event: {event_type}")
    
    if event_type in (WEBHOOK_ORDER_CONFIRMED, WEBHOOK_ORDER_UPDATED):
        # Payment successful - add credits to user
        logger.info(f"Payment confirmed for order: {data.get('id')}")
        return True
    
    return True
