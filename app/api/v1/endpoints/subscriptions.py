from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpgrade,
    SubscriptionResponse,
    SubscriptionListResponse,
)
from app.models.subscription import SubscriptionStatus
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
):
    """Create a new subscription for a customer."""
    service = SubscriptionService(db)
    subscription = service.create_subscription(
        customer_id=payload.customer_id,
        plan_id=payload.plan_id,
        currency=payload.currency,
    )
    return subscription


@router.get("", response_model=SubscriptionListResponse)
def list_subscriptions(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[SubscriptionStatus] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List subscriptions with optional filters."""
    service = SubscriptionService(db)
    subscriptions, total = service.list_subscriptions(
        customer_id=customer_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return SubscriptionListResponse(
        subscriptions=subscriptions,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
):
    """Get subscription details by ID."""
    service = SubscriptionService(db)
    return service.get_subscription(subscription_id)


@router.patch("/{subscription_id}/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpgrade,
    db: Session = Depends(get_db),
):
    """Upgrade a subscription to a higher-tier plan."""
    service = SubscriptionService(db)
    return service.upgrade_subscription(subscription_id, payload.new_plan_id)


@router.patch("/{subscription_id}/downgrade", response_model=SubscriptionResponse)
def downgrade_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpgrade,
    db: Session = Depends(get_db),
):
    """Downgrade a subscription to a lower-tier plan."""
    service = SubscriptionService(db)
    return service.downgrade_subscription(subscription_id, payload.new_plan_id)


@router.patch("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: UUID,
    at_period_end: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Cancel a subscription. Optionally cancel at period end."""
    service = SubscriptionService(db)
    return service.cancel_subscription(subscription_id, at_period_end=at_period_end)


@router.patch("/{subscription_id}/reactivate", response_model=SubscriptionResponse)
def reactivate_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
):
    """Reactivate a subscription that was scheduled for cancellation."""
    service = SubscriptionService(db)
    return service.reactivate_subscription(subscription_id)
