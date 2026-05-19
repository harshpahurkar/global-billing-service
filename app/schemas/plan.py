from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.plan import PlanInterval


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    interval: PlanInterval = PlanInterval.MONTHLY
    interval_count: int = Field(default=1, ge=1)
    trial_days: int = Field(default=0, ge=0)
    features: str | None = None
    sort_order: int = Field(default=0, ge=0)


class PlanUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    amount: float | None = Field(None, gt=0)
    is_active: bool | None = None
    features: str | None = None
    sort_order: int | None = Field(None, ge=0)


class PlanResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    stripe_product_id: str | None = None
    stripe_price_id: str | None = None
    amount: float
    currency: str
    interval: PlanInterval
    interval_count: int
    trial_days: int
    is_active: bool
    features: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    total: int
