"""Tests for the Stripe webhook endpoint.

Stripe HMAC signature verification is exercised via mock_stripe by stubbing
StripeService.construct_webhook_event to return a fixed event dict. The
endpoint logic — dedupe via processed_stripe_events, state-transition guards,
and per-event-type handlers — is then tested directly.
"""

from unittest.mock import patch
from uuid import uuid4


def _post_event(client, event):
    """Helper: call the webhook endpoint with construct_webhook_event stubbed."""
    with patch(
        "app.api.v1.endpoints.webhooks.StripeService.construct_webhook_event",
        return_value=event,
    ):
        return client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=0,v1=fake"},
        )


def _event(event_type, data, event_id=None):
    return {
        "id": event_id or f"evt_{uuid4().hex}",
        "type": event_type,
        "data": {"object": data},
    }


class TestWebhookDedupe:
    """Each event ID is processed at most once."""

    def test_duplicate_event_is_skipped(self, unauthenticated_client, db_session):
        from app.models.stripe_event import ProcessedStripeEvent

        event = _event("customer.subscription.created", {"id": "sub_xxx"}, event_id="evt_dedupe_1")

        r1 = _post_event(unauthenticated_client, event)
        assert r1.status_code == 200
        assert r1.json() == {"status": "ok"}

        r2 = _post_event(unauthenticated_client, event)
        assert r2.status_code == 200
        assert r2.json() == {"status": "ok", "duplicate": True}

        rows = db_session.query(ProcessedStripeEvent).filter_by(stripe_event_id="evt_dedupe_1").all()
        assert len(rows) == 1


class TestInvoicePaymentFailedGuard:
    """A late payment_failed must not overwrite a PAID invoice."""

    def test_paid_invoice_is_not_reopened(self, client, mock_stripe, db_session):
        from app.models.invoice import Invoice, InvoiceStatus

        # Create a customer + invoice via the API so the local row exists.
        customer_id = client.post(
            "/api/v1/customers",
            json={"email": f"gw_{uuid4().hex[:8]}@example.com", "name": "G"},
        ).json()["id"]
        invoice_id = client.post(
            "/api/v1/invoices",
            json={"customer_id": customer_id, "subtotal": 10.0, "currency": "usd"},
        ).json()["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/pay")

        invoice = db_session.query(Invoice).filter_by(id=invoice_id).first()
        assert invoice.status == InvoiceStatus.PAID
        stripe_invoice_id = invoice.stripe_invoice_id

        # Now deliver a stale payment_failed event for that same Stripe invoice.
        _post_event(
            client,
            _event("invoice.payment_failed", {"id": stripe_invoice_id}),
        )

        db_session.expire_all()
        invoice = db_session.query(Invoice).filter_by(id=invoice_id).first()
        assert invoice.status == InvoiceStatus.PAID, (
            "PAID invoice must not be reopened by a stale payment_failed event"
        )


class TestSubscriptionStatusGuard:
    """Once a subscription is CANCELED locally, an out-of-order 'active'
    update from Stripe must not silently revive it."""

    def test_canceled_subscription_is_not_revived(self, client, mock_stripe, db_session):
        from app.models.subscription import Subscription, SubscriptionStatus

        # Create customer + plan + subscription, then cancel immediately.
        customer_id = client.post(
            "/api/v1/customers",
            json={"email": f"sg_{uuid4().hex[:8]}@example.com", "name": "S"},
        ).json()["id"]
        plan_id = client.post(
            "/api/v1/plans",
            json={"name": "P", "amount": 10.0, "currency": "usd", "interval": "monthly"},
        ).json()["id"]
        sub_id = client.post(
            "/api/v1/subscriptions",
            json={"customer_id": customer_id, "plan_id": plan_id},
        ).json()["id"]
        client.patch(f"/api/v1/subscriptions/{sub_id}/cancel?at_period_end=false")

        sub = db_session.query(Subscription).filter_by(id=sub_id).first()
        assert sub.status == SubscriptionStatus.CANCELED
        stripe_sub_id = sub.stripe_subscription_id

        _post_event(
            client,
            _event("customer.subscription.updated", {"id": stripe_sub_id, "status": "active"}),
        )

        db_session.expire_all()
        sub = db_session.query(Subscription).filter_by(id=sub_id).first()
        assert sub.status == SubscriptionStatus.CANCELED


class TestWebhookHappyPath:
    """Spot-check that the dedupe gate doesn't break normal processing."""

    def test_invoice_paid_event_marks_local_invoice_paid(self, client, mock_stripe, db_session):
        from app.models.invoice import Invoice, InvoiceStatus

        customer_id = client.post(
            "/api/v1/customers",
            json={"email": f"hp_{uuid4().hex[:8]}@example.com", "name": "H"},
        ).json()["id"]
        invoice_id = client.post(
            "/api/v1/invoices",
            json={"customer_id": customer_id, "subtotal": 25.0, "currency": "usd"},
        ).json()["id"]
        stripe_invoice_id = db_session.query(Invoice).filter_by(id=invoice_id).first().stripe_invoice_id

        _post_event(client, _event("invoice.paid", {"id": stripe_invoice_id}))

        db_session.expire_all()
        invoice = db_session.query(Invoice).filter_by(id=invoice_id).first()
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.amount_due == 0
