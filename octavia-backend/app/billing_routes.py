"""Billing and payment endpoints for Octavia."""
import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional

from . import db
from .models import User
from .security import decode_token, get_bearer_token
from .billing_models import (
    CreditPackage, Payment, PaymentStatus, PricingTier, 
    CreditTransaction, CreditUsageLog
)
from .billing_schemas import (
    CreditPackageType, CheckoutRequest, CheckoutResponse, 
    PricingListOut, PricingTierOut, CreditBalance, 
    TransactionHistoryOut, CreditTransactionOut, PaymentConfirmation,
    WebhookPayload
)
from .polar_client import (
    get_polar_client, WEBHOOK_ORDER_CONFIRMED, 
    WEBHOOK_ORDER_UPDATED, WEBHOOK_CHECKOUT_UPDATED
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user ID from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = get_bearer_token(authorization)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user_id


@router.get("/pricing", response_model=PricingListOut)
def get_pricing_tiers(db_session: Session = Depends(db.get_db)):
    """Get available credit packages and pricing."""
    try:
        tiers = db_session.query(PricingTier).filter(PricingTier.is_active == True).all()
        
        # If no tiers in DB, return defaults
        if not tiers:
            default_tiers = [
                {"package": "starter", "credits": 100, "price_usd": 5.0},
                {"package": "basic", "credits": 250, "price_usd": 10.0},
                {"package": "pro", "credits": 500, "price_usd": 18.0},
                {"package": "enterprise", "credits": 1000, "price_usd": 30.0},
            ]
            
            tiers = []
            for tier_data in default_tiers:
                tier = PricingTier(
                    package=CreditPackage(tier_data["package"]),
                    credits=tier_data["credits"],
                    price_usd=tier_data["price_usd"],
                    is_active=True
                )
                tiers.append(tier)
            
            logger.info("Initialized default pricing tiers")
        
        tier_list = [PricingTierOut.model_validate(tier) for tier in tiers]
        return PricingListOut(tiers=tier_list)
    
    except Exception as e:
        logger.error(f"Error fetching pricing tiers: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching pricing")


@router.get("/balance", response_model=CreditBalance)
def get_credit_balance(
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Get user's current credit balance."""
    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return CreditBalance(
            user_id=user_id,
            balance=user.credits,
            last_updated=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching balance: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching balance")


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    request: CheckoutRequest,
    user_id: str = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Create a checkout session for credit purchase."""
    try:
        # Get user
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get pricing tier
        tier = db_session.query(PricingTier).filter(
            PricingTier.package == CreditPackage(request.package),
            PricingTier.is_active == True
        ).first()
        
        if not tier:
            raise HTTPException(status_code=404, detail="Pricing tier not found")
        
        # Prepare metadata
        metadata = {
            "user_id": user_id,
            "user_email": user.email,
            "package": request.package,
            "credits": tier.credits,
        }
        
        # Create Polar checkout
        polar = get_polar_client()
        
        # Get product and price IDs from environment
        product_id = os.environ.get("POLAR_PRODUCT_ID")
        price_id = os.environ.get(f"POLAR_PRICE_ID_{request.package.upper()}")
        
        if not product_id or not price_id:
            logger.error(f"Missing Polar product/price configuration")
            raise HTTPException(status_code=500, detail="Payment service not configured")
        
        # Create checkout
        checkout_data = polar.create_checkout_session(
            product_id=product_id,
            product_price_id=price_id,
            customer_email=user.email,
            customer_name=user.email.split("@")[0],
            success_url=request.success_url or "http://localhost:3000/dashboard/billing?status=success",
            cancel_url=request.cancel_url or "http://localhost:3000/dashboard/billing?status=cancelled",
            metadata=metadata
        )
        
        if not checkout_data:
            raise HTTPException(status_code=500, detail="Failed to create checkout session")
        
        # Extract checkout URL
        checkout_url = checkout_data.get("url") or checkout_data.get("checkout_url")
        if not checkout_url:
            logger.error(f"No checkout URL in Polar response: {checkout_data}")
            raise HTTPException(status_code=500, detail="Invalid checkout response")
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            polar_order_id=checkout_data.get("order_id"),
            polar_product_id=product_id,
            package=CreditPackage(request.package),
            credits_purchased=tier.credits,
            amount_usd=tier.price_usd,
            status=PaymentStatus.PENDING,
            polar_checkout_url=checkout_url,
            metadata=json.dumps(metadata)
        )
        
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        
        logger.info(f"Checkout created for user {user_id}: {payment.id}")
        
        return CheckoutResponse(
            checkout_url=checkout_url,
            order_id=payment.id,
            credits=tier.credits,
            amount_usd=tier.price_usd,
            expires_at=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating checkout: {str(e)}")


@router.post("/webhook/polar")
async def handle_polar_webhook(
    request: Request,
    db_session: Session = Depends(db.get_db),
):
    """Handle webhook events from Polar.sh."""
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Get signature from headers
        signature = request.headers.get("x-polar-signature") or request.headers.get("Polar-Signature")
        if not signature:
            logger.warning("Webhook received without signature")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # Verify signature
        polar = get_polar_client()
        if not polar.verify_webhook_signature(body.decode() if isinstance(body, bytes) else body, signature):
            logger.error("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        payload = await request.json()
        webhook_data = polar.parse_webhook(payload)
        
        if not webhook_data:
            raise HTTPException(status_code=400, detail="Invalid webhook payload")
        
        event_type = webhook_data["event_type"]
        data = webhook_data["data"]
        
        logger.info(f"Processing webhook: {event_type}")
        
        # Handle order confirmation
        if event_type in (WEBHOOK_ORDER_CONFIRMED, WEBHOOK_ORDER_UPDATED):
            order_id = data.get("id")
            status = data.get("status")
            
            # Find payment by Polar order ID
            payment = db_session.query(Payment).filter(
                Payment.polar_order_id == order_id
            ).first()
            
            if not payment:
                logger.warning(f"Payment not found for order {order_id}")
                return {"status": "ok"}
            
            # If order is paid/confirmed, add credits
            if status in ("paid", "confirmed", "completed"):
                user = db_session.query(User).filter(User.id == payment.user_id).first()
                
                if user:
                    # Add credits
                    old_balance = user.credits
                    user.credits += payment.credits_purchased
                    
                    # Record transaction
                    transaction = CreditTransaction(
                        user_id=payment.user_id,
                        transaction_type="purchase",
                        amount=payment.credits_purchased,
                        reason=f"Purchase via {payment.package.value} package",
                        balance_before=old_balance,
                        balance_after=user.credits
                    )
                    
                    # Update payment status
                    payment.status = PaymentStatus.COMPLETED
                    payment.completed_at = datetime.utcnow()
                    
                    db_session.add(transaction)
                    db_session.commit()
                    
                    logger.info(f"Credits added for user {payment.user_id}: +{payment.credits_purchased}")
            
            elif status == "refunded":
                # Handle refund
                user = db_session.query(User).filter(User.id == payment.user_id).first()
                
                if user and payment.status == PaymentStatus.COMPLETED:
                    old_balance = user.credits
                    user.credits -= payment.credits_purchased
                    user.credits = max(0, user.credits)  # Don't go negative
                    
                    transaction = CreditTransaction(
                        user_id=payment.user_id,
                        transaction_type="refund",
                        amount=payment.credits_purchased,
                        reason=f"Refund for order {order_id}",
                        balance_before=old_balance,
                        balance_after=user.credits
                    )
                    
                    payment.status = PaymentStatus.REFUNDED
                    
                    db_session.add(transaction)
                    db_session.commit()
                    
                    logger.info(f"Refund processed for user {payment.user_id}: -{payment.credits_purchased}")
        
        return {"status": "ok"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


@router.get("/transactions", response_model=TransactionHistoryOut)
def get_transaction_history(
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    db_session: Session = Depends(db.get_db),
):
    """Get user's credit transaction history."""
    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        transactions = db_session.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).order_by(CreditTransaction.created_at.desc()).limit(limit).all()
        
        total_purchased = 0
        total_used = 0
        
        for txn in transactions:
            if txn.transaction_type == "purchase":
                total_purchased += txn.amount
            elif txn.transaction_type == "deduction":
                total_used += txn.amount
        
        transaction_list = [CreditTransactionOut.model_validate(t) for t in transactions]
        
        return TransactionHistoryOut(
            transactions=transaction_list,
            total_purchased=total_purchased,
            total_used=total_used,
            current_balance=user.credits
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching transactions")


def deduct_credits(
    session: Session,
    user_id: str,
    job_id: str,
    job_type: str,
    credits: int,
    reason: str = ""
) -> bool:
    """
    Deduct credits from user's balance for a job.
    
    Args:
        session: Database session
        user_id: User ID
        job_id: Job ID that credits are being deducted for
        job_type: Type of job (transcribe, translate, synthesize, video_translate)
        credits: Number of credits to deduct
        reason: Optional reason for deduction
        
    Returns:
        True if successful, False if insufficient credits
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found for credit deduction")
            return False
        
        if user.credits < credits:
            logger.warning(f"User {user_id} has insufficient credits: {user.credits} < {credits}")
            return False
        
        old_balance = user.credits
        user.credits -= credits
        
        # Record transaction
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="deduction",
            amount=credits,
            reason=reason or f"{job_type} job",
            balance_before=old_balance,
            balance_after=user.credits
        )
        
        # Record usage log
        usage_log = CreditUsageLog(
            user_id=user_id,
            job_id=job_id,
            job_type=job_type,
            credits_deducted=credits,
            reason=reason
        )
        
        session.add(transaction)
        session.add(usage_log)
        session.commit()
        
        logger.info(f"Credits deducted for user {user_id}: -{credits} (remaining: {user.credits})")
        return True
    
    except Exception as e:
        logger.error(f"Error deducting credits: {str(e)}")
        return False
