# Billing & Credits System Documentation

## Overview

Octavia uses a credit-based billing system for media processing. Users purchase credit packages through Polar.sh and consume credits based on job type and duration.

## System Architecture

### Components

1. **Polar.sh Integration** (`polar_client.py`)
   - Payment processing
   - Webhook handling
   - Order management

2. **Billing Models** (`billing_models.py`)
   - `CreditPackage` - Available credit packages
   - `Payment` - Payment records
   - `PricingTier` - Credit pricing
   - `CreditTransaction` - Credit ledger
   - `CreditUsageLog` - Job credit consumption

3. **Billing API** (`billing_routes.py`)
   - Pricing endpoints
   - Checkout creation
   - Webhook handler
   - Transaction history

4. **Credit Deduction**
   - Integrated into job processing
   - Automatic deduction on job completion
   - Insufficient credits prevention

## Credit Packages

| Package | Credits | Price | Use Case |
|---------|---------|-------|----------|
| Starter | 100 | $5 | Small projects, testing |
| Basic | 250 | $10 | Regular users |
| Professional | 500 | $18 | Teams, frequent usage |
| Enterprise | 1000 | $30 | Business, high volume |

## Credit Costs per Job Type

| Job Type | Credits | Based On |
|----------|---------|----------|
| Transcribe | 10 | Per minute of audio |
| Translate | 5 | Per translation job |
| Synthesize | 15 | Per minute of audio |
| Video Translate | 30 | Per minute of video |

**Formula Example:**
- 5-minute audio transcription: 5 min × 10 credits = 50 credits

## API Endpoints

### Get Pricing Tiers

```http
GET /api/v1/billing/pricing
Authorization: Bearer <token>
```

**Response:**
```json
{
  "tiers": [
    {
      "id": "tier-1",
      "package": "starter",
      "credits": 100,
      "price_usd": 5.0,
      "description": "Get started with Octavia",
      "is_active": true
    },
    ...
  ]
}
```

### Get Credit Balance

```http
GET /api/v1/billing/balance
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "user-123",
  "balance": 450,
  "last_updated": "2025-12-05T10:30:00Z"
}
```

### Create Checkout Session

```http
POST /api/v1/billing/checkout
Authorization: Bearer <token>
Content-Type: application/json

{
  "package": "basic",
  "success_url": "https://app.octavia.ai/billing?status=success",
  "cancel_url": "https://app.octavia.ai/billing?status=cancelled"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.polar.sh/...",
  "order_id": "payment-456",
  "credits": 250,
  "amount_usd": 10.0,
  "expires_at": null
}
```

### Get Transaction History

```http
GET /api/v1/billing/transactions?limit=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "transactions": [
    {
      "id": "txn-789",
      "transaction_type": "purchase",
      "amount": 100,
      "reason": "Purchase via starter package",
      "balance_before": 0,
      "balance_after": 100,
      "created_at": "2025-12-05T10:00:00Z"
    },
    {
      "id": "txn-790",
      "transaction_type": "deduction",
      "amount": 50,
      "reason": "transcribe job",
      "balance_before": 100,
      "balance_after": 50,
      "created_at": "2025-12-05T10:30:00Z"
    }
  ],
  "total_purchased": 100,
  "total_used": 50,
  "current_balance": 50
}
```

### Webhook Handler

```http
POST /api/v1/billing/webhook/polar
Content-Type: application/json
X-Polar-Signature: <signature>

{
  "type": "order.confirmed",
  "data": { ... },
  "timestamp": "2025-12-05T10:35:00Z"
}
```

**Webhook Events Handled:**
- `order.confirmed` - Payment successful, credits added
- `order.updated` - Order status changed
- `order.refunded` - Payment refunded, credits removed

## Environment Configuration

Required environment variables:

```bash
# Polar.sh API
POLAR_ACCESS_TOKEN=<token>
POLAR_WEBHOOK_SECRET=<secret>
POLAR_ORGANIZATION_ID=<org-id>
POLAR_PRODUCT_ID=<product-id>

# Price IDs (one per package)
POLAR_PRICE_ID_STARTER=price_starter_123
POLAR_PRICE_ID_BASIC=price_basic_456
POLAR_PRICE_ID_PRO=price_pro_789
POLAR_PRICE_ID_ENTERPRISE=price_ent_000
```

## Payment Flow

### 1. User Initiates Purchase

```
User clicks "Buy Credits" on dashboard
  ↓
Frontend calls POST /api/v1/billing/checkout
  ↓
Backend creates Payment record (status: PENDING)
  ↓
Backend calls Polar.sh API
  ↓
Returns checkout_url
  ↓
User redirected to Polar checkout
```

### 2. User Completes Payment

```
User enters payment details on Polar.sh
  ↓
Polar processes payment
  ↓
Polar sends webhook: order.confirmed
  ↓
Backend receives webhook (signature verified)
  ↓
Backend finds Payment record
  ↓
Backend adds credits to User.credits
  ↓
Backend records CreditTransaction
  ↓
User sees updated balance
```

