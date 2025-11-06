# Billing Module — Техническая спецификация

## 1. Обзор

Billing модуль обрабатывает платежи, подписки и управление балансом пользователей для сервиса OneiroScope/СоноГраф.

---

## 2. Требования

### 2.1 Функциональные требования

| ID | Требование | Приоритет |
|----|------------|-----------|
| BILL-F-001 | 1 бесплатный анализ сна для нового пользователя | P0 |
| BILL-F-002 | Pay-per-use модель: $2.99 за анализ | P0 |
| BILL-F-003 | Подписка: $5.99/мес за 10 анализов | P0 |
| BILL-F-004 | Интеграция Stripe (международные платежи) | P0 |
| BILL-F-005 | Интеграция YooKassa (Россия) | P1 |
| BILL-F-006 | Webhook обработка для подтверждения платежей | P0 |
| BILL-F-007 | Idempotency ключи для предотвращения дублирования | P0 |
| BILL-F-008 | История транзакций | P1 |
| BILL-F-009 | Автоматическое продление подписки | P1 |
| BILL-F-010 | Email уведомления о платежах | P2 |
| BILL-F-011 | Invoice генерация (PDF) | P2 |
| BILL-F-012 | Возвраты (refunds) | P2 |

### 2.2 Нефункциональные требования

| ID | Метрика | Значение |
|----|---------|----------|
| BILL-NF-001 | Uptime | 99.9% |
| BILL-NF-002 | Webhook latency | ≤ 500ms |
| BILL-NF-003 | Idempotency window | 24 часа |
| BILL-NF-004 | PCI DSS compliance | N/A (через Stripe/YooKassa) |
| BILL-NF-005 | Retry error rate | ≤ 0.5% |
| BILL-NF-006 | Fraud detection | Stripe Radar |

---

## 3. Pricing Model

### 3.1 Тарифные планы

```yaml
plans:
  free_tier:
    name: "Free Trial"
    price: $0
    dreams_included: 1
    features:
      - Basic dream analysis
      - Lunar calendar
      - RU/EN support

  pay_per_dream:
    name: "Pay-per-Dream"
    price: $2.99
    dreams_included: 1
    features:
      - Full dream analysis
      - Voice input
      - PDF export
      - Email support

  monthly:
    name: "Monthly"
    price: $5.99
    billing_period: "month"
    dreams_included: 10
    features:
      - All pay-per-dream features
      - Priority analysis
      - Dream journal
      - Trend analytics

  annual:
    name: "Annual"
    price: $59.99  # ~17% discount
    billing_period: "year"
    dreams_included: unlimited
    features:
      - All monthly features
      - Advanced analytics
      - Export to Notion/Obsidian
      - API access
```

### 3.2 Regional Pricing

```yaml
regions:
  USD:  # Default
    pay_per_dream: 2.99
    monthly: 5.99
    annual: 59.99

  RUB:  # Russia (via YooKassa)
    pay_per_dream: 249  # ~$2.99
    monthly: 499        # ~$5.99
    annual: 4999        # ~$59.99

  EUR:
    pay_per_dream: 2.79
    monthly: 5.49
    annual: 54.99
```

---

## 4. Архитектура

### 4.1 System Context

```
┌───────────┐
│  Client   │
└─────┬─────┘
      │
      ▼
┌─────────────────────────────────────────┐
│         Billing Service (FastAPI)       │
│                                         │
│  ┌────────────────────────────────────┐│
│  │     Payment Gateway Abstraction    ││
│  │  (Strategy Pattern)                ││
│  └──┬──────────────────────────────┬──┘│
│     │                              │   │
│     ▼                              ▼   │
│  ┌────────┐                  ┌─────────┐
│  │ Stripe │                  │YooKassa │
│  │Checkout│                  │   API   │
│  └────┬───┘                  └────┬────┘
│       │                           │    │
│       ▼                           ▼    │
│  ┌────────────────────────────────────┐│
│  │      Webhook Handler               ││
│  └────────────┬───────────────────────┘│
│               ▼                        │
│  ┌────────────────────────────────────┐│
│  │   Transaction & Subscription DB    ││
│  └────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### 4.2 Component Diagram

```
backend/
├── services/
│   └── billing/
│       ├── __init__.py
│       ├── service.py              # Main billing orchestration
│       ├── payment_gateway.py      # Abstract gateway interface
│       ├── stripe_gateway.py       # Stripe implementation
│       ├── yookassa_gateway.py     # YooKassa implementation
│       ├── subscription_manager.py # Subscription lifecycle
│       ├── invoice_generator.py    # PDF invoice generation
│       ├── webhooks.py             # Webhook handlers
│       └── schemas.py              # Pydantic models
├── api/
│   └── v1/
│       ├── billing.py              # Payment endpoints
│       └── webhooks.py             # Webhook endpoints
└── models/
    ├── transaction.py              # Transaction model
    ├── subscription.py             # Subscription model
    └── user_balance.py             # User balance tracking
