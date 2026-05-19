from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    currency = Column(String(3), nullable=False, default="usd")
    country = Column(String(2), nullable=True)
    phone = Column(String(50), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata_ = Column("metadata", String(2000), nullable=True)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="customer", lazy="selectin")
    invoices = relationship("Invoice", back_populates="customer", lazy="selectin")
    payments = relationship("Payment", back_populates="customer", lazy="selectin")

    def __repr__(self):
        return f"<Customer(id={self.id}, email={self.email})>"
