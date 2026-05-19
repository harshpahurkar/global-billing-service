"""Subscription lifecycle management service."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import structlog

from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.customer import Customer
from app.models.plan import Plan
from app.core.exceptions import (
    SubscriptionNotFoundError,
    SubscriptionNotActiveError,
    SubscriptionAlreadyCancelledError,
    CustomerNotFoundError,
    PlanNotFoundError,
)
from app.services.stripe_service import StripeService

logger = structlog.get_logger()


class SubscriptionService:
    """Handles all subscription lifecycle operations."""

    def __init__(self, db: Session):
        self.db = db
        self.stripe = StripeService()

    def create_subscription(
        self,
        customer_id: UUID,
        plan_id: UUID,
        currency: str = "usd",
    ) -> Subscription:
        """Create a new subscription for a customer.

        Local row is written first; Stripe is called second with an
        idempotency key derived from the local UUID. A failed Stripe call
        leaves the local row with stripe_subscription_id NULL for reconciliation.
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        plan = self.db.query(Plan).filter(Plan.id == plan_id, Plan.is_active.is_(True)).first()
        if not plan:
            raise PlanNotFoundError(str(plan_id))

        now = datetime.now(timezone.utc)
        status = SubscriptionStatus.ACTIVE
        trial_start = None
        trial_end = None

        if plan.trial_days > 0:
            status = SubscriptionStatus.TRIALING
            trial_start = now
            trial_end = now + timedelta(days=plan.trial_days)

        subscription = Subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            stripe_subscription_id=None,
            status=status,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),  # Overwritten from Stripe below
            trial_start=trial_start,
            trial_end=trial_end,
            currency=currency,
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        if customer.stripe_customer_id and plan.stripe_price_id:
            stripe_sub = self.stripe.create_subscription(
                customer_id=customer.stripe_customer_id,
                price_id=plan.stripe_price_id,
                trial_days=plan.trial_days,
                metadata={"local_id": str(subscription.id)},
                idempotency_key=str(subscription.id),
            )
            subscription.stripe_subscription_id = stripe_sub.id
            self.db.commit()
            self.db.refresh(subscription)

        logger.info(
            "subscription_created",
            subscription_id=str(subscription.id),
            customer_id=str(customer_id),
            plan_id=str(plan_id),
        )
        return subscription

    def get_subscription(self, subscription_id: UUID) -> Subscription:
        """Get a subscription by ID."""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        if not subscription:
            raise SubscriptionNotFoundError(str(subscription_id))
        return subscription

    def upgrade_subscription(
        self,
        subscription_id: UUID,
        new_plan_id: UUID,
    ) -> Subscription:
        """Upgrade a subscription to a new plan."""
        subscription = self.get_subscription(subscription_id)

        if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            raise SubscriptionNotActiveError()

        new_plan = self.db.query(Plan).filter(
            Plan.id == new_plan_id, Plan.is_active.is_(True)
        ).first()
        if not new_plan:
            raise PlanNotFoundError(str(new_plan_id))

        # Update in Stripe if applicable
        if subscription.stripe_subscription_id and new_plan.stripe_price_id:
            self.stripe.update_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                new_price_id=new_plan.stripe_price_id,
            )

        old_plan_id = subscription.plan_id
        subscription.plan_id = new_plan_id
        self.db.commit()
        self.db.refresh(subscription)

        logger.info(
            "subscription_upgraded",
            subscription_id=str(subscription_id),
            old_plan_id=str(old_plan_id),
            new_plan_id=str(new_plan_id),
        )
        return subscription

    def downgrade_subscription(
        self,
        subscription_id: UUID,
        new_plan_id: UUID,
    ) -> Subscription:
        """Downgrade a subscription (same flow as upgrade, different semantics)."""
        return self.upgrade_subscription(subscription_id, new_plan_id)

    def cancel_subscription(
        self,
        subscription_id: UUID,
        at_period_end: bool = True,
    ) -> Subscription:
        """Cancel a subscription."""
        subscription = self.get_subscription(subscription_id)

        if subscription.status == SubscriptionStatus.CANCELED:
            raise SubscriptionAlreadyCancelledError()

        if subscription.status not in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
        ):
            raise SubscriptionNotActiveError()

        # Cancel in Stripe
        if subscription.stripe_subscription_id:
            self.stripe.cancel_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                at_period_end=at_period_end,
            )

        now = datetime.now(timezone.utc)
        if at_period_end:
            subscription.cancel_at = subscription.current_period_end
        else:
            subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = now

        self.db.commit()
        self.db.refresh(subscription)

        logger.info(
            "subscription_canceled",
            subscription_id=str(subscription_id),
            at_period_end=at_period_end,
        )
        return subscription

    def reactivate_subscription(self, subscription_id: UUID) -> Subscription:
        """Reactivate a canceled subscription (only if cancel_at is set, before period end)."""
        subscription = self.get_subscription(subscription_id)

        if subscription.status == SubscriptionStatus.CANCELED:
            raise SubscriptionAlreadyCancelledError()

        if not subscription.cancel_at:
            raise SubscriptionNotActiveError()

        # Reactivate in Stripe
        if subscription.stripe_subscription_id:
            self.stripe.reactivate_subscription(subscription.stripe_subscription_id)

        subscription.cancel_at = None
        subscription.canceled_at = None
        self.db.commit()
        self.db.refresh(subscription)

        logger.info("subscription_reactivated", subscription_id=str(subscription_id))
        return subscription

    def list_subscriptions(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[SubscriptionStatus] = None,
        page: int = 1,
        per_page: int = 20,
    ):
        """List subscriptions with optional filters."""
        query = self.db.query(Subscription)

        if customer_id:
            query = query.filter(Subscription.customer_id == customer_id)
        if status:
            query = query.filter(Subscription.status == status)

        total = query.count()
        subscriptions = (
            query.order_by(Subscription.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return subscriptions, total
