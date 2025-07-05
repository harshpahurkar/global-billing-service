from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.payment import PaymentStatus, PaymentMethod


class PaymentCreate(BaseModel):
    customer_id: UUID
    invoice_id: Optional[UUID] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    payment_method: PaymentMethod = PaymentMethod.CARD
    description: Optional[str] = Field(None, max_length=500)


class PaymentRefund(BaseModel):
    amount: Optional[float] = Field(None, gt=0)  # None = full refund
    reason: Optional[str] = Field(None, max_length=500)


class PaymentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    invoice_id: Optional[UUID] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    refunded_amount: float
    failure_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
