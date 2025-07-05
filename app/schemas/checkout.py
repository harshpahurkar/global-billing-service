from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID


class CheckoutSessionCreate(BaseModel):
    customer_id: UUID
    plan_id: UUID
    success_url: str = Field(..., max_length=500)
    cancel_url: str = Field(..., max_length=500)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    customer_id: UUID
    plan_id: UUID
    currency: str
    amount: float


class CurrencyResponse(BaseModel):
    code: str
    name: str
    symbol: str
    min_charge_amount: float


class CurrencyListResponse(BaseModel):
    currencies: List[CurrencyResponse]
    total: int
