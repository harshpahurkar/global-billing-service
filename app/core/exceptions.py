from fastapi import HTTPException, status


class BillingException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class CustomerNotFoundError(BillingException):
    def __init__(self, customer_id: str):
        super().__init__(
            detail=f"Customer with id '{customer_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PlanNotFoundError(BillingException):
    def __init__(self, plan_id: str):
        super().__init__(
            detail=f"Plan with id '{plan_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SubscriptionNotFoundError(BillingException):
    def __init__(self, subscription_id: str):
        super().__init__(
            detail=f"Subscription with id '{subscription_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvoiceNotFoundError(BillingException):
    def __init__(self, invoice_id: str):
        super().__init__(
            detail=f"Invoice with id '{invoice_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PaymentNotFoundError(BillingException):
    def __init__(self, payment_id: str):
        super().__init__(
            detail=f"Payment with id '{payment_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SubscriptionAlreadyCancelledError(BillingException):
    def __init__(self):
        super().__init__(
            detail="Subscription is already cancelled",
            status_code=status.HTTP_409_CONFLICT,
        )


class SubscriptionNotActiveError(BillingException):
    def __init__(self):
        super().__init__(
            detail="Subscription is not active",
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidCurrencyError(BillingException):
    def __init__(self, currency: str):
        super().__init__(
            detail=f"Currency '{currency}' is not supported",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class StripeError(BillingException):
    def __init__(self, detail: str):
        super().__init__(
            detail=f"Stripe error: {detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class DuplicateCustomerError(BillingException):
    def __init__(self, email: str):
        super().__init__(
            detail=f"Customer with email '{email}' already exists",
            status_code=status.HTTP_409_CONFLICT,
        )


class WebhookVerificationError(BillingException):
    def __init__(self):
        super().__init__(
            detail="Invalid webhook signature",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
