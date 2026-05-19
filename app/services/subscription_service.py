"""Subscription lifecycle management service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CustomerNotFoundError,
    PlanNotFoundError,
    SubscriptionAlreadyCancelledError,
    SubscriptionNotActiveError,
    SubscriptionNotFoundError,
)
from app.models.customer import Customer
from app.models.plan import Plan, PlanInterval
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.stripe_service import StripeService

logger = structlog.get_logger()


# Fallback period length when Stripe is not available to give us authoritative
# boundaries. These are calendar-naive (30/365/7 days) — Stripe's response is
# preferred whenever we have it.
_INTERVAL_FALLBACK_DAYS = {
    PlanInterval.WEEKLY: 7,
    PlanInterval.MONTHLY: 30,
    PlanInterval.YEARLY: 365,
}


def _period_end_fallback(plan: Plan, start: datetime) -> datetime:
    days = _INTERVAL_FALLBACK_DAYS.get(plan.interval, 30) * max(plan.interval_count or 1, 1)
    return start + timedelta(days=days)


def _stripe_ts_to_datetime(ts) -> datetime | None:
    """Convert a Stripe Unix timestamp (or MagicMock in tests) to a UTC datetime."""
    if not isinstance(ts, int | float) or ts <= 0:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


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

        Period boundaries come from the Stripe response when available; if Stripe
        is not in the loop (no stripe IDs) or the response is silent on dates,
        we fall back to plan.interval-based math (7/30/365 days).
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        plan = self.db.query(Plan).filter(Plan.id == plan_id, Plan.is_active.is_(True)).first()
        if not plan:
            raise PlanNotFoundError(str(plan_id))

        now = datetime.now(UTC)
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
            current_period_end=_period_end_fallback(plan, now),
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

            stripe_start = _stripe_ts_to_datetime(getattr(stripe_sub, "current_period_start", None))
            stripe_end = _stripe_ts_to_datetime(getattr(stripe_sub, "current_period_end", None))
            if stripe_start is not None:
                subscription.current_period_start = stripe_start
            if stripe_end is not None:
                subscription.current_period_end = stripe_end

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

    def _change_plan(
        self,
        subscription_id: UUID,
        new_plan_id: UUID,
        proration_behavior: str,
        event: str,
    ) -> Subscription:
        """Shared upgrade/downgrade implementation; differs only in proration."""
        subscription = self.get_subscription(subscription_id)

        if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            raise SubscriptionNotActiveError()

        new_plan = self.db.query(Plan).filter(
            Plan.id == new_plan_id, Plan.is_active.is_(True)
        ).first()
        if not new_plan:
            raise PlanNotFoundError(str(new_plan_id))

        if subscription.stripe_subscription_id and new_plan.stripe_price_id:
            self.stripe.update_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                new_price_id=new_plan.stripe_price_id,
                proration_behavior=proration_behavior,
            )

        old_plan_id = subscription.plan_id
        subscription.plan_id = new_plan_id
        self.db.commit()
        self.db.refresh(subscription)

        logger.info(
            event,
            subscription_id=str(subscription_id),
            old_plan_id=str(old_plan_id),
            new_plan_id=str(new_plan_id),
            proration_behavior=proration_behavior,
        )
        return subscription

    def upgrade_subscription(self, subscription_id: UUID, new_plan_id: UUID) -> Subscription:
        """Upgrade: charge a prorated difference immediately."""
        return self._change_plan(
            subscription_id, new_plan_id,
            proration_behavior="create_prorations",
            event="subscription_upgraded",
        )

    def downgrade_subscription(self, subscription_id: UUID, new_plan_id: UUID) -> Subscription:
        """Downgrade: apply at next renewal, no proration credit.

        Customers keep what they paid for; the cheaper plan kicks in at the
        next billing cycle. Using `create_prorations` here would credit the
        customer mid-cycle, which is almost never what billing teams want.
        """
        return self._change_plan(
            subscription_id, new_plan_id,
            proration_behavior="none",
            event="subscription_downgraded",
        )

    def cancel_subscription(
        self,
        subscription_id: UUID,
        at_period_end: bool = True,
    ) -> Subscription:
        """Cancel a subscription.

        - at_period_end=True: schedule cancellation; subscription stays ACTIVE
          until the period ends. Only `cancel_at` is set; `canceled_at` and the
          terminal status are written when Stripe's customer.subscription.deleted
          webhook arrives, or when this method is called with at_period_end=False.
        - at_period_end=False: cancel immediately; status flips to CANCELED and
          canceled_at is set now.
        """
        subscription = self.get_subscription(subscription_id)

        if subscription.status == SubscriptionStatus.CANCELED:
            raise SubscriptionAlreadyCancelledError()

        if subscription.status not in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
        ):
            raise SubscriptionNotActiveError()

        if subscription.stripe_subscription_id:
            self.stripe.cancel_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                at_period_end=at_period_end,
            )

        if at_period_end:
            subscription.cancel_at = subscription.current_period_end
            # status and canceled_at are deliberately left untouched; the webhook
            # handler (or a direct at_period_end=False cancel) flips them.
        else:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(subscription)

        logger.info(
            "subscription_canceled",
            subscription_id=str(subscription_id),
            at_period_end=at_period_end,
        )
        return subscription

    def reactivate_subscription(self, subscription_id: UUID) -> Subscription:
        """Reactivate a subscription that was scheduled for cancellation."""
        subscription = self.get_subscription(subscription_id)

        if subscription.status == SubscriptionStatus.CANCELED:
            raise SubscriptionAlreadyCancelledError()

        if not subscription.cancel_at:
            raise SubscriptionNotActiveError()

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
        customer_id: UUID | None = None,
        status: SubscriptionStatus | None = None,
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
