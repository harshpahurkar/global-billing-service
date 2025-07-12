"""Stripe API integration service layer."""

import stripe
import structlog
from typing import Optional, Dict, Any

from app.core.config import get_settings
from app.core.exceptions import StripeError

logger = structlog.get_logger()
settings = get_settings()

# Configure stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for all Stripe API interactions."""

    # --- Customers ---

    @staticmethod
    def create_customer(email: str, name: str, metadata: Optional[Dict] = None) -> stripe.Customer:
        """Create a customer in Stripe."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            logger.info("stripe_customer_created", customer_id=customer.id, email=email)
            return customer
        except stripe.error.StripeError as e:
            logger.error("stripe_customer_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def update_customer(stripe_customer_id: str, **kwargs) -> stripe.Customer:
        """Update a customer in Stripe."""
        try:
            customer = stripe.Customer.modify(stripe_customer_id, **kwargs)
            logger.info("stripe_customer_updated", customer_id=stripe_customer_id)
            return customer
        except stripe.error.StripeError as e:
            logger.error("stripe_customer_update_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def delete_customer(stripe_customer_id: str) -> None:
        """Delete a customer from Stripe."""
        try:
            stripe.Customer.delete(stripe_customer_id)
            logger.info("stripe_customer_deleted", customer_id=stripe_customer_id)
        except stripe.error.StripeError as e:
            logger.error("stripe_customer_delete_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Products & Prices ---

    @staticmethod
    def create_product(name: str, description: Optional[str] = None) -> stripe.Product:
        """Create a product in Stripe."""
        try:
            product = stripe.Product.create(
                name=name,
                description=description or "",
            )
            logger.info("stripe_product_created", product_id=product.id)
            return product
        except stripe.error.StripeError as e:
            logger.error("stripe_product_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def create_price(
        product_id: str,
        amount: int,
        currency: str,
        interval: Optional[str] = None,
        interval_count: int = 1,
    ) -> stripe.Price:
        """Create a price in Stripe. Amount should be in cents."""
        try:
            price_data: Dict[str, Any] = {
                "product": product_id,
                "unit_amount": amount,
                "currency": currency.lower(),
            }
            if interval and interval != "one_time":
                price_data["recurring"] = {
                    "interval": interval if interval != "yearly" else "year",
                    "interval_count": interval_count,
                }
                # Map our intervals to Stripe's
                interval_map = {"monthly": "month", "yearly": "year", "weekly": "week"}
                price_data["recurring"]["interval"] = interval_map.get(interval, interval)

            price = stripe.Price.create(**price_data)
            logger.info("stripe_price_created", price_id=price.id, amount=amount)
            return price
        except stripe.error.StripeError as e:
            logger.error("stripe_price_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Subscriptions ---

    @staticmethod
    def create_subscription(
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
    ) -> stripe.Subscription:
        """Create a subscription in Stripe."""
        try:
            sub_data: Dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "expand": ["latest_invoice.payment_intent"],
            }
            if trial_days > 0:
                sub_data["trial_period_days"] = trial_days

            subscription = stripe.Subscription.create(**sub_data)
            logger.info("stripe_subscription_created", subscription_id=subscription.id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error("stripe_subscription_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def update_subscription(
        stripe_subscription_id: str,
        new_price_id: str,
    ) -> stripe.Subscription:
        """Update (upgrade/downgrade) a subscription in Stripe."""
        try:
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            updated = stripe.Subscription.modify(
                stripe_subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations",
            )
            logger.info("stripe_subscription_updated", subscription_id=stripe_subscription_id)
            return updated
        except stripe.error.StripeError as e:
            logger.error("stripe_subscription_update_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def cancel_subscription(
        stripe_subscription_id: str,
        at_period_end: bool = True,
    ) -> stripe.Subscription:
        """Cancel a subscription in Stripe."""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                subscription = stripe.Subscription.delete(stripe_subscription_id)
            logger.info(
                "stripe_subscription_canceled",
                subscription_id=stripe_subscription_id,
                at_period_end=at_period_end,
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error("stripe_subscription_cancel_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def reactivate_subscription(stripe_subscription_id: str) -> stripe.Subscription:
        """Reactivate a canceled subscription (before period end)."""
        try:
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=False,
            )
            logger.info("stripe_subscription_reactivated", subscription_id=stripe_subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error("stripe_subscription_reactivate_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Invoices ---

    @staticmethod
    def create_invoice(
        customer_id: str,
        description: Optional[str] = None,
        currency: str = "usd",
    ) -> stripe.Invoice:
        """Create an invoice in Stripe."""
        try:
            invoice = stripe.Invoice.create(
                customer=customer_id,
                description=description or "Billing invoice",
                currency=currency.lower(),
                auto_advance=True,
            )
            logger.info("stripe_invoice_created", invoice_id=invoice.id)
            return invoice
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def pay_invoice(stripe_invoice_id: str) -> stripe.Invoice:
        """Pay an invoice in Stripe."""
        try:
            invoice = stripe.Invoice.pay(stripe_invoice_id)
            logger.info("stripe_invoice_paid", invoice_id=stripe_invoice_id)
            return invoice
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_pay_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def void_invoice(stripe_invoice_id: str) -> stripe.Invoice:
        """Void an invoice in Stripe."""
        try:
            invoice = stripe.Invoice.void_invoice(stripe_invoice_id)
            logger.info("stripe_invoice_voided", invoice_id=stripe_invoice_id)
            return invoice
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_void_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Payments ---

    @staticmethod
    def create_payment_intent(
        amount: int,
        currency: str,
        customer_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> stripe.PaymentIntent:
        """Create a payment intent in Stripe. Amount in cents."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency.lower(),
                customer=customer_id,
                description=description,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
            )
            logger.info("stripe_payment_intent_created", intent_id=intent.id, amount=amount)
            return intent
        except stripe.error.StripeError as e:
            logger.error("stripe_payment_intent_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    @staticmethod
    def create_refund(
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> stripe.Refund:
        """Create a refund in Stripe. Amount in cents. None = full refund."""
        try:
            refund_data: Dict[str, Any] = {"payment_intent": payment_intent_id}
            if amount is not None:
                refund_data["amount"] = amount
            if reason:
                refund_data["reason"] = "requested_by_customer"

            refund = stripe.Refund.create(**refund_data)
            logger.info("stripe_refund_created", refund_id=refund.id, amount=amount)
            return refund
        except stripe.error.StripeError as e:
            logger.error("stripe_refund_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Checkout Sessions ---

    @staticmethod
    def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout session."""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                mode=mode,
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info("stripe_checkout_session_created", session_id=session.id)
            return session
        except stripe.error.StripeError as e:
            logger.error("stripe_checkout_session_create_failed", error=str(e))
            raise StripeError(detail=str(e))

    # --- Webhooks ---

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
        """Verify and construct a Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except stripe.error.SignatureVerificationError:
            from app.core.exceptions import WebhookVerificationError
            raise WebhookVerificationError()
        except ValueError:
            raise StripeError(detail="Invalid webhook payload")
