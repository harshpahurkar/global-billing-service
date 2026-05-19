from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.security import require_api_key
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
)
from app.core.exceptions import CustomerNotFoundError, DuplicateCustomerError
from app.services.stripe_service import StripeService

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=CustomerResponse, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer.

    Local row is written first with no Stripe ID, then Stripe is called with
    `idempotency_key=<local_id>` and `metadata={"local_id": ...}`. If the
    Stripe call fails, the local row persists with `stripe_customer_id=NULL`
    so a reconciliation job can retry without creating duplicates.
    """
    existing = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing:
        raise DuplicateCustomerError(payload.email)

    customer = Customer(
        email=payload.email,
        name=payload.name,
        stripe_customer_id=None,
        currency=payload.currency.lower(),
        country=payload.country,
        phone=payload.phone,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    stripe_customer = StripeService.create_customer(
        email=payload.email,
        name=payload.name,
        metadata={"local_id": str(customer.id)},
        idempotency_key=str(customer.id),
    )

    customer.stripe_customer_id = stripe_customer.id
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List customers with pagination."""
    query = db.query(Customer).filter(Customer.is_active == is_active)
    total = query.count()
    customers = (
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return CustomerListResponse(
        customers=customers,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    """Get a customer by ID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(customer_id))
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
):
    """Update a customer's information."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(customer_id))

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    # Sync with Stripe
    if customer.stripe_customer_id:
        stripe_update = {}
        if "name" in update_data:
            stripe_update["name"] = update_data["name"]
        if stripe_update:
            StripeService.update_customer(customer.stripe_customer_id, **stripe_update)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete a customer (deactivate)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(customer_id))

    customer.is_active = False
    db.commit()
    return None
