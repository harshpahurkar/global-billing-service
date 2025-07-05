from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
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
    stripe_subscription_id: Optional[str] = None
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    subscriptions: List[SubscriptionResponse]
    total: int
    page: int
    per_page: int
