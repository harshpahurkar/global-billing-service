from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    customer_id: UUID
    subscription_id: Optional[UUID] = None
    currency: str = Field(default="usd", min_length=3, max_length=3)
    subtotal: float = Field(..., ge=0)
    tax: float = Field(default=0, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    line_items: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    id: UUID
    customer_id: UUID
    subscription_id: Optional[UUID] = None
    stripe_invoice_id: Optional[str] = None
    invoice_number: str
    status: InvoiceStatus
    currency: str
    subtotal: float
    tax: float
    total: float
    amount_paid: float
    amount_due: float
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    line_items: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceResponse]
    total: int
    page: int
    per_page: int
