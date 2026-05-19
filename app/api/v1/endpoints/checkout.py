from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BillingException, CustomerNotFoundError, PlanNotFoundError
from app.core.security import require_api_key
from app.db.session import get_db
from app.models.customer import Customer
from app.models.plan import Plan
from app.schemas.checkout import CheckoutSessionCreate, CheckoutSessionResponse
from app.services.stripe_service import StripeService

router = APIRouter(
    prefix="/checkout",
    tags=["Checkout"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/sessions", response_model=CheckoutSessionResponse, status_code=201)
def create_checkout_session(
    payload: CheckoutSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for purchasing a plan."""
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise CustomerNotFoundError(str(payload.customer_id))

    plan = db.query(Plan).filter(Plan.id == payload.plan_id, Plan.is_active.is_(True)).first()
    if not plan:
        raise PlanNotFoundError(str(payload.plan_id))

    if not customer.stripe_customer_id or not plan.stripe_price_id:
        raise BillingException(detail="Customer or plan is missing Stripe integration")

    # Determine checkout mode
    mode = "subscription" if plan.interval.value != "one_time" else "payment"
    currency = payload.currency or customer.currency

    stripe_service = StripeService()
    session = stripe_service.create_checkout_session(
        customer_id=customer.stripe_customer_id,
        price_id=plan.stripe_price_id,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        mode=mode,
    )

    return CheckoutSessionResponse(
        session_id=session.id,
        checkout_url=session.url,
        customer_id=customer.id,
        plan_id=plan.id,
        currency=currency,
        amount=float(plan.amount),
    )
