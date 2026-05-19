from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    customer_id: UUID
    invoice_id: UUID | None = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    payment_method: PaymentMethod = PaymentMethod.CARD
    description: str | None = Field(None, max_length=500)


class PaymentRefund(BaseModel):
    amount: float | None = Field(None, gt=0)  # None = full refund
    reason: str | None = Field(None, max_length=500)


class PaymentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    invoice_id: UUID | None = None
    stripe_payment_intent_id: str | None = None
    stripe_charge_id: str | None = None
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod | None = None
    refunded_amount: float
    failure_reason: str | None = None
    paid_at: datetime | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int
    page: int
    per_page: int
