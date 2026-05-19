from fastapi import APIRouter

from app.api.v1.endpoints import (
    checkout,
    currencies,
    customers,
    invoices,
    payments,
    plans,
    subscriptions,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(customers.router)
api_router.include_router(plans.router)
api_router.include_router(subscriptions.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
api_router.include_router(checkout.router)
api_router.include_router(webhooks.router)
api_router.include_router(currencies.router)
