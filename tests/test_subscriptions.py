"""Tests for subscription lifecycle."""

from datetime import UTC
from unittest.mock import MagicMock
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


class TestSubscriptionSemantics:
    """Cancel-at-period-end, upgrade vs downgrade proration, period-from-Stripe."""

    def _setup(self, client):
        from uuid import uuid4
        customer_id = client.post(
            "/api/v1/customers",
            json={"email": f"sem_{uuid4().hex[:8]}@example.com", "name": "S"},
        ).json()["id"]
        plan_a_id = client.post(
            "/api/v1/plans",
            json={"name": "A", "amount": 10.0, "currency": "usd", "interval": "monthly"},
        ).json()["id"]
        plan_b_id = client.post(
            "/api/v1/plans",
            json={"name": "B", "amount": 50.0, "currency": "usd", "interval": "monthly"},
        ).json()["id"]
        return customer_id, plan_a_id, plan_b_id

    def test_cancel_at_period_end_leaves_status_active(self, client, mock_stripe):
        customer_id, plan_id, _ = self._setup(client)
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        ).json()["id"]

        response = client.patch(f"/api/v1/subscriptions/{sub_id}/cancel?at_period_end=true")
        assert response.status_code == 200
        body = response.json()
        # Status stays active; only cancel_at is set. canceled_at is None until
        # the period actually ends (webhook flips it, or immediate cancel does).
        assert body["status"] == "active"
        assert body["cancel_at"] is not None
        assert body["canceled_at"] is None

    def test_immediate_cancel_flips_status_and_sets_canceled_at(self, client, mock_stripe):
        customer_id, plan_id, _ = self._setup(client)
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        ).json()["id"]

        response = client.patch(f"/api/v1/subscriptions/{sub_id}/cancel?at_period_end=false")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "canceled"
        assert body["canceled_at"] is not None

    def test_upgrade_uses_create_prorations(self, client, mock_stripe):
        customer_id, plan_a, plan_b = self._setup(client)
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_a},
        ).json()["id"]

        client.patch(f"/api/v1/subscriptions/{sub_id}/upgrade", json={"new_plan_id": plan_b})

        _, kwargs = mock_stripe.Subscription.modify.call_args
        assert kwargs["proration_behavior"] == "create_prorations"

    def test_downgrade_uses_none_proration(self, client, mock_stripe):
        customer_id, plan_a, plan_b = self._setup(client)
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_b},
        ).json()["id"]

        client.patch(f"/api/v1/subscriptions/{sub_id}/downgrade", json={"new_plan_id": plan_a})

        _, kwargs = mock_stripe.Subscription.modify.call_args
        assert kwargs["proration_behavior"] == "none"

    def test_period_end_from_stripe_response(self, client, mock_stripe, db_session):
        """When Stripe returns a current_period_end timestamp, we honor it
        instead of using the local 30-day fallback."""
        from datetime import datetime

        from app.models.subscription import Subscription

        # Configure the subscription create mock to return a specific period_end
        ts_end = 1893456000  # 2030-01-01 UTC
        ts_start = 1890777600  # 2029-12-01 UTC

        def _create_with_period(**kwargs):
            m = MagicMock()
            m.id = "sub_periodtest"
            m.current_period_start = ts_start
            m.current_period_end = ts_end
            m.__getitem__ = lambda self, key: {"items": {"data": [MagicMock(id="si")]}}[key]
            return m

        mock_stripe.Subscription.create.side_effect = _create_with_period

        customer_id, plan_id, _ = self._setup(client)
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        ).json()["id"]

        row = db_session.query(Subscription).filter_by(id=sub_id).first()
        # SQLite drops tzinfo on DateTime(timezone=True) roundtrip; the
        # stored timestamp is still UTC. Compare the wall-clock value, not
        # the tz-aware/naive flavor.
        expected_end = datetime.fromtimestamp(ts_end, tz=UTC).replace(tzinfo=None)
        expected_start = datetime.fromtimestamp(ts_start, tz=UTC).replace(tzinfo=None)
        actual_end = row.current_period_end.replace(tzinfo=None) if row.current_period_end.tzinfo else row.current_period_end
        actual_start = row.current_period_start.replace(tzinfo=None) if row.current_period_start.tzinfo else row.current_period_start
        assert actual_end == expected_end
        assert actual_start == expected_start
