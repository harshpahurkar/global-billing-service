from fastapi import APIRouter, Request, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import structlog

from app.db.session import get_db
from app.services.stripe_service import StripeService
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.stripe_event import ProcessedStripeEvent

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# Status maps live at module scope so they're easy to extend.
_SUB_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "incomplete": SubscriptionStatus.INCOMPLETE,
    "trialing": SubscriptionStatus.TRIALING,
    "paused": SubscriptionStatus.PAUSED,
    "unpaid": SubscriptionStatus.UNPAID,
}


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Stripe webhook events.

    Authentication is the Stripe HMAC signature, not the X-API-Key header.
    Idempotency is enforced via the processed_stripe_events table — Stripe
    can deliver the same event id more than once or out of order, so the
    handler records the id (and short-circuits on duplicates) before mutating
    any other state.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = StripeService.construct_webhook_event(payload, sig_header)
    event_id = event["id"]
    event_type = event["type"]
    data = event["data"]["object"]

    # Idempotency gate. Insert first; if the unique PK conflicts, this event
    # has already been processed and we return 200 OK without re-applying.
    db.add(ProcessedStripeEvent(stripe_event_id=event_id, event_type=event_type))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("webhook_duplicate_ignored", event_type=event_type, event_id=event_id)
        return {"status": "ok", "duplicate": True}

    logger.info("webhook_received", event_type=event_type, event_id=event_id)

    if event_type == "customer.subscription.created":
        _handle_subscription_created(db, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_payment_failed(db, data)
    elif event_type == "payment_intent.succeeded":
        _handle_payment_succeeded(db, data)
    elif event_type == "payment_intent.payment_failed":
        _handle_payment_failed(db, data)
    else:
        logger.info("webhook_unhandled", event_type=event_type)

    return {"status": "ok"}


def _handle_subscription_created(db: Session, data: dict):
    logger.info("webhook_subscription_created", stripe_subscription_id=data.get("id"))


def _handle_subscription_updated(db: Session, data: dict):
    stripe_sub_id = data.get("id")
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()
    if not subscription:
        return

    stripe_status = data.get("status")
    new_status = _SUB_STATUS_MAP.get(stripe_status)
    if new_status is None:
        return

    # Guard: once CANCELED is set, only an explicit reactivate (different event
    # entirely) should leave that terminal state. A late 'active' event for a
    # canceled subscription is treated as out-of-order and ignored.
    if subscription.status == SubscriptionStatus.CANCELED and new_status != SubscriptionStatus.CANCELED:
        logger.info(
            "webhook_subscription_status_ignored_terminal",
            subscription_id=str(subscription.id),
            attempted_status=stripe_status,
        )
        return

    subscription.status = new_status
    db.commit()
    logger.info(
        "webhook_subscription_status_updated",
        subscription_id=str(subscription.id),
        new_status=stripe_status,
    )


def _handle_subscription_deleted(db: Session, data: dict):
    from datetime import datetime, timezone

    stripe_sub_id = data.get("id")
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()
    if subscription:
        subscription.status = SubscriptionStatus.CANCELED
        if subscription.canceled_at is None:
            subscription.canceled_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("webhook_subscription_deleted", subscription_id=str(subscription.id))


def _handle_invoice_paid(db: Session, data: dict):
    stripe_invoice_id = data.get("id")
    invoice = db.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice_id
    ).first()
    if invoice and invoice.status != InvoiceStatus.PAID:
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice.total
        invoice.amount_due = 0
        db.commit()
        logger.info("webhook_invoice_paid", invoice_id=str(invoice.id))


def _handle_invoice_payment_failed(db: Session, data: dict):
    """A payment_failed event must never overwrite a terminal PAID state.

    Stripe can deliver events out of order; a stale 'payment_failed' arriving
    after a real 'paid' would otherwise flip the invoice back to OPEN and the
    customer would look like they owe money they've already paid.
    """
    stripe_invoice_id = data.get("id")
    invoice = db.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice_id
    ).first()
    if not invoice:
        return
    if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.VOID, InvoiceStatus.UNCOLLECTIBLE):
        logger.info(
            "webhook_invoice_payment_failed_ignored_terminal",
            invoice_id=str(invoice.id),
            current_status=invoice.status.value,
        )
        return
    invoice.status = InvoiceStatus.OPEN
    db.commit()
    logger.info("webhook_invoice_payment_failed", invoice_id=str(invoice.id))


def _handle_payment_succeeded(db: Session, data: dict):
    stripe_pi_id = data.get("id")
    payment = db.query(Payment).filter(
        Payment.stripe_payment_intent_id == stripe_pi_id
    ).first()
    if payment and payment.status != PaymentStatus.SUCCEEDED:
        payment.status = PaymentStatus.SUCCEEDED
        db.commit()
        logger.info("webhook_payment_succeeded", payment_id=str(payment.id))


def _handle_payment_failed(db: Session, data: dict):
    stripe_pi_id = data.get("id")
    payment = db.query(Payment).filter(
        Payment.stripe_payment_intent_id == stripe_pi_id
    ).first()
    if not payment:
        return
    # Same guard as invoice: don't overwrite a SUCCEEDED state with a stale
    # late-arriving 'failed' event.
    if payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED):
        return
    payment.status = PaymentStatus.FAILED
    failure_msg = data.get("last_payment_error", {})
    if isinstance(failure_msg, dict):
        failure_msg = failure_msg.get("message", "Payment failed")
    payment.failure_reason = str(failure_msg)[:500]
    db.commit()
    logger.info("webhook_payment_failed", payment_id=str(payment.id))
