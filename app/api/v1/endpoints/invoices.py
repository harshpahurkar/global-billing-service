from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.core.security import require_api_key
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceListResponse
from app.models.invoice import InvoiceStatus
from app.services.invoice_service import InvoiceService

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
):
    """Create a new invoice for a customer."""
    service = InvoiceService(db)
    invoice = service.create_invoice(
        customer_id=payload.customer_id,
        subtotal=payload.subtotal,
        currency=payload.currency,
        tax=payload.tax,
        subscription_id=payload.subscription_id,
        description=payload.description,
        line_items=payload.line_items,
        due_date=payload.due_date,
    )
    return invoice


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List invoices with optional filters."""
    service = InvoiceService(db)
    invoices, total = service.list_invoices(
        customer_id=customer_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return InvoiceListResponse(
        invoices=invoices,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
):
    """Get invoice details by ID."""
    service = InvoiceService(db)
    return service.get_invoice(invoice_id)


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
def pay_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
):
    """Pay an open invoice."""
    service = InvoiceService(db)
    return service.pay_invoice(invoice_id)


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
def void_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
):
    """Void a draft or open invoice."""
    service = InvoiceService(db)
    return service.void_invoice(invoice_id)
