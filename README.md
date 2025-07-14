<div align="center">

# 💳 Global Billing Microservice

**A production-ready billing and subscription management microservice powering multi-currency payments at scale.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Stripe](https://img.shields.io/badge/Stripe-API-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![AWS](https://img.shields.io/badge/AWS-ECS_Fargate-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/ecs)

[![Tests](https://img.shields.io/badge/tests-27%20passed-success?style=flat-square)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen?style=flat-square)]()
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-black?style=flat-square)]()

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API Reference](#-api-reference) · [Deployment](#-deployment) · [Contributing](#contributing)

</div>

---

## 📋 Overview

Global Billing Service is a **full-stack billing microservice** designed to handle complex subscription management, multi-currency payment processing, and invoice generation for SaaS platforms. Built with a clean service-oriented architecture, it integrates with Stripe's payment infrastructure and deploys seamlessly to AWS ECS Fargate.

### Why This Project?

Most billing systems are either too simple (can't handle upgrades/downgrades) or too complex (require months to set up). This service hits the sweet spot:

- **39 currencies** supported out of the box with proper minimum charge validation
- **Full subscription lifecycle** — create → upgrade → downgrade → cancel → reactivate
- **Webhook-driven** — real-time payment status updates via Stripe webhooks
- **Production-ready** — Docker, CI/CD, health checks, structured logging, and AWS deployment

---

## ✨ Features

<table>
<tr>
<td width="50%">

**🔄 Subscription Management**
- Create, upgrade, downgrade subscriptions
- Cancel with immediate or end-of-period options
- Trial period support with configurable durations
- Automatic status tracking (active, past_due, canceled)

**💰 Payment Processing**
- Stripe Checkout session integration
- Payment intent creation and tracking
- Refund support with partial/full options
- Idempotent payment operations

</td>
<td width="50%">

**🌍 Multi-Currency Support**
- 39 currencies (USD, EUR, GBP, JPY, CAD...)
- Per-currency minimum charge validation
- Currency metadata (symbol, name, decimals)
- Automatic formatting for zero-decimal currencies

**📄 Invoice & Billing**
- Automated invoice generation with line items
- Sequential invoice numbering (INV-YYYYMM-XXXX)
- Pay, void, and track invoice status
- Tax and discount support

</td>
</tr>
</table>

**Additional capabilities:**
- 🔐 **API Key Authentication** — JWT token generation with secure hashing
- 📡 **Webhook Processing** — Stripe event verification and handling
- 🏥 **Health Monitoring** — Built-in health check endpoint
- 📊 **Structured Logging** — Request/response logging with `structlog`
- 🔒 **CORS Configuration** — Configurable cross-origin resource sharing

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│                   (Web App / Mobile / Admin Panel)                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway / Load Balancer                   │
│                        (AWS ALB / nginx)                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Global Billing Service (FastAPI)                │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  API Layer   │  │  Service     │  │  Data Layer            │  │
│  │  (v1)        │  │  Layer       │  │                        │  │
│  │              │  │              │  │  ┌──────────────────┐  │  │
│  │ • Customers  │  │ • Stripe     │  │  │  SQLAlchemy ORM  │  │  │
│  │ • Plans      │──│ • Subscript. │──│  │  (5 Models)      │  │  │
│  │ • Subscript. │  │ • Invoice    │  │  └────────┬─────────┘  │  │
│  │ • Invoices   │  │ • Currency   │  │           │            │  │
│  │ • Payments   │  │              │  │  ┌────────▼─────────┐  │  │
│  │ • Checkout   │  │              │  │  │  PostgreSQL 15   │  │  │
│  │ • Webhooks   │  │              │  │  │  (via Alembic)   │  │  │
│  │ • Currencies │  │              │  │  └──────────────────┘  │  │
│  └─────────────┘  └──────┬───────┘  └────────────────────────┘  │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    Stripe API          │
              │  (Sandbox / Live)      │
              │                        │
              │  • Customers           │
              │  • Products & Prices   │
              │  • Subscriptions       │
              │  • Payment Intents     │
              │  • Invoices            │
              │  • Checkout Sessions   │
              │  • Webhooks ──────────────► POST /api/v1/webhooks/stripe
              └────────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| **Runtime** | Python 3.11 | Core language |
| **Framework** | FastAPI 0.104 | Async REST API with auto-generated docs |
| **ORM** | SQLAlchemy 2.0 | Database models & queries |
| **Migrations** | Alembic 1.13 | Schema versioning |
| **Database** | PostgreSQL 15 | Primary data store |
| **Payments** | Stripe API 7.8 | Payment processing |
| **Validation** | Pydantic 2.5 | Request/response schemas |
| **Auth** | python-jose, passlib | JWT & API key hashing |
| **Logging** | structlog | Structured JSON logging |
| **Testing** | pytest 7.4 | Unit & integration tests |
| **Container** | Docker + Compose | Local dev & deployment |
| **CI/CD** | GitHub Actions | Automated test & deploy |
| **Cloud** | AWS ECS Fargate | Production hosting |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+** (or use Docker)
- **Stripe account** — [Sign up for test mode](https://dashboard.stripe.com/register)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/harshpahurkar/global-billing-service.git
cd global-billing-service

# Copy environment config
cp .env.example .env
# Edit .env with your Stripe test keys

# Start everything
docker-compose up --build

# In another terminal — run migrations & seed data
docker-compose exec api alembic upgrade head
docker-compose exec api python -m app.scripts.seed_data
```

The API is now running at **http://localhost:8000** 🎉

### Option 2: Local Development

```bash
# Clone & setup
git clone https://github.com/harshpahurkar/global-billing-service.git
cd global-billing-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL and Stripe test keys

# Run migrations
alembic upgrade head

# Seed demo data (6 plans + 5 customers)
python -m app.scripts.seed_data

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Verify It's Running

```bash
# Health check
curl http://localhost:8000/health
# → {"status": "healthy", "service": "global-billing-service"}

# List supported currencies
curl http://localhost:8000/api/v1/currencies
# → {"currencies": [{"code": "usd", "name": "US Dollar", ...}, ...]}
```

📖 **Interactive API docs:** http://localhost:8000/docs

---

## 📚 API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints

<details>
<summary><b>👤 Customers</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/customers` | Create a new customer |
| `GET` | `/customers` | List customers (paginated) |
| `GET` | `/customers/{id}` | Get customer by ID |
| `PATCH` | `/customers/{id}` | Update customer details |
| `DELETE` | `/customers/{id}` | Soft-delete a customer |

**Create Customer Example:**

```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@acme.com",
    "name": "John Doe",
    "currency": "usd",
    "country": "US"
  }'
```

</details>

<details>
<summary><b>📦 Plans</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/plans` | Create a billing plan |
| `GET` | `/plans` | List all plans |
| `GET` | `/plans/{id}` | Get plan details |
| `PATCH` | `/plans/{id}` | Update a plan |
| `DELETE` | `/plans/{id}` | Deactivate a plan |

**Create Plan Example:**

```bash
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pro Plan",
    "amount": 29.99,
    "currency": "usd",
    "interval": "monthly",
    "trial_days": 14,
    "features": "[\"Unlimited users\", \"API access\", \"Priority support\"]"
  }'
```

</details>

<details>
<summary><b>🔄 Subscriptions</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/subscriptions` | Create a subscription |
| `GET` | `/subscriptions` | List subscriptions (filterable) |
| `GET` | `/subscriptions/{id}` | Get subscription details |
| `PATCH` | `/subscriptions/{id}/upgrade` | Upgrade to a new plan |
| `PATCH` | `/subscriptions/{id}/downgrade` | Downgrade to a lower plan |
| `PATCH` | `/subscriptions/{id}/cancel` | Cancel a subscription |
| `PATCH` | `/subscriptions/{id}/reactivate` | Reactivate a canceled subscription |

**Upgrade Subscription Example:**

```bash
curl -X PATCH http://localhost:8000/api/v1/subscriptions/{sub_id}/upgrade \
  -H "Content-Type: application/json" \
  -d '{"new_plan_id": "plan-uuid-here"}'
```

</details>

<details>
<summary><b>🧾 Invoices</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/invoices` | Create an invoice |
| `GET` | `/invoices` | List invoices (filterable) |
| `GET` | `/invoices/{id}` | Get invoice details |
| `POST` | `/invoices/{id}/pay` | Mark invoice as paid |
| `POST` | `/invoices/{id}/void` | Void an invoice |

</details>

<details>
<summary><b>💳 Payments & Checkout</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/payments` | Record a payment |
| `GET` | `/payments` | List payments |
| `POST` | `/payments/{id}/refund` | Refund a payment |
| `POST` | `/checkout/sessions` | Create a Stripe Checkout session |
| `POST` | `/webhooks/stripe` | Process Stripe webhook events |

</details>

<details>
<summary><b>🌍 Currencies</b></summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/currencies` | List all 39 supported currencies |

**Supported currencies include:** USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, INR, BRL, and 29 more.

</details>

---

## 📁 Project Structure

```
global-billing-service/
│
├── app/
│   ├── api/v1/
│   │   ├── endpoints/          # Route handlers
│   │   │   ├── customers.py    # Customer CRUD
│   │   │   ├── plans.py        # Plan management
│   │   │   ├── subscriptions.py# Subscription lifecycle
│   │   │   ├── invoices.py     # Invoice operations
│   │   │   ├── payments.py     # Payment processing
│   │   │   ├── checkout.py     # Stripe Checkout sessions
│   │   │   ├── webhooks.py     # Stripe webhook handler
│   │   │   └── currencies.py   # Currency listing
│   │   └── router.py           # API router aggregation
│   │
│   ├── core/
│   │   ├── config.py           # Pydantic settings management
│   │   ├── security.py         # JWT & API key utilities
│   │   └── exceptions.py       # Custom exception hierarchy
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── customer.py         # Customer model
│   │   ├── plan.py             # Plan & PlanInterval enum
│   │   ├── subscription.py     # Subscription & status enum
│   │   ├── invoice.py          # Invoice & status enum
│   │   └── payment.py          # Payment & method/status enums
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── customer.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── invoice.py
│   │   ├── payment.py
│   │   └── checkout.py
│   │
│   ├── services/               # Business logic layer
│   │   ├── stripe_service.py   # Stripe API abstraction
│   │   ├── subscription_service.py  # Subscription operations
│   │   ├── invoice_service.py  # Invoice generation & management
│   │   └── currency_service.py # Multi-currency support (39 currencies)
│   │
│   ├── db/
│   │   ├── base.py             # Base model, GUID type, mixins
│   │   └── session.py          # Database session factory
│   │
│   ├── scripts/
│   │   └── seed_data.py        # Database seeding (plans + customers)
│   │
│   └── main.py                 # FastAPI application factory
│
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial.py      # Initial schema migration
│
├── tests/                      # Test suite (27 tests)
│   ├── conftest.py             # Fixtures, mocks, test DB setup
│   ├── test_customers.py       # Customer endpoint tests
│   ├── test_plans.py           # Plan endpoint tests
│   ├── test_subscriptions.py   # Subscription lifecycle tests
│   ├── test_invoices_payments.py  # Invoice & payment tests
│   └── test_currencies.py      # Currency & health check tests
│
├── .github/workflows/
│   └── ci-cd.yml               # GitHub Actions pipeline
│
├── .aws/
│   └── task-definition.json    # ECS Fargate task config
│
├── docker-compose.yml          # Local dev environment
├── Dockerfile                  # Production container
├── Makefile                    # Developer workflow commands
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── pytest.ini                  # Test configuration
```

---

## 🧪 Testing

The project includes **27 tests** covering all major features:

```bash
# Run all tests
make test

# Run with verbose output
pytest -v --tb=short

# Run with coverage report
make test-cov

# Run a specific test module
pytest tests/test_subscriptions.py -v
```

**Test breakdown:**

| Module | Tests | Coverage |
|:-------|:-----:|:---------|
| Customers | 7 | CRUD, pagination, soft-delete |
| Plans | 5 | Create, list, update, deactivate |
| Subscriptions | 6 | Create, upgrade, cancel, list |
| Invoices & Payments | 6 | Create, pay, void, list |
| Currencies & Health | 3 | Currency listing, health check |

All tests use an **in-memory SQLite database** with mocked Stripe API calls — no external services required.

---

## ⚙️ Configuration

All configuration is managed via environment variables. Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Description | Required | Default |
|:---------|:------------|:--------:|:--------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ | `postgresql://billing:billing@localhost:5432/billing_db` |
| `STRIPE_SECRET_KEY` | Stripe API secret key | ✅ | — |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | ✅ | — |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | ❌ | — |
| `APP_ENV` | Environment (`development` / `production`) | ❌ | `development` |
| `APP_PORT` | Server port | ❌ | `8000` |
| `LOG_LEVEL` | Logging verbosity | ❌ | `info` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | ❌ | `["http://localhost:3000"]` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | ❌ | `60` |

---

## 🚢 Deployment

### CI/CD Pipeline

The GitHub Actions pipeline (`ci-cd.yml`) automates the full deployment flow:

```
Push to main → Lint → Test (PostgreSQL) → Build Docker → Push to ECR → Deploy to ECS
```

### AWS Architecture

```
                    ┌──────────────────┐
                    │   Route 53 DNS   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  ALB (HTTPS:443) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   ECS Fargate    │
                    │   ┌───────────┐  │
                    │   │  Task 1   │  │
                    │   │ (billing  │  │
                    │   │  -api)    │  │
                    │   └───────────┘  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──┐  ┌───────▼──────┐  ┌───▼──────────┐
    │ RDS        │  │ Secrets      │  │ CloudWatch   │
    │ PostgreSQL │  │ Manager      │  │ Logs         │
    └────────────┘  └──────────────┘  └──────────────┘
```

### Manual Deployment

```bash
# Build production image
docker build -t global-billing-service:latest .

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag global-billing-service:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/global-billing-service:latest

docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/global-billing-service:latest
```

---

## 🛠 Development

### Make Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make dev           # Start dev server (hot reload)
make test          # Run test suite
make test-cov      # Run tests with coverage
make lint          # Run linter
make docker-up     # Start Docker services
make docker-down   # Stop Docker services
make migrate       # Run database migrations
make seed          # Seed demo data
make clean         # Remove cached files
```

### Database Migrations

```bash
# Create a new migration
make migrate-create msg="add_payment_method_column"

# Apply migrations
make migrate

# Rollback one version
alembic downgrade -1
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ using FastAPI and Stripe**

[⬆ Back to top](#-global-billing-microservice)

</div>
