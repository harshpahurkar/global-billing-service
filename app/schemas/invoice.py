from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    customer_id: UUID
    subscription_id: UUID | None = None
    currency: str = Field(default="usd", min_length=3, max_length=3)
    subtotal: float = Field(..., ge=0)
    tax: float = Field(default=0, ge=0)
    description: str | None = Field(None, max_length=500)
    line_items: str | None = None
    due_date: datetime | None = None


class InvoiceResponse(BaseModel):
    id: UUID
    customer_id: UUID
    subscription_id: UUID | None = None
    stripe_invoice_id: str | None = None
    invoice_number: str
    status: InvoiceStatus
    currency: str
    subtotal: float
    tax: float
    total: float
    amount_paid: float
    amount_due: float
    due_date: datetime | None = None
    paid_at: datetime | None = None
    line_items: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]
    total: int
    page: int
    per_page: int
