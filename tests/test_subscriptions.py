"""Tests for subscription lifecycle."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4


class TestSubscriptionEndpoints:
    """Test suite for /api/v1/subscriptions endpoints."""

    def _create_customer(self, client):
        """Helper to create a test customer."""
        response = client.post(
            "/api/v1/customers",
            json={"email": f"sub_{uuid4().hex[:8]}@example.com", "name": "Sub Tester"},
        )
        return response.json()["id"]

    def _create_plan(self, client):
        """Helper to create a test plan."""
        response = client.post(
            "/api/v1/plans",
            json={
                "name": "Pro Plan",
                "amount": 29.99,
                "currency": "usd",
                "interval": "monthly",
            },
        )
        return response.json()["id"]

    def test_create_subscription(self, client, mock_stripe):
        """Test creating a new subscription."""
        customer_id = self._create_customer(client)
        plan_id = self._create_plan(client)

        response = client.post(
            "/api/v1/subscriptions",
            json={
                "customer_id": customer_id,
                "plan_id": plan_id,
                "currency": "usd",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == customer_id
        assert data["plan_id"] == plan_id
        assert data["status"] == "active"

    def test_get_subscription(self, client, mock_stripe):
        """Test getting a subscription by ID."""
        customer_id = self._create_customer(client)
        plan_id = self._create_plan(client)

        create_response = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        )
        sub_id = create_response.json()["id"]

        response = client.get(f"/api/v1/subscriptions/{sub_id}")
        assert response.status_code == 200
        assert response.json()["id"] == sub_id

    def test_cancel_subscription(self, client, mock_stripe):
        """Test canceling a subscription."""
        customer_id = self._create_customer(client)
        plan_id = self._create_plan(client)

        create_response = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        )
        sub_id = create_response.json()["id"]

        response = client.patch(f"/api/v1/subscriptions/{sub_id}/cancel?at_period_end=false")
        assert response.status_code == 200
        assert response.json()["status"] == "canceled"

    def test_upgrade_subscription(self, client, mock_stripe):
        """Test upgrading a subscription to a new plan."""
        customer_id = self._create_customer(client)
        plan_id = self._create_plan(client)

        # Create a second plan for upgrade
        upgrade_response = client.post(
            "/api/v1/plans",
            json={
                "name": "Enterprise Plan",
                "amount": 99.99,
                "currency": "usd",
                "interval": "monthly",
            },
        )
        new_plan_id = upgrade_response.json()["id"]

        # Create subscription
        create_response = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        )
        sub_id = create_response.json()["id"]

        # Upgrade
        response = client.patch(
            f"/api/v1/subscriptions/{sub_id}/upgrade",
            json={"new_plan_id": new_plan_id},
        )
        assert response.status_code == 200
        assert response.json()["plan_id"] == new_plan_id

    def test_list_subscriptions(self, client, mock_stripe):
        """Test listing subscriptions."""
        customer_id = self._create_customer(client)
        plan_id = self._create_plan(client)

        # Create 2 subscriptions
        for _ in range(2):
            client.post(
                "/api/v1/subscriptions",
                json={"customer_id": customer_id, "plan_id": plan_id},
            )

        response = client.get(f"/api/v1/subscriptions?customer_id={customer_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_subscription_not_found(self, client):
        """Test getting non-existent subscription."""
        response = client.get("/api/v1/subscriptions/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
