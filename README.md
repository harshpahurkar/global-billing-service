# Global Billing Microservice

A scalable billing and subscription management microservice built with Python (FastAPI) to support recurring payments, one-time transactions, and multi-currency payment processing.

## Features

- **Subscription Lifecycle Management** — Create, upgrade, downgrade, cancel, and reactivate subscriptions
- **Multi-Currency Support** — Process payments in 39+ currencies with automatic exchange rate handling
- **Stripe Integration** — Checkout workflows, invoice generation, and payment processing via Stripe sandbox APIs
- **Invoice Management** — Automated invoice generation with PDF-ready line items
- **Webhook Processing** — Real-time event handling for payment status updates
- **RESTful API** — Clean, versioned API with OpenAPI/Swagger documentation

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL 15
- **Payments:** Stripe API (sandbox mode)
- **Containerization:** Docker, Docker Compose
- **Cloud:** AWS ECS (Fargate)
- **CI/CD:** GitHub Actions

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose
- Stripe account (test mode)

### Local Development

```bash
# Clone the repo
git clone https://github.com/harshpahurkar/global-billing-service.git
cd global-billing-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Stripe test keys and database credentials

# Run database migrations
alembic upgrade head

# Seed initial data (plans, currencies)
python -m app.scripts.seed_data

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Using Docker

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose exec api alembic upgrade head

# Seed data
docker-compose exec api python -m app.scripts.seed_data
```

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create a customer |
| GET | `/api/v1/customers/{id}` | Get customer details |
| POST | `/api/v1/subscriptions` | Create a subscription |
| PATCH | `/api/v1/subscriptions/{id}/upgrade` | Upgrade subscription |
| PATCH | `/api/v1/subscriptions/{id}/cancel` | Cancel subscription |
| POST | `/api/v1/checkout/sessions` | Create checkout session |
| GET | `/api/v1/invoices` | List invoices |
| POST | `/api/v1/webhooks/stripe` | Stripe webhook handler |
| GET | `/api/v1/currencies` | List supported currencies |

## Project Structure

```
global-billing-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── customers.py
│   │       │   ├── plans.py
│   │       │   ├── subscriptions.py
│   │       │   ├── invoices.py
│   │       │   ├── payments.py
│   │       │   ├── checkout.py
│   │       │   ├── webhooks.py
│   │       │   └── currencies.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── customer.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── invoice.py
│   │   └── payment.py
│   ├── schemas/
│   │   ├── customer.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── invoice.py
│   │   └── payment.py
│   ├── services/
│   │   ├── stripe_service.py
│   │   ├── subscription_service.py
│   │   ├── invoice_service.py
│   │   └── currency_service.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── scripts/
│   │   └── seed_data.py
│   └── main.py
├── alembic/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://billing:billing@localhost:5432/billing_db` |
| `STRIPE_SECRET_KEY` | Stripe secret key (test mode) | — |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | — |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | — |
| `APP_ENV` | Application environment | `development` |
| `APP_HOST` | Server host | `0.0.0.0` |
| `APP_PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `info` |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_subscriptions.py -v
```

## Deployment

The service is containerized and deployed on AWS ECS (Fargate). See the `.github/workflows/` directory for CI/CD pipeline configuration.

```bash
# Build production Docker image
docker build -t global-billing-service:latest .

# Tag and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag global-billing-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/global-billing-service:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/global-billing-service:latest
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
