"""Billing related schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class CreditPackageType(str, Enum):
    """Available credit packages."""
    STARTER = "starter"      # 100 credits - $5
    BASIC = "basic"          # 250 credits - $10
    PROFESSIONAL = "pro"     # 500 credits - $18
    ENTERPRISE = "enterprise"  # 1000 credits - $30


class PricingTierOut(BaseModel):
    """Pricing tier information."""
    id: str
    package: CreditPackageType
    credits: int
    price_usd: float
    description: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class PricingListOut(BaseModel):
    """List of available pricing tiers."""
    tiers: list[PricingTierOut]


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    package: CreditPackageType
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str
    order_id: str
    polar_order_id: Optional[str] = None
    credits: int
    amount_usd: float
    expires_at: Optional[str] = None


class CreditBalance(BaseModel):
    """User credit balance."""
    balance: int


class CreditTransactionOut(BaseModel):
    """Credit transaction record."""
    id: str
    transaction_type: str
    amount: int
    reason: Optional[str] = None
    balance_before: int
    balance_after: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionHistoryOut(BaseModel):
    """User's transaction history."""
    transactions: list[CreditTransactionOut]
    total_purchased: int
    total_used: int
    current_balance: int


class CreditEstimateRequest(BaseModel):
    """Request to estimate credits needed for a job."""
    job_type: str  # 'transcribe', 'translate', 'synthesize', 'video_translate'
    input_file_path: Optional[str] = None
    duration_minutes: Optional[int] = None
    duration_override: Optional[int] = None
    target_language: Optional[str] = None


class CreditEstimateResponse(BaseModel):
    """Response with estimated credit cost."""
    job_type: str
    estimated_credits: int
    current_balance: int
    sufficient_balance: bool
    reason: str
