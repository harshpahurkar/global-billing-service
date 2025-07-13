from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base, TimestampMixin, UUIDMixin, GUID


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"

    customer_id = Column(GUID(), ForeignKey("customers.id"), nullable=False, index=True)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id"), nullable=True, index=True)
    stripe_invoice_id = Column(String(255), unique=True, nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(
        SQLEnum(InvoiceStatus),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )
    currency = Column(String(3), nullable=False, default="usd")
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0)
    amount_due = Column(Numeric(10, 2), nullable=False, default=0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    line_items = Column(Text, nullable=True)  # JSON string
    description = Column(String(500), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", lazy="selectin")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, status={self.status})>"
