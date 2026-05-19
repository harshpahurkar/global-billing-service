import enum

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELED = "canceled"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    customer_id = Column(GUID(), ForeignKey("customers.id"), nullable=False, index=True)
    invoice_id = Column(GUID(), ForeignKey("invoices.id"), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    stripe_charge_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(
        SQLEnum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    payment_method = Column(
        SQLEnum(PaymentMethod),
        nullable=True,
        default=PaymentMethod.CARD,
    )
    refunded_amount = Column(Numeric(10, 2), nullable=False, default=0)
    failure_reason = Column(String(500), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(500), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount} {self.currency}, status={self.status})>"
