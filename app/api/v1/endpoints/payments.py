from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.models.payment import Payment, PaymentStatus
from app.models.customer import Customer
from app.schemas.payment import (
    PaymentCreate,
    PaymentRefund,
    PaymentResponse,
    PaymentListResponse,
)
from app.core.exceptions import PaymentNotFoundError, CustomerNotFoundError, BillingException
from app.services.stripe_service import StripeService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
):
    """Create a payment (charge) for a customer."""
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(payload.customer_id))

    # Create payment intent in Stripe
    stripe_service = StripeService()
    amount_cents = int(payload.amount * 100)
    stripe_intent = None

    if customer.stripe_customer_id:
        stripe_intent = stripe_service.create_payment_intent(
            amount=amount_cents,
            currency=payload.currency,
            customer_id=customer.stripe_customer_id,
            description=payload.description,
        )

    payment = Payment(
        customer_id=payload.customer_id,
        invoice_id=payload.invoice_id,
        stripe_payment_intent_id=stripe_intent.id if stripe_intent else None,
        amount=payload.amount,
        currency=payload.currency.lower(),
        status=PaymentStatus.PENDING,
        payment_method=payload.payment_method,
        description=payload.description,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=PaymentListResponse)
def list_payments(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
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


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: UUID,
    payload: PaymentRefund,
    db: Session = Depends(get_db),
):
    """Refund a payment (full or partial)."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise PaymentNotFoundError(str(payment_id))

    if payment.status != PaymentStatus.SUCCEEDED:
        raise BillingException(detail="Can only refund succeeded payments")

    refund_amount = payload.amount or float(payment.amount)
    remaining = float(payment.amount) - float(payment.refunded_amount)

    if refund_amount > remaining:
        raise BillingException(detail=f"Refund amount ({refund_amount}) exceeds remaining ({remaining})")

    # Refund in Stripe
    if payment.stripe_payment_intent_id:
        stripe_service = StripeService()
        amount_cents = int(refund_amount * 100)
        stripe_service.create_refund(
            payment_intent_id=payment.stripe_payment_intent_id,
            amount=amount_cents,
            reason=payload.reason,
        )

    payment.refunded_amount = float(payment.refunded_amount) + refund_amount
    if payment.refunded_amount >= float(payment.amount):
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED

    db.commit()
    db.refresh(payment)
    return payment
