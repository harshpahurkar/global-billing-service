"""Tests for invoice and payment endpoints."""

import pytest
from uuid import uuid4


class TestInvoiceEndpoints:
    """Test suite for /api/v1/invoices endpoints."""

    def _create_customer(self, client):
        response = client.post(
            "/api/v1/customers",
            json={"email": f"inv_{uuid4().hex[:8]}@example.com", "name": "Invoice Tester"},
        )
        return response.json()["id"]

    def test_create_invoice(self, client, mock_stripe):
        """Test creating an invoice."""
        customer_id = self._create_customer(client)

        response = client.post(
            "/api/v1/invoices",
            json={
                "customer_id": customer_id,
                "subtotal": 29.99,
                "tax": 3.00,
                "currency": "usd",
                "description": "Monthly subscription",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subtotal"] == 29.99
        assert data["tax"] == 3.00
        assert data["total"] == 32.99
        assert data["status"] == "open"

    def test_pay_invoice(self, client, mock_stripe):
        """Test paying an invoice."""
        customer_id = self._create_customer(client)

        create_response = client.post(
            "/api/v1/invoices",
            json={"customer_id": customer_id, "subtotal": 29.99, "currency": "usd"},
        )
        invoice_id = create_response.json()["id"]

        response = client.post(f"/api/v1/invoices/{invoice_id}/pay")
        assert response.status_code == 200
        assert response.json()["status"] == "paid"
        assert response.json()["amount_due"] == 0

    def test_void_invoice(self, client, mock_stripe):
        """Test voiding an invoice."""
        customer_id = self._create_customer(client)

        create_response = client.post(
            "/api/v1/invoices",
            json={"customer_id": customer_id, "subtotal": 29.99, "currency": "usd"},
        )
        invoice_id = create_response.json()["id"]

        response = client.post(f"/api/v1/invoices/{invoice_id}/void")
        assert response.status_code == 200
        assert response.json()["status"] == "void"

    def test_list_invoices(self, client, mock_stripe):
        """Test listing invoices."""
        customer_id = self._create_customer(client)

        for _ in range(3):
            client.post(
                "/api/v1/invoices",
                json={"customer_id": customer_id, "subtotal": 10.00, "currency": "usd"},
            )

        response = client.get(f"/api/v1/invoices?customer_id={customer_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 3


class TestPaymentEndpoints:
    """Test suite for /api/v1/payments endpoints."""

    def _create_customer(self, client):
        response = client.post(
            "/api/v1/customers",
            json={"email": f"pay_{uuid4().hex[:8]}@example.com", "name": "Payment Tester"},
        )
        return response.json()["id"]

    def test_create_payment(self, client, mock_stripe):
        """Test creating a payment."""
        customer_id = self._create_customer(client)

        response = client.post(
            "/api/v1/payments",
            json={
                "customer_id": customer_id,
                "amount": 49.99,
                "currency": "usd",
                "payment_method": "card",
                "description": "One-time charge",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 49.99
        assert data["status"] == "pending"

    def test_list_payments(self, client, mock_stripe):
        """Test listing payments."""
        customer_id = self._create_customer(client)

        client.post(
            "/api/v1/payments",
            json={"customer_id": customer_id, "amount": 10.00, "currency": "usd"},
        )

        response = client.get(f"/api/v1/payments?customer_id={customer_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestRefundDecimalArithmetic:
    """Multi-step partial refunds must use Decimal arithmetic so cents don't
    drift from binary-float rounding."""

    def _create_customer(self, client):
        from uuid import uuid4
        return client.post(
            "/api/v1/customers",
            json={"email": f"dec_{uuid4().hex[:8]}@example.com", "name": "Dec"},
        ).json()["id"]

    def test_partial_refunds_sum_exactly_in_decimal(self, client, mock_stripe, db_session):
        from decimal import Decimal
        from app.models.payment import Payment, PaymentStatus

        customer_id = self._create_customer(client)
        pid = client.post(
            "/api/v1/payments",
            json={"customer_id": customer_id, "amount": 10.00, "currency": "usd"},
        ).json()["id"]

        # Force SUCCEEDED so refunds are allowed.
        payment = db_session.query(Payment).filter_by(id=pid).first()
        payment.status = PaymentStatus.SUCCEEDED
        db_session.commit()

        client.post(f"/api/v1/payments/{pid}/refund", json={"amount": 0.10})
        client.post(f"/api/v1/payments/{pid}/refund", json={"amount": 0.20})

        db_session.expire_all()
        payment = db_session.query(Payment).filter_by(id=pid).first()
        # Exact: 0.10 + 0.20 == 0.30 in Decimal; would be 0.30000000000000004
        # under float arithmetic.
        assert payment.refunded_amount == Decimal("0.30")
        assert payment.status == PaymentStatus.PARTIALLY_REFUNDED

    def test_refund_reason_validated(self, client, mock_stripe, db_session):
        """Stripe accepts only 3 reason values; anything else should fall back
        to 'requested_by_customer' rather than being silently dropped (the old
        bug always sent 'requested_by_customer' regardless of input)."""
        from app.models.payment import Payment, PaymentStatus

        customer_id = self._create_customer(client)
        pid = client.post(
            "/api/v1/payments",
            json={"customer_id": customer_id, "amount": 5.00, "currency": "usd"},
        ).json()["id"]
        payment = db_session.query(Payment).filter_by(id=pid).first()
        payment.status = PaymentStatus.SUCCEEDED
        db_session.commit()

        client.post(
            f"/api/v1/payments/{pid}/refund",
            json={"amount": 1.00, "reason": "fraudulent"},
        )
        _, kwargs = mock_stripe.Refund.create.call_args
        assert kwargs["reason"] == "fraudulent"