```

---

## 5. Database Schema

### 5.1 Tables

```sql
-- Users table (extends existing)
ALTER TABLE users ADD COLUMN free_dream_used BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN dream_balance INTEGER DEFAULT 0;

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL,  -- 'monthly', 'annual'
    status VARCHAR(20) NOT NULL,   -- 'active', 'canceled', 'past_due', 'expired'
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    stripe_subscription_id VARCHAR(255),
    yookassa_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_one_gateway CHECK (
        (stripe_subscription_id IS NOT NULL AND yookassa_subscription_id IS NULL) OR
        (stripe_subscription_id IS NULL AND yookassa_subscription_id IS NOT NULL)
    )
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,  -- 'one_time', 'subscription', 'refund'
    status VARCHAR(20) NOT NULL,  -- 'pending', 'succeeded', 'failed', 'refunded'
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,  -- 'USD', 'RUB', 'EUR'
    gateway VARCHAR(20) NOT NULL,  -- 'stripe', 'yookassa'
    gateway_transaction_id VARCHAR(255),
    gateway_customer_id VARCHAR(255),
    description TEXT,
    metadata JSONB DEFAULT '{}',
    dreams_purchased INTEGER,  -- Number of dreams purchased
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_idempotency_key ON transactions(idempotency_key);
CREATE INDEX idx_transactions_gateway_id ON transactions(gateway_transaction_id);

-- Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_id UUID REFERENCES transactions(id),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    pdf_url TEXT,
    stripe_invoice_id VARCHAR(255),
    issued_at TIMESTAMP NOT NULL,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_transaction_id ON invoices(transaction_id);

-- Dream usage tracking
CREATE TABLE dream_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dream_id UUID NOT NULL,
    used_free_tier BOOLEAN DEFAULT FALSE,
    used_subscription BOOLEAN DEFAULT FALSE,
    subscription_id UUID REFERENCES subscriptions(id),
    transaction_id UUID REFERENCES transactions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dream_usage_user_id ON dream_usage(user_id);
CREATE INDEX idx_dream_usage_subscription_id ON dream_usage(subscription_id);
```

---

## 6. API Specification

### 6.1 Create Checkout Session

#### POST /api/v1/billing/checkout

**Description**: Создать сессию оформления заказа

**Request**:
```json
{
  "plan": "pay_per_dream|monthly|annual",
  "success_url": "https://app.oneiroscope.com/success",
  "cancel_url": "https://app.oneiroscope.com/cancel",
  "metadata": {
    "user_id": "uuid",
    "source": "web"
  }
}
```

**Response**:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_...",
  "expires_at": "2025-11-01T13:34:56Z"
}
```

### 6.2 Check User Balance

#### GET /api/v1/billing/balance

**Description**: Получить баланс пользователя

**Response**:
```json
{
  "user_id": "uuid",
  "free_dream_available": false,
  "dream_balance": 5,
  "subscription": {
    "active": true,
    "plan": "monthly",
    "dreams_remaining": 5,
    "renews_at": "2025-12-01T00:00:00Z"
  }
}
```

### 6.3 Get Subscription Status

#### GET /api/v1/billing/subscription

**Response**:
```json
{
  "id": "uuid",
  "plan": "monthly",
  "status": "active",
  "current_period_start": "2025-11-01T00:00:00Z",
  "current_period_end": "2025-12-01T00:00:00Z",
  "cancel_at_period_end": false,
  "dreams_used_this_period": 5,
  "dreams_total_this_period": 10
}
```

### 6.4 Cancel Subscription

#### POST /api/v1/billing/subscription/cancel

**Request**:
```json
{
  "immediate": false  // Cancel at period end
}
```

**Response**:
```json
{
  "id": "uuid",
  "status": "active",
  "cancel_at_period_end": true,
  "cancels_at": "2025-12-01T00:00:00Z"
}
```

### 6.5 Transaction History

#### GET /api/v1/billing/transactions?limit=20&offset=0

