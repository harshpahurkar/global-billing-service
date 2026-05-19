import enum

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import GUID, Base, TimestampMixin, UUIDMixin


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    PAUSED = "paused"
    UNPAID = "unpaid"


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    customer_id = Column(GUID(), ForeignKey("customers.id"), nullable=False, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=False, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    status = Column(
        SQLEnum(SubscriptionStatus),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    currency = Column(String(3), nullable=False, default="usd")

    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", lazy="selectin")

    def __repr__(self):
        return f"<Subscription(id={self.id}, status={self.status})>"
