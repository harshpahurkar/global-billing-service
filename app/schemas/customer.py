from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CustomerCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    phone: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    phone: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    id: UUID
    email: str
    name: str
    stripe_customer_id: Optional[str] = None
    currency: str
    country: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    customers: List[CustomerResponse]
    total: int
    page: int
    per_page: int
