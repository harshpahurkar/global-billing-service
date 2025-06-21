"""Supported currencies with metadata for multi-currency billing."""

from typing import Dict, List, Optional
from app.schemas.checkout import CurrencyResponse


SUPPORTED_CURRENCIES: Dict[str, dict] = {
    "usd": {"name": "US Dollar", "symbol": "$", "min_charge": 0.50},
    "eur": {"name": "Euro", "symbol": "€", "min_charge": 0.50},
    "gbp": {"name": "British Pound", "symbol": "£", "min_charge": 0.30},
    "cad": {"name": "Canadian Dollar", "symbol": "CA$", "min_charge": 0.50},
    "aud": {"name": "Australian Dollar", "symbol": "A$", "min_charge": 0.50},
    "jpy": {"name": "Japanese Yen", "symbol": "¥", "min_charge": 50},
    "inr": {"name": "Indian Rupee", "symbol": "₹", "min_charge": 0.50},
    "brl": {"name": "Brazilian Real", "symbol": "R$", "min_charge": 0.50},
    "mxn": {"name": "Mexican Peso", "symbol": "MX$", "min_charge": 10},
    "sgd": {"name": "Singapore Dollar", "symbol": "S$", "min_charge": 0.50},
    "hkd": {"name": "Hong Kong Dollar", "symbol": "HK$", "min_charge": 4.00},
    "nzd": {"name": "New Zealand Dollar", "symbol": "NZ$", "min_charge": 0.50},
    "sek": {"name": "Swedish Krona", "symbol": "kr", "min_charge": 3.00},
    "nok": {"name": "Norwegian Krone", "symbol": "kr", "min_charge": 3.00},
    "dkk": {"name": "Danish Krone", "symbol": "kr", "min_charge": 2.50},
    "chf": {"name": "Swiss Franc", "symbol": "CHF", "min_charge": 0.50},
    "pln": {"name": "Polish Zloty", "symbol": "zł", "min_charge": 2.00},
    "czk": {"name": "Czech Koruna", "symbol": "Kč", "min_charge": 15.00},
    "ron": {"name": "Romanian Leu", "symbol": "lei", "min_charge": 2.00},
    "bgn": {"name": "Bulgarian Lev", "symbol": "лв", "min_charge": 1.00},
    "huf": {"name": "Hungarian Forint", "symbol": "Ft", "min_charge": 175.00},
    "krw": {"name": "South Korean Won", "symbol": "₩", "min_charge": 500},
    "thb": {"name": "Thai Baht", "symbol": "฿", "min_charge": 10},
    "myr": {"name": "Malaysian Ringgit", "symbol": "RM", "min_charge": 2},
    "php": {"name": "Philippine Peso", "symbol": "₱", "min_charge": 100},
    "idr": {"name": "Indonesian Rupiah", "symbol": "Rp", "min_charge": 10000},
    "twd": {"name": "New Taiwan Dollar", "symbol": "NT$", "min_charge": 50},
    "zar": {"name": "South African Rand", "symbol": "R", "min_charge": 10},
    "aed": {"name": "UAE Dirham", "symbol": "د.إ", "min_charge": 2.00},
    "sar": {"name": "Saudi Riyal", "symbol": "﷼", "min_charge": 2.00},
    "ils": {"name": "Israeli Shekel", "symbol": "₪", "min_charge": 3.00},
    "try": {"name": "Turkish Lira", "symbol": "₺", "min_charge": 10.00},
    "clp": {"name": "Chilean Peso", "symbol": "CL$", "min_charge": 500},
    "cop": {"name": "Colombian Peso", "symbol": "CO$", "min_charge": 2000},
    "pen": {"name": "Peruvian Sol", "symbol": "S/.", "min_charge": 2.00},
    "ars": {"name": "Argentine Peso", "symbol": "AR$", "min_charge": 100},
    "egp": {"name": "Egyptian Pound", "symbol": "E£", "min_charge": 10},
    "ngn": {"name": "Nigerian Naira", "symbol": "₦", "min_charge": 500},
    "kes": {"name": "Kenyan Shilling", "symbol": "KSh", "min_charge": 100},
}


def get_supported_currencies() -> List[CurrencyResponse]:
    """Return a list of all supported currencies."""
    return [
        CurrencyResponse(
            code=code,
            name=info["name"],
            symbol=info["symbol"],
            min_charge_amount=info["min_charge"],
        )
        for code, info in SUPPORTED_CURRENCIES.items()
    ]


def is_currency_supported(currency: str) -> bool:
    """Check if a currency code is supported."""
    return currency.lower() in SUPPORTED_CURRENCIES


def get_currency_info(currency: str) -> Optional[dict]:
    """Get metadata for a specific currency."""
    return SUPPORTED_CURRENCIES.get(currency.lower())


def get_min_charge_amount(currency: str) -> float:
    """Get the minimum charge amount for a currency."""
    info = SUPPORTED_CURRENCIES.get(currency.lower())
    if info:
        return info["min_charge"]
    return 0.50  # default
