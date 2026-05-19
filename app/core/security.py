"""API key authentication and verification helpers."""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, status
from sqlalchemy.orm import Session

from app.core.exceptions import BillingException
from app.db.session import get_db
from app.models.api_key import APIKey


API_KEY_PREFIX = "gbs_"
_RAW_KEY_BYTES = 32  # 32 bytes -> 43-char base64url body


class AuthenticationError(BillingException):
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


def generate_api_key() -> str:
    """Generate a new random API key string. Show this once; only the hash is stored."""
    return API_KEY_PREFIX + secrets.token_urlsafe(_RAW_KEY_BYTES)


def hash_api_key(plain_key: str) -> str:
    """Return the SHA-256 hex digest of an API key for storage."""
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time comparison between a supplied key and its stored hash."""
    return hmac.compare_digest(hash_api_key(plain_key), hashed_key)


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> APIKey:
    """FastAPI dependency: require a valid X-API-Key header.

    Looks up by hash (constant-time at the DB layer) and updates last_used_at
    on success. Raises 401 for missing, malformed, unknown, or deactivated keys.
    """
    if not x_api_key:
        raise AuthenticationError("Missing X-API-Key header")

    hashed = hash_api_key(x_api_key)
    api_key = db.query(APIKey).filter(APIKey.hashed_key == hashed).first()
    if api_key is None or not api_key.is_active:
        raise AuthenticationError()

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key
