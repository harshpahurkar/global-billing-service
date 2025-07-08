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
