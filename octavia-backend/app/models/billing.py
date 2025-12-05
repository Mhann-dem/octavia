"""Billing and payment models for Octavia."""
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CreditPackage(str, enum.Enum):
    """Available credit packages for purchase."""
    STARTER = "starter"      # 100 credits
    BASIC = "basic"          # 250 credits
    PROFESSIONAL = "pro"     # 500 credits
    ENTERPRISE = "enterprise"  # 1000 credits


class PaymentStatus(str, enum.Enum):
    """Payment transaction status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CreditTransaction(Base):
    """Record of credit purchases and usage."""
    __tablename__ = "credit_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    transaction_type = Column(String, nullable=False)  # 'purchase', 'deduction', 'refund'
    amount = Column(Integer, nullable=False)  # Credit amount
    reason = Column(String, nullable=True)  # Why credits were added/removed
    balance_before = Column(Integer, nullable=False)  # User's credit balance before transaction
    balance_after = Column(Integer, nullable=False)  # User's credit balance after transaction
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    """Payment records for credit purchases."""
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    polar_order_id = Column(String(255), nullable=True, unique=True, index=True)  # Polar.sh order ID
    polar_product_id = Column(String(255), nullable=True)  # Polar.sh product ID
    package = Column(Enum(CreditPackage), nullable=False)
    credits_purchased = Column(Integer, nullable=False)
    amount_usd = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    polar_checkout_url = Column(String(500), nullable=True)
    payment_metadata = Column(Text, nullable=True)  # JSON with payment details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class PricingTier(Base):
    """Pricing configuration for credit packages."""
    __tablename__ = "pricing_tiers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    package = Column(Enum(CreditPackage), nullable=False, unique=True, index=True)
    credits = Column(Integer, nullable=False)
    price_usd = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CreditUsageLog(Base):
    """Log of credit usage by jobs."""
    __tablename__ = "credit_usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    job_type = Column(String, nullable=False)  # 'transcribe', 'translate', 'synthesize', 'video_translate'
    credits_deducted = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