### 3. User Consumes Credits

```
User submits transcription job
  ↓
Backend calculates credit cost: 5 min × 10 = 50 credits
  ↓
Backend checks User.credits >= 50
  ↓
If yes: deduct credits, proceed with job
  ↓
If no: return 402 Payment Required error
  ↓
Backend records CreditUsageLog
  ↓
Job processes normally
```

## Database Schema

### Users Table (Extended)

```sql
ALTER TABLE users ADD COLUMN credits BIGINT DEFAULT 0;
```

### Payments Table

```sql
CREATE TABLE payments (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  polar_order_id VARCHAR(255) UNIQUE,
  polar_product_id VARCHAR(255),
  package VARCHAR(20) NOT NULL,
  credits_purchased INTEGER NOT NULL,
  amount_usd FLOAT NOT NULL,
  status VARCHAR(20) NOT NULL,
  polar_checkout_url VARCHAR(500),
  metadata TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Credit Transactions Table

```sql
CREATE TABLE credit_transactions (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  transaction_type VARCHAR(20) NOT NULL,
  amount INTEGER NOT NULL,
  reason VARCHAR(255),
  balance_before INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX (user_id, created_at)
);
```

### Pricing Tiers Table

```sql
CREATE TABLE pricing_tiers (
  id VARCHAR(36) PRIMARY KEY,
  package VARCHAR(20) UNIQUE NOT NULL,
  credits INTEGER NOT NULL,
  price_usd FLOAT NOT NULL,
  description VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Credit Usage Logs Table

```sql
CREATE TABLE credit_usage_logs (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  job_id VARCHAR(36) NOT NULL,
  job_type VARCHAR(30) NOT NULL,
  credits_deducted INTEGER NOT NULL,
  reason VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX (user_id, job_id)
);
```

## Integration with Job Processing

When a job is completed, credits should be deducted:

```python
from app.billing_routes import deduct_credits

# In job completion handler
success = deduct_credits(
    session=db_session,
    user_id=user_id,
    job_id=job_id,
    job_type="transcribe",
    credits=50,
    reason="5-minute audio transcription"
)

if not success:
    # Handle insufficient credits
    job.status = JobStatus.FAILED
    job.error_message = "Insufficient credits"
    return False
```

## Security Considerations

1. **Webhook Signature Verification**
   - All Polar webhooks are HMAC-SHA256 signed
   - Signatures verified before processing
   - Prevents replay attacks

2. **Token-Based Authentication**
   - All endpoints require valid JWT token
   - User ID extracted from token
   - Operations scoped to authenticated user

3. **Credit Deduction Validation**
   - Balance checked before deduction
   - Atomic transactions (all-or-nothing)
   - Usage logged for auditing

4. **Payment Idempotency**
   - Duplicate webhook events handled safely
   - No double-crediting possible

## Testing

### Mock Polar.sh for Development

Set `POLAR_ACCESS_TOKEN` to test token for development:

```bash
export POLAR_ACCESS_TOKEN=test_pk_local_...
export POLAR_WEBHOOK_SECRET=test_secret_...
```

### Test Webhook Signature

```python
from app.polar_client import PolarClient

client = PolarClient()
payload = '{"type":"order.confirmed","data":{}}'
signature = "correct_hmac_signature"

assert client.verify_webhook_signature(payload, signature)
```

### Test Credit Deduction

```python
from app.billing_routes import deduct_credits

success = deduct_credits(
    session=db_session,
    user_id="test_user",
    job_id="test_job",
    job_type="transcribe",
    credits=50
)

assert success
assert user.credits == initial_credits - 50
```

## Error Handling

### Insufficient Credits

```http
HTTP 402 Payment Required

{
  "error": "insufficient_credits",
  "required": 50,
  "current_balance": 30,
  "message": "You have 30 credits but need 50. Purchase more credits to continue."
}
```

### Payment Service Unavailable

```http
HTTP 503 Service Unavailable

{
  "error": "payment_service_error",
  "message": "Payment service is temporarily unavailable. Try again later."
}
```

### Invalid Webhook

```http
HTTP 401 Unauthorized

{
  "error": "invalid_signature",
  "message": "Webhook signature verification failed"
}
```

## Future Enhancements

1. **Subscription Plans**
   - Monthly recurring billing
   - Automatic credit replenishment
   - Discounts for annual plans

2. **Usage Analytics**
   - Credits used per job type
   - Monthly spending trends
   - Cost optimization recommendations

3. **Refund Handling**
   - Partial refunds
   - Credit expiration policies
   - Chargeback handling

4. **Team Billing**
   - Shared credit pools
   - Department/project allocation
   - Usage limits per user

5. **Invoicing**
   - Monthly invoices
   - Tax calculation
   - Multi-currency support

## References

- [Polar.sh API Documentation](https://docs.polar.sh)
- [Payment Gateway Integration Patterns](https://stripe.com/docs/payments)
- [Credit System Best Practices](https://en.wikipedia.org/wiki/Virtual_currency)
