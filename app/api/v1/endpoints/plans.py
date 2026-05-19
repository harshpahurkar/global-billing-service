from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.security import require_api_key
from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse, PlanListResponse
from app.core.exceptions import PlanNotFoundError
from app.services.stripe_service import StripeService

router = APIRouter(
    prefix="/plans",
    tags=["Plans"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=PlanResponse, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    """Create a new billing plan with Stripe product and price."""
    stripe_service = StripeService()

    # Create product in Stripe
    stripe_product = stripe_service.create_product(
        name=payload.name,
        description=payload.description,
    )

    # Create price in Stripe (amount in cents)
    amount_cents = int(payload.amount * 100)
    stripe_price = stripe_service.create_price(
        product_id=stripe_product.id,
        amount=amount_cents,
        currency=payload.currency,
        interval=payload.interval.value if payload.interval.value != "one_time" else None,
        interval_count=payload.interval_count,
    )

    plan = Plan(
        name=payload.name,
        description=payload.description,
        stripe_product_id=stripe_product.id,
        stripe_price_id=stripe_price.id,
        amount=payload.amount,
        currency=payload.currency.lower(),
        interval=payload.interval,
        interval_count=payload.interval_count,
        trial_days=payload.trial_days,
        features=payload.features,
        sort_order=payload.sort_order,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=PlanListResponse)
def list_plans(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all available plans."""
    query = db.query(Plan)
    if active_only:
        query = query.filter(Plan.is_active.is_(True))

    plans = query.order_by(Plan.sort_order, Plan.amount).all()
    return PlanListResponse(plans=plans, total=len(plans))


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Get a plan by ID."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise PlanNotFoundError(str(plan_id))
    return plan


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
):
    """Update a plan's metadata (not pricing — create new plan for price changes)."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise PlanNotFoundError(str(plan_id))

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def deactivate_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Deactivate a plan (soft delete)."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise PlanNotFoundError(str(plan_id))

    plan.is_active = False
    db.commit()
    return None
