from fastapi import APIRouter, Depends

from app.core.security import require_api_key
from app.services.currency_service import get_supported_currencies
from app.schemas.checkout import CurrencyListResponse

router = APIRouter(
    prefix="/currencies",
    tags=["Currencies"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=CurrencyListResponse)
def list_currencies():
    """List all supported currencies for billing."""
    currencies = get_supported_currencies()
    return CurrencyListResponse(currencies=currencies, total=len(currencies))
