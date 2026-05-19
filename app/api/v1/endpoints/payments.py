from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import BillingException, CustomerNotFoundError, PaymentNotFoundError
from app.core.security import require_api_key
from app.db.session import get_db
from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentRefund,
    PaymentResponse,
)
from app.services.stripe_service import StripeService

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
):
    """Create a payment intent for a customer.

    Local payment row is written first as PENDING with no Stripe ID, then
    Stripe is called with `idempotency_key=<local_id>`. Failure leaves the
    local row in PENDING with stripe_payment_intent_id NULL for reconciliation.
    """
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(payload.customer_id))

    payment = Payment(
        customer_id=payload.customer_id,
        invoice_id=payload.invoice_id,
        stripe_payment_intent_id=None,
        amount=payload.amount,
        currency=payload.currency.lower(),
        status=PaymentStatus.PENDING,
        payment_method=payload.payment_method,
        description=payload.description,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if customer.stripe_customer_id:
        amount_cents = int(payload.amount * 100)
        stripe_intent = StripeService.create_payment_intent(
            amount=amount_cents,
            currency=payload.currency,
            customer_id=customer.stripe_customer_id,
            description=payload.description,
            metadata={"local_id": str(payment.id)},
            idempotency_key=str(payment.id),
        )
        payment.stripe_payment_intent_id = stripe_intent.id
        db.commit()
        db.refresh(payment)

    return payment


@router.get("", response_model=PaymentListResponse)
def list_payments(
    customer_id: UUID | None = Query(None),
    status: PaymentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List payments with optional filters."""
    query = db.query(Payment)

    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    if status:
        query = query.filter(Payment.status == status)

    total = query.count()
    payments = (
        query.order_by(Payment.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaymentListResponse(
        payments=payments,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: UUID, db: Session = Depends(get_db)):
    """Get payment details by ID."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise PaymentNotFoundError(str(payment_id))
    return payment


def _to_cents(amount: Decimal) -> int:
    """Convert a Decimal currency amount to integer cents using bankers' input
    but standard rounding so half-cent values round up consistently."""
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: UUID,
    payload: PaymentRefund,
    db: Session = Depends(get_db),
):
    """Refund a payment (full or partial).

    All arithmetic is done in Decimal so multi-step partial refunds don't
    accumulate binary-float rounding error.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise PaymentNotFoundError(str(payment_id))

    # Allow multiple partial refunds: keep refunding while the payment is in
    # SUCCEEDED or PARTIALLY_REFUNDED until refunded_amount catches up to total.
    if payment.status not in (PaymentStatus.SUCCEEDED, PaymentStatus.PARTIALLY_REFUNDED):
        raise BillingException(detail="Can only refund succeeded payments")

    # payment.amount and payment.refunded_amount come back as Decimal from
    # Numeric(10,2). payload.amount is float; round once at the boundary.
    total = payment.amount
    already_refunded = payment.refunded_amount or Decimal("0")
    requested = Decimal(str(payload.amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) \
        if payload.amount is not None else total
    remaining = total - already_refunded

    if requested > remaining:
        raise BillingException(
            detail=f"Refund amount ({requested}) exceeds remaining ({remaining})"
        )

    if payment.stripe_payment_intent_id:
        StripeService.create_refund(
            payment_intent_id=payment.stripe_payment_intent_id,
            amount=_to_cents(requested),
            reason=payload.reason,
            idempotency_key=f"refund:{payment.id}:{already_refunded}",
        )

    payment.refunded_amount = already_refunded + requested
    if payment.refunded_amount >= total:
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED

    db.commit()
    db.refresh(payment)
    return payment