**Response**:
```json
{
  "transactions": [
    {
      "id": "uuid",
      "type": "subscription",
      "status": "succeeded",
      "amount": 5.99,
      "currency": "USD",
      "description": "Monthly subscription",
      "created_at": "2025-11-01T12:00:00Z",
      "invoice_url": "https://..."
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

### 6.6 Webhook Endpoint

#### POST /api/v1/webhooks/stripe

**Description**: Обработка Stripe webhooks

**Headers**:
```
Stripe-Signature: t=1234567890,v1=abcdef...
```

**Events Handled**:
- `checkout.session.completed`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

---

## 7. Implementation Details

### 7.1 Payment Gateway Abstraction

```python
# backend/services/billing/payment_gateway.py

from abc import ABC, abstractmethod
from typing import Dict, Any
from enum import Enum

class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    YOOKASSA = "yookassa"

class PaymentGatewayInterface(ABC):
    """Abstract interface for payment gateways"""

    @abstractmethod
    async def create_checkout_session(
        self,
        amount_cents: int,
        currency: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a checkout session"""
        pass

    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a recurring subscription"""
        pass

    @abstractmethod
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Cancel a subscription"""
        pass

    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        pass

    @abstractmethod
    async def process_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Process and verify webhook"""
        pass

    @abstractmethod
    async def create_refund(
        self,
        transaction_id: str,
        amount_cents: int
    ) -> Dict[str, Any]:
        """Create a refund"""
        pass
```

### 7.2 Stripe Implementation

```python
# backend/services/billing/stripe_gateway.py

import stripe
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class StripeGateway(PaymentGatewayInterface):
    def __init__(self, api_key: str, webhook_secret: str):
        stripe.api_key = api_key
        self.webhook_secret = webhook_secret

    async def create_checkout_session(
        self,
        amount_cents: int,
        currency: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Stripe Checkout Session"""

        try:
            # For one-time payments
            if plan_id == "pay_per_dream":
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": amount_cents,
                            "product_data": {
                                "name": "Dream Analysis",
                                "description": "One-time dream analysis with full report"
                            }
                        },
                        "quantity": 1
                    }],
                    mode="payment",
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata=metadata,
                    client_reference_id=metadata.get("user_id")
                )

            # For subscriptions
            else:
                price_id = self._get_price_id(plan_id, currency)
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price": price_id,
                        "quantity": 1
                    }],
                    mode="subscription",
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata=metadata,
                    client_reference_id=metadata.get("user_id"),
                    subscription_data={
                        "metadata": metadata
                    }
                )

            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "expires_at": session.expires_at
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise

    async def process_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Verify and process Stripe webhook"""

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            return await self._handle_checkout_completed(session)

        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            return await self._handle_invoice_paid(invoice)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            return await self._handle_subscription_canceled(subscription)

        return {"status": "unhandled", "type": event["type"]}

    async def _handle_checkout_completed(self, session: Dict) -> Dict:
        """Handle successful checkout"""
        return {
            "event": "checkout_completed",
            "user_id": session.get("client_reference_id"),
            "session_id": session["id"],
            "amount_total": session["amount_total"],
            "currency": session["currency"],
            "subscription_id": session.get("subscription")
        }

    def _get_price_id(self, plan_id: str, currency: str) -> str:
        """Map plan and currency to Stripe Price ID"""
        # In production, store these in database
        price_map = {
            ("monthly", "usd"): "price_monthly_usd",
            ("monthly", "eur"): "price_monthly_eur",
            ("annual", "usd"): "price_annual_usd",
            ("annual", "eur"): "price_annual_eur"
        }
        return price_map.get((plan_id, currency.lower()))
```

### 7.3 Billing Service

```python
# backend/services/billing/service.py

from typing import Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BillingService:
    def __init__(
        self,
        payment_gateway: PaymentGatewayInterface,
        db_session
    ):
        self.gateway = payment_gateway
        self.db = db_session

    async def can_analyze_dream(self, user_id: UUID) -> dict:
        """Check if user can analyze a dream"""

        user = await self.db.get_user(user_id)

        # Check free tier
        if not user.free_dream_used:
            return {
                "allowed": True,
                "source": "free_tier",
                "remaining": 1
            }

        # Check active subscription
        subscription = await self.db.get_active_subscription(user_id)
        if subscription:
            dreams_used = await self.db.count_dreams_this_period(
                user_id,
                subscription.current_period_start,
                subscription.current_period_end
            )

            dreams_limit = self._get_plan_limit(subscription.plan_id)
            if dreams_limit == -1 or dreams_used < dreams_limit:
                return {
                    "allowed": True,
                    "source": "subscription",
                    "remaining": dreams_limit - dreams_used if dreams_limit > 0 else -1
                }

        # Check prepaid balance
        if user.dream_balance > 0:
            return {
                "allowed": True,
                "source": "prepaid",
                "remaining": user.dream_balance
            }

        return {
            "allowed": False,
            "source": None,
            "remaining": 0,
            "payment_required": True
        }

    async def consume_dream_credit(
        self,
        user_id: UUID,
        dream_id: UUID
    ) -> dict:
        """Consume one dream credit"""

        eligibility = await self.can_analyze_dream(user_id)

        if not eligibility["allowed"]:
            raise ValueError("No dream credits available")

        user = await self.db.get_user(user_id)

        # Consume free tier
        if eligibility["source"] == "free_tier":
            user.free_dream_used = True
            await self.db.save(user)

            await self.db.create_dream_usage(
                user_id=user_id,
                dream_id=dream_id,
                used_free_tier=True
            )

        # Consume from subscription
        elif eligibility["source"] == "subscription":
            subscription = await self.db.get_active_subscription(user_id)

            await self.db.create_dream_usage(
                user_id=user_id,
                dream_id=dream_id,
                used_subscription=True,
                subscription_id=subscription.id
            )

        # Consume from prepaid balance
        elif eligibility["source"] == "prepaid":
            user.dream_balance -= 1
            await self.db.save(user)

            await self.db.create_dream_usage(
                user_id=user_id,
                dream_id=dream_id,
                used_free_tier=False
            )

        return {
            "consumed": True,
            "source": eligibility["source"],
            "remaining": eligibility["remaining"] - 1
        }

    async def create_checkout(
        self,
        user_id: UUID,
        plan_id: str,
        success_url: str,
        cancel_url: str
    ) -> dict:
        """Create checkout session"""

        # Get pricing
        amount_cents, currency = self._get_plan_pricing(plan_id)

        # Generate idempotency key
        idempotency_key = f"{user_id}:{plan_id}:{datetime.utcnow().timestamp()}"

        # Create pending transaction
        transaction = await self.db.create_transaction(
            user_id=user_id,
            idempotency_key=idempotency_key,
            type="one_time" if plan_id == "pay_per_dream" else "subscription",
            status="pending",
            amount_cents=amount_cents,
            currency=currency,
            gateway=self.gateway.name
        )

        # Create checkout session
        session = await self.gateway.create_checkout_session(
            amount_cents=amount_cents,
            currency=currency,
            plan_id=plan_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "transaction_id": str(transaction.id),
                "plan_id": plan_id
            }
        )

        return session

    async def handle_payment_succeeded(
        self,
        transaction_id: UUID,
        gateway_transaction_id: str
    ):
        """Handle successful payment"""

        transaction = await self.db.get_transaction(transaction_id)

        if transaction.status == "succeeded":
            logger.warning(f"Transaction {transaction_id} already succeeded")
            return

        # Update transaction
        transaction.status = "succeeded"
        transaction.gateway_transaction_id = gateway_transaction_id
        await self.db.save(transaction)

        # Credit user account
        if transaction.type == "one_time":
            user = await self.db.get_user(transaction.user_id)
            user.dream_balance += transaction.dreams_purchased or 1
            await self.db.save(user)

        # Send confirmation email
        await self._send_payment_confirmation(transaction)

    def _get_plan_pricing(self, plan_id: str) -> tuple[int, str]:
        """Get plan pricing in cents"""
        pricing = {
            "pay_per_dream": (299, "USD"),
            "monthly": (599, "USD"),
            "annual": (5999, "USD")
        }
        return pricing.get(plan_id, (299, "USD"))

    def _get_plan_limit(self, plan_id: str) -> int:
        """Get dream limit for plan (-1 = unlimited)"""
        limits = {
            "monthly": 10,
            "annual": -1
        }
        return limits.get(plan_id, 0)
```

---

## 8. Security

### 8.1 Webhook Verification

```python
def verify_stripe_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook signature"""
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
        return True
    except:
        return False
```

### 8.2 Idempotency

```python
async def ensure_idempotency(idempotency_key: str, handler_func):
    """Ensure webhook is processed only once"""

    # Check if already processed
    existing = await db.get_transaction_by_idempotency_key(idempotency_key)
    if existing:
        return {"status": "duplicate", "transaction": existing}

    # Process and store result
    result = await handler_func()
    return result
```

### 8.3 PCI DSS Compliance

- **NO card data stored** in our database
- All payment data handled by Stripe/YooKassa (PCI DSS Level 1)
- HTTPS only for all payment endpoints
- Webhook signatures verified

---

## 9. Testing

### 9.1 Test Cards (Stripe)

```yaml
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
Insufficient funds: 4000 0000 0000 9995
3D Secure: 4000 0025 0000 3155
```

### 9.2 Test Scenarios

```python
# tests/integration/test_billing.py

@pytest.mark.asyncio
async def test_free_tier_dream():
    """New user can analyze 1 dream for free"""
    user = await create_test_user()

    eligibility = await billing_service.can_analyze_dream(user.id)
    assert eligibility["allowed"] == True
    assert eligibility["source"] == "free_tier"

    await billing_service.consume_dream_credit(user.id, dream_id)

    eligibility = await billing_service.can_analyze_dream(user.id)
    assert eligibility["allowed"] == False

@pytest.mark.asyncio
async def test_subscription_dream_limit():
    """Monthly subscription allows 10 dreams"""
    user = await create_test_user_with_subscription("monthly")

    for i in range(10):
        eligibility = await billing_service.can_analyze_dream(user.id)
        assert eligibility["allowed"] == True
        await billing_service.consume_dream_credit(user.id, uuid4())

    eligibility = await billing_service.can_analyze_dream(user.id)
    assert eligibility["allowed"] == False

@pytest.mark.asyncio
async def test_webhook_idempotency():
    """Duplicate webhook should not double-credit"""
    webhook_payload = create_test_webhook("payment_succeeded")

    result1 = await billing_service.handle_webhook(webhook_payload)
    result2 = await billing_service.handle_webhook(webhook_payload)

    user = await db.get_user(user_id)
    assert user.dream_balance == 1  # Only credited once
```

---

## 10. Monitoring

### 10.1 Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Transaction metrics
billing_transactions_total = Counter(
    'billing_transactions_total',
    'Total billing transactions',
    ['gateway', 'type', 'status']
)

billing_revenue = Counter(
    'billing_revenue_cents',
    'Total revenue in cents',
    ['currency', 'plan']
)

# Webhook metrics
billing_webhooks_received = Counter(
    'billing_webhooks_received_total',
    'Webhooks received',
    ['gateway', 'event_type', 'status']
)

billing_webhook_processing_duration = Histogram(
    'billing_webhook_processing_duration_seconds',
    'Webhook processing time',
    ['gateway', 'event_type']
)

# Subscription metrics
billing_active_subscriptions = Gauge(
    'billing_active_subscriptions',
    'Active subscriptions',
    ['plan']
)

# Conversion metrics
billing_conversion_rate = Gauge(
    'billing_conversion_rate',
    'Free to paid conversion rate'
)
```

### 10.2 Alerts

```yaml
alerts:
  - name: HighPaymentFailureRate
    condition: rate(billing_transactions_total{status="failed"}[5m]) > 0.05
    severity: critical
    message: "Payment failure rate above 5%"

  - name: WebhookProcessingDelayed
    condition: billing_webhook_processing_duration_seconds > 2
    severity: warning
    message: "Webhook processing taking too long"

  - name: RefundSpikeDetected
    condition: rate(billing_transactions_total{type="refund"}[1h]) > 10
    severity: warning
    message: "Unusual refund activity"
```

---

## 11. Deployment

### 11.1 Environment Variables

```bash
# .env.billing

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# YooKassa
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=...

# Pricing (Price IDs)
STRIPE_PRICE_MONTHLY_USD=price_...
STRIPE_PRICE_ANNUAL_USD=price_...

# URLs
STRIPE_SUCCESS_URL=https://app.oneiroscope.com/payment/success
STRIPE_CANCEL_URL=https://app.oneiroscope.com/payment/cancel
```

---

## 12. Cost Estimates

### 12.1 Transaction Fees

```yaml
Stripe:
  - 2.9% + $0.30 per transaction (US)
  - 1.4% + €0.25 per transaction (EU)
  - 0.5% per payout

YooKassa (Russia):
  - 2.8% + 0 RUB per transaction
  - Additional 0.5% for international cards

Examples:
  - $2.99 dream: $0.39 fee (13%)
  - $5.99 subscription: $0.47 fee (7.8%)
  - $59.99 annual: $2.04 fee (3.4%)
```

### 12.2 Monthly Cost Projection

```yaml
Scenario: 1000 active users

Revenue:
  - 200 pay-per-dream × $2.99 = $598
  - 100 monthly × $5.99 = $599
  - 20 annual × $59.99 = $1,200
  Total: $2,397/month

Fees:
  - Stripe fees (~3%): $72
  - Payout fees: $12
  Total fees: $84/month

Net revenue: $2,313/month
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-01
**Owner**: Billing Module Team
