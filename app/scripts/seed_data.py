"""Seed initial data for development and testing."""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models.plan import Plan, PlanInterval
from app.models.customer import Customer


# Default plans
SEED_PLANS = [
    {
        "name": "Starter",
        "description": "Perfect for individuals and small projects",
        "amount": 9.99,
        "currency": "usd",
        "interval": PlanInterval.MONTHLY,
        "interval_count": 1,
        "trial_days": 14,
        "features": json.dumps([
            "Up to 1,000 responses/month",
            "Basic analytics",
            "Email support",
            "1 user seat",
        ]),
        "sort_order": 1,
    },
    {
        "name": "Professional",
        "description": "For growing teams that need more power",
        "amount": 29.99,
        "currency": "usd",
        "interval": PlanInterval.MONTHLY,
        "interval_count": 1,
        "trial_days": 14,
        "features": json.dumps([
            "Up to 10,000 responses/month",
            "Advanced analytics",
            "Priority email support",
            "5 user seats",
            "Custom branding",
            "API access",
        ]),
        "sort_order": 2,
    },
    {
        "name": "Business",
        "description": "For organizations that need full capabilities",
        "amount": 79.99,
        "currency": "usd",
        "interval": PlanInterval.MONTHLY,
        "interval_count": 1,
        "trial_days": 7,
        "features": json.dumps([
            "Unlimited responses",
            "Full analytics suite",
            "Phone & email support",
            "Unlimited user seats",
            "Custom branding",
            "API access",
            "SSO integration",
            "Data export",
        ]),
        "sort_order": 3,
    },
    {
        "name": "Enterprise",
        "description": "Custom solutions for large organizations",
        "amount": 199.99,
        "currency": "usd",
        "interval": PlanInterval.MONTHLY,
        "interval_count": 1,
        "trial_days": 0,
        "features": json.dumps([
            "Everything in Business",
            "Dedicated account manager",
            "Custom integrations",
            "SLA guarantee",
            "On-premise deployment option",
            "Advanced security",
            "Audit logs",
        ]),
        "sort_order": 4,
    },
    {
        "name": "Starter Annual",
        "description": "Starter plan billed annually (save 20%)",
        "amount": 95.88,
        "currency": "usd",
        "interval": PlanInterval.YEARLY,
        "interval_count": 1,
        "trial_days": 14,
        "features": json.dumps([
            "Up to 1,000 responses/month",
            "Basic analytics",
            "Email support",
            "1 user seat",
            "Annual billing discount",
        ]),
        "sort_order": 5,
    },
    {
        "name": "Professional Annual",
        "description": "Professional plan billed annually (save 20%)",
        "amount": 287.88,
        "currency": "usd",
        "interval": PlanInterval.YEARLY,
        "interval_count": 1,
        "trial_days": 14,
        "features": json.dumps([
            "Up to 10,000 responses/month",
            "Advanced analytics",
            "Priority email support",
            "5 user seats",
            "Custom branding",
            "API access",
            "Annual billing discount",
        ]),
        "sort_order": 6,
    },
]

SEED_CUSTOMERS = [
    {
        "email": "demo@acmecorp.com",
        "name": "Acme Corporation",
        "currency": "usd",
        "country": "US",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94102",
    },
    {
        "email": "billing@techstartup.io",
        "name": "TechStartup Inc",
        "currency": "usd",
        "country": "US",
        "city": "Austin",
        "state": "TX",
        "postal_code": "73301",
    },
    {
        "email": "admin@eurocompany.eu",
        "name": "Euro Company GmbH",
        "currency": "eur",
        "country": "DE",
        "city": "Berlin",
        "postal_code": "10115",
    },
    {
        "email": "finance@ukbusiness.co.uk",
        "name": "UK Business Ltd",
        "currency": "gbp",
        "country": "GB",
        "city": "London",
        "postal_code": "EC1A 1BB",
    },
    {
        "email": "accounts@tokyotech.jp",
        "name": "Tokyo Tech KK",
        "currency": "jpy",
        "country": "JP",
        "city": "Tokyo",
        "postal_code": "100-0001",
    },
]


def seed_data():
    """Insert seed data into the database."""
    print("Seeding database...")

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed plans
        existing_plans = db.query(Plan).count()
        if existing_plans == 0:
            for plan_data in SEED_PLANS:
                plan = Plan(**plan_data)
                db.add(plan)
            db.commit()
            print(f"  ✓ Seeded {len(SEED_PLANS)} plans")
        else:
            print(f"  - Skipping plans (already {existing_plans} exist)")

        # Seed demo customers
        existing_customers = db.query(Customer).count()
        if existing_customers == 0:
            for customer_data in SEED_CUSTOMERS:
                customer = Customer(**customer_data)
                db.add(customer)
            db.commit()
            print(f"  ✓ Seeded {len(SEED_CUSTOMERS)} demo customers")
        else:
            print(f"  - Skipping customers (already {existing_customers} exist)")

        print("Seeding complete!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
