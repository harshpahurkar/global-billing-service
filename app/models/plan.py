import enum

from sqlalchemy import Boolean, Column, Integer, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PlanInterval(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    WEEKLY = "weekly"
    ONE_TIME = "one_time"


class Plan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plans"

    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    stripe_product_id = Column(String(255), unique=True, nullable=True)
    stripe_price_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="usd")
    interval = Column(SQLEnum(PlanInterval), nullable=False, default=PlanInterval.MONTHLY)
    interval_count = Column(Integer, nullable=False, default=1)
    trial_days = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    features = Column(String(2000), nullable=True)  # JSON string of features
    sort_order = Column(Integer, nullable=False, default=0)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan", lazy="selectin")

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, amount={self.amount} {self.currency})>"
