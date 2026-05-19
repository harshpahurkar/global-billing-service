from sqlalchemy import Column, DateTime, String, func

from app.db.base import Base


class ProcessedStripeEvent(Base):
    """Idempotency record for Stripe webhook events.

    The stripe `event.id` is the primary key; the row's existence is the
    "already processed" flag. Stripe may deliver the same event more than once
    or out of order, so the handler upserts here before mutating any other
    state and skips if the row already exists.
    """

    __tablename__ = "processed_stripe_events"

    stripe_event_id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ProcessedStripeEvent(id={self.stripe_event_id}, type={self.event_type})>"
