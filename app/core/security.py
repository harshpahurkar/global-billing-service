import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def create_api_key_hash(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hmac.compare_digest(
        hashlib.sha256(plain_key.encode()).hexdigest(), hashed_key
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire})
    settings = get_settings()
    return jwt.encode(to_encode, settings.STRIPE_SECRET_KEY, algorithm=ALGORITHM)
