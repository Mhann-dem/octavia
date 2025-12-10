#!/usr/bin/env python3
"""Add test credits to a user account for testing purposes."""

import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.billing import CreditTransaction
from datetime import datetime


def add_credits_to_user(user_email: str, credits_amount: int):
    """Add credits to a user's account."""
    db = SessionLocal()
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            print(f"❌ User with email '{user_email}' not found")
            return False
        
        # Record balance before
        balance_before = user.credits
        
        # Add credits
        user.credits += credits_amount
        balance_after = user.credits
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user.id,
            transaction_type="admin_grant",
            amount=credits_amount,
            reason=f"Test credits granted for development",
            balance_before=balance_before,
            balance_after=balance_after
        )
        
        db.add(transaction)
        db.commit()
        
        print(f"✅ Added {credits_amount} credits to {user.email}")
        print(f"   Balance: {balance_before} → {balance_after}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_user_balance(user_email: str):
    """Check current balance of a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User with email '{user_email}' not found")
            return None
        
        print(f"📊 User: {user.email}")
        print(f"   Current credits: {user.credits}")
        return user.credits
    finally:
        db.close()


if __name__ == "__main__":
    # Check if email is provided
    if len(sys.argv) < 2:
        print("Usage: python add_test_credits.py <email> [credits_amount]")
        print("Example: python add_test_credits.py user@example.com 1000")
        print()
        # If no args, list all users
        db = SessionLocal()
        users = db.query(User).all()
        if users:
            print("Available users:")
            for user in users:
                print(f"  - {user.email} (Credits: {user.credits})")
        else:
            print("No users found in database")
        db.close()
    else:
        email = sys.argv[1]
        credits = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        
        # Check current balance first
        get_user_balance(email)
        print()
        
        # Add credits
        if add_credits_to_user(email, credits):
            print()
            # Show new balance
            get_user_balance(email)
