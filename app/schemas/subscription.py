from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.subscription import SubscriptionStatus


class SubscriptionCreate(BaseModel):
    customer_id: UUID
    plan_id: UUID
    currency: str = Field(default="usd", min_length=3, max_length=3)


class SubscriptionUpgrade(BaseModel):
    new_plan_id: UUID


class SubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    plan_id: UUID
    stripe_subscription_id: str | None = None
    status: SubscriptionStatus
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at: datetime | None = None
    canceled_at: datetime | None = None
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionResponse]
    total: int
    page: int
    per_page: int
