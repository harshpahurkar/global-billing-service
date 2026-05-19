"""Invoice management service."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID
import secrets
import string
import structlog

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BillingException, InvoiceNotFoundError, CustomerNotFoundError
from app.models.invoice import Invoice, InvoiceStatus
from app.models.customer import Customer
from app.services.stripe_service import StripeService

logger = structlog.get_logger()

_INVOICE_NUMBER_ALPHABET = string.ascii_uppercase + string.digits


def _generate_invoice_number() -> str:
    """Generate a unique invoice number using a cryptographic RNG.

    `random.choices` is not collision-safe under high concurrency; `secrets`
    uses the OS CSPRNG. The 6-char suffix gives ~2.2B values per day so the
    `invoice_number UNIQUE` constraint is the safety net, not the assumption.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = "".join(secrets.choice(_INVOICE_NUMBER_ALPHABET) for _ in range(6))
    return f"INV-{timestamp}-{random_suffix}"


def _money(value) -> Decimal:
    """Coerce float/int/Decimal to a Decimal with cent precision."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
        """Create a new invoice.

        Local row is written first; Stripe is called second with an idempotency
        key derived from the local UUID. A failed Stripe call leaves the local
        invoice with stripe_invoice_id NULL for reconciliation.
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        # Decimal-throughout arithmetic. Subtotal/tax arrive as floats from the
        # Pydantic schema; quantize to cents at the boundary and never go back
        # to float so partial totals don't accumulate binary rounding error.
        subtotal_d = _money(subtotal)
        tax_d = _money(tax)
        total_d = subtotal_d + tax_d

        if due_date is None:
            due_date = datetime.now(timezone.utc) + timedelta(days=30)

        # Retry once on invoice_number collision; with 6 random chars + daily
        # prefix collisions are vanishingly rare but the UNIQUE constraint is
        # the safety net.
        for attempt in range(2):
            invoice = Invoice(
                customer_id=customer_id,
                subscription_id=subscription_id,
                stripe_invoice_id=None,
                invoice_number=_generate_invoice_number(),
                status=InvoiceStatus.OPEN,
                currency=currency,
                subtotal=subtotal_d,
                tax=tax_d,
                total=total_d,
                amount_paid=Decimal("0"),
                amount_due=total_d,
                due_date=due_date,
                line_items=line_items,
                description=description,
            )
            self.db.add(invoice)
            try:
                self.db.commit()
                self.db.refresh(invoice)
                break
            except IntegrityError:
                self.db.rollback()
                if attempt == 1:
                    raise BillingException(detail="Failed to generate unique invoice number; try again")

        if customer.stripe_customer_id:
            stripe_invoice = self.stripe.create_invoice(
                customer_id=customer.stripe_customer_id,
                description=description,
                currency=currency,
                metadata={"local_id": str(invoice.id)},
                idempotency_key=str(invoice.id),
            )
            invoice.stripe_invoice_id = stripe_invoice.id
            self.db.commit()
            self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            total=str(total_d),
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
            raise BillingException(
                detail=f"Invoice cannot be paid (current status: {invoice.status.value})"
            )

        # Pay in Stripe if applicable
        if invoice.stripe_invoice_id:
            self.stripe.pay_invoice(invoice.stripe_invoice_id)

        now = datetime.now(timezone.utc)
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice.total
        invoice.amount_due = Decimal("0")
        invoice.paid_at = now

        self.db.commit()
        self.db.refresh(invoice)

        logger.info("invoice_paid", invoice_id=str(invoice_id))
        return invoice

    def void_invoice(self, invoice_id: UUID) -> Invoice:
        """Void an invoice."""
        invoice = self.get_invoice(invoice_id)

        if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.OPEN):
            raise BillingException(
                detail=f"Invoice cannot be voided (current status: {invoice.status.value})"
            )

        if invoice.stripe_invoice_id:
            self.stripe.void_invoice(invoice.stripe_invoice_id)

        invoice.status = InvoiceStatus.VOID
        invoice.amount_due = Decimal("0")

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
