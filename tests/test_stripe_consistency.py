"""Tests for the local-first / Stripe-second creation ordering.

These tests prove that when Stripe fails, the local row already exists so a
reconciliation job can retry without creating duplicates, and that the
idempotency_key passed to Stripe matches the local row UUID.
"""

from uuid import uuid4

import stripe


class TestLocalFirstOrdering:
    """Local row must be committed BEFORE the Stripe API is called."""

    def test_customer_persists_when_stripe_fails(self, client, mock_stripe, db_session):
        from app.models.customer import Customer

        mock_stripe.Customer.create.side_effect = stripe.StripeError("simulated outage")

        response = client.post(
            "/api/v1/customers",
            json={"email": "orphan@example.com", "name": "Orphan"},
        )
        assert response.status_code == 502

        row = db_session.query(Customer).filter_by(email="orphan@example.com").first()
        assert row is not None, "local row must persist for reconciliation"
        assert row.stripe_customer_id is None

    def test_customer_create_passes_local_id_as_idempotency_key(self, client, mock_stripe):
        response = client.post(
            "/api/v1/customers",
            json={"email": "idem@example.com", "name": "Idem"},
        )
        assert response.status_code == 201
        local_id = response.json()["id"]

        _, kwargs = mock_stripe.Customer.create.call_args
        assert kwargs["idempotency_key"] == local_id
        assert kwargs["metadata"] == {"local_id": local_id}

    def test_payment_persists_when_stripe_fails(self, client, mock_stripe, db_session):
        from app.models.payment import Payment, PaymentStatus

        # Customer first (succeeds)
        customer_id = client.post(
            "/api/v1/customers",
            json={"email": f"pay_{uuid4().hex[:8]}@example.com", "name": "P"},
        ).json()["id"]

        mock_stripe.PaymentIntent.create.side_effect = stripe.StripeError("outage")

        response = client.post(
            "/api/v1/payments",
            json={"customer_id": customer_id, "amount": 25.00, "currency": "usd"},
        )
        assert response.status_code == 502

        row = db_session.query(Payment).filter_by(customer_id=customer_id).first()
        assert row is not None
        assert row.stripe_payment_intent_id is None
        assert row.status == PaymentStatus.PENDING
