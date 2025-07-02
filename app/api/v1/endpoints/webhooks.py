from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import structlog

from app.db.session import get_db
from app.services.stripe_service import StripeService
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    stripe_service = StripeService()
    event = stripe_service.construct_webhook_event(payload, sig_header)

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("webhook_received", event_type=event_type, event_id=event["id"])

    # Handle subscription events
    if event_type == "customer.subscription.created":
        _handle_subscription_created(db, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)

    # Handle invoice events
    elif event_type == "invoice.paid":
        _handle_invoice_paid(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_payment_failed(db, data)

    # Handle payment intent events
    elif event_type == "payment_intent.succeeded":
        _handle_payment_succeeded(db, data)
    elif event_type == "payment_intent.payment_failed":
        _handle_payment_failed(db, data)

    else:
        logger.info("webhook_unhandled", event_type=event_type)

    return {"status": "ok"}


def _handle_subscription_created(db: Session, data: dict):
    """Handle subscription.created webhook."""
    stripe_sub_id = data.get("id")
    logger.info("webhook_subscription_created", stripe_subscription_id=stripe_sub_id)


def _handle_subscription_updated(db: Session, data: dict):
    """Handle subscription.updated webhook."""
    stripe_sub_id = data.get("id")
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "trialing": SubscriptionStatus.TRIALING,
        "paused": SubscriptionStatus.PAUSED,
        "unpaid": SubscriptionStatus.UNPAID,
    }

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if subscription:
        stripe_status = data.get("status")
        if stripe_status in status_map:
            subscription.status = status_map[stripe_status]
            db.commit()
            logger.info(
                "webhook_subscription_status_updated",
                subscription_id=str(subscription.id),
                new_status=stripe_status,
            )


def _handle_subscription_deleted(db: Session, data: dict):
    """Handle subscription.deleted webhook."""
    stripe_sub_id = data.get("id")
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if subscription:
        subscription.status = SubscriptionStatus.CANCELED
        db.commit()
        logger.info("webhook_subscription_deleted", subscription_id=str(subscription.id))


def _handle_invoice_paid(db: Session, data: dict):
    """Handle invoice.paid webhook."""
    stripe_invoice_id = data.get("id")
    invoice = db.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice_id
    ).first()

    if invoice:
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice.total
        invoice.amount_due = 0
        db.commit()
        logger.info("webhook_invoice_paid", invoice_id=str(invoice.id))


def _handle_invoice_payment_failed(db: Session, data: dict):
    """Handle invoice.payment_failed webhook."""
    stripe_invoice_id = data.get("id")
    invoice = db.query(Invoice).filter(
        Invoice.stripe_invoice_id == stripe_invoice_id
    ).first()

    if invoice:
        invoice.status = InvoiceStatus.OPEN
        db.commit()
        logger.info("webhook_invoice_payment_failed", invoice_id=str(invoice.id))


def _handle_payment_succeeded(db: Session, data: dict):
    """Handle payment_intent.succeeded webhook."""
    stripe_pi_id = data.get("id")
    payment = db.query(Payment).filter(
        Payment.stripe_payment_intent_id == stripe_pi_id
    ).first()

    if payment:
        payment.status = PaymentStatus.SUCCEEDED
        db.commit()
        logger.info("webhook_payment_succeeded", payment_id=str(payment.id))


def _handle_payment_failed(db: Session, data: dict):
    """Handle payment_intent.payment_failed webhook."""
    stripe_pi_id = data.get("id")
    payment = db.query(Payment).filter(
        Payment.stripe_payment_intent_id == stripe_pi_id
    ).first()

    if payment:
        payment.status = PaymentStatus.FAILED
        failure_msg = data.get("last_payment_error", {})
        if isinstance(failure_msg, dict):
            failure_msg = failure_msg.get("message", "Payment failed")
        payment.failure_reason = str(failure_msg)[:500]
        db.commit()
        logger.info("webhook_payment_failed", payment_id=str(payment.id))
