"""Invoice management service."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import structlog
import random
import string

from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.customer import Customer
from app.core.exceptions import InvoiceNotFoundError, CustomerNotFoundError
from app.services.stripe_service import StripeService

logger = structlog.get_logger()


def _generate_invoice_number() -> str:
    """Generate a unique invoice number."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"INV-{timestamp}-{random_suffix}"


class InvoiceService:
    """Handles invoice creation, payment, and management."""

    def __init__(self, db: Session):
        self.db = db
        self.stripe = StripeService()

    def create_invoice(
        self,
        customer_id: UUID,
        subtotal: float,
        currency: str = "usd",
        tax: float = 0,
        subscription_id: Optional[UUID] = None,
        description: Optional[str] = None,
        line_items: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> Invoice:
        """Create a new invoice."""
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        total = subtotal + tax
        if due_date is None:
            due_date = datetime.now(timezone.utc) + timedelta(days=30)

        # Create in Stripe if customer has Stripe ID
        stripe_invoice_id = None
        if customer.stripe_customer_id:
            stripe_invoice = self.stripe.create_invoice(
                customer_id=customer.stripe_customer_id,
                description=description,
                currency=currency,
            )
            stripe_invoice_id = stripe_invoice.id

        invoice = Invoice(
            customer_id=customer_id,
            subscription_id=subscription_id,
            stripe_invoice_id=stripe_invoice_id,
            invoice_number=_generate_invoice_number(),
            status=InvoiceStatus.OPEN,
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            total=total,
            amount_paid=0,
            amount_due=total,
            due_date=due_date,
            line_items=line_items,
            description=description,
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            total=total,
        )
        return invoice

    def get_invoice(self, invoice_id: UUID) -> Invoice:
        """Get an invoice by ID."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise InvoiceNotFoundError(str(invoice_id))
        return invoice

    def pay_invoice(self, invoice_id: UUID) -> Invoice:
        """Mark an invoice as paid."""
        invoice = self.get_invoice(invoice_id)

        if invoice.status != InvoiceStatus.OPEN:
            from app.core.exceptions import BillingException
            raise BillingException(
                detail=f"Invoice cannot be paid (current status: {invoice.status.value})"
            )

        # Pay in Stripe if applicable
        if invoice.stripe_invoice_id:
            self.stripe.pay_invoice(invoice.stripe_invoice_id)

        now = datetime.now(timezone.utc)
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice.total
        invoice.amount_due = 0
        invoice.paid_at = now

        self.db.commit()
        self.db.refresh(invoice)

        logger.info("invoice_paid", invoice_id=str(invoice_id))
        return invoice

    def void_invoice(self, invoice_id: UUID) -> Invoice:
        """Void an invoice."""
        invoice = self.get_invoice(invoice_id)

        if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.OPEN):
            from app.core.exceptions import BillingException
            raise BillingException(
                detail=f"Invoice cannot be voided (current status: {invoice.status.value})"
            )

        if invoice.stripe_invoice_id:
            self.stripe.void_invoice(invoice.stripe_invoice_id)

        invoice.status = InvoiceStatus.VOID
        invoice.amount_due = 0

        self.db.commit()
        self.db.refresh(invoice)

        logger.info("invoice_voided", invoice_id=str(invoice_id))
        return invoice

    def list_invoices(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
        page: int = 1,
        per_page: int = 20,
    ):
        """List invoices with optional filters."""
        query = self.db.query(Invoice)

        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)
        if status:
            query = query.filter(Invoice.status == status)

        total = query.count()
        invoices = (
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return invoices, total
