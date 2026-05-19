import os

# Disable rate limiting during the test suite. Must be set before any module
# that calls get_settings() is imported, otherwise the Settings lru_cache
# captures APP_ENV=development.
os.environ.setdefault("APP_ENV", "testing")

import itertools
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import generate_api_key, hash_api_key
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.api_key import APIKey

# In-memory SQLite, shared across connections via StaticPool so the API
# request handler and the test fixture see the same data.
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def api_key(db_session):
    """Seed an active API key and return the plaintext value."""
    plain = generate_api_key()
    db_session.add(APIKey(name="test-key", hashed_key=hash_api_key(plain), is_active=True))
    db_session.commit()
    return plain


@pytest.fixture(scope="function")
def client(db_session, api_key):
    """Create a test client with a fresh DB and the X-API-Key header pre-set."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"X-API-Key": api_key}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauthenticated_client(db_session):
    """Test client without an API key, for testing auth rejection."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_stripe():
    """Mock all Stripe API calls."""
    import stripe as real_stripe

    with patch("app.services.stripe_service.stripe") as mock:
        # Preserve the real exception classes so `except stripe.StripeError`
        # in service code resolves to a real BaseException subclass.
        mock.StripeError = real_stripe.StripeError
        mock.SignatureVerificationError = real_stripe.SignatureVerificationError

        # Counters for unique IDs
        _cus_counter = itertools.count(1)
        _prod_counter = itertools.count(1)
        _price_counter = itertools.count(1)
        _sub_counter = itertools.count(1)
        _inv_counter = itertools.count(1)

        # Mock customer creation - unique IDs each call
        def _create_customer(**kwargs):
            m = MagicMock()
            m.id = f"cus_test_{next(_cus_counter)}"
            return m
        mock.Customer.create.side_effect = _create_customer
        mock.Customer.modify.return_value = MagicMock(id="cus_test_1")
        mock.Customer.delete.return_value = None

        # Mock product and price creation - unique IDs each call
        def _create_product(**kwargs):
            m = MagicMock()
            m.id = f"prod_test_{next(_prod_counter)}"
            return m
        mock.Product.create.side_effect = _create_product

        def _create_price(**kwargs):
            m = MagicMock()
            m.id = f"price_test_{next(_price_counter)}"
            return m
        mock.Price.create.side_effect = _create_price

        # Mock subscription - unique IDs each call
        def _create_subscription(**kwargs):
            m = MagicMock()
            m.id = f"sub_test_{next(_sub_counter)}"
            m.__getitem__ = lambda self, key: {"items": {"data": [MagicMock(id="si_test")]}}[key]
            return m
        mock.Subscription.create.side_effect = _create_subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_1"
        mock_subscription.__getitem__ = lambda self, key: {"items": {"data": [MagicMock(id="si_test")]}}[key]
        mock.Subscription.modify.return_value = mock_subscription
        mock.Subscription.retrieve.return_value = mock_subscription
        mock.Subscription.delete.return_value = mock_subscription

        # Mock payment intent
        mock_intent = MagicMock()
        mock_intent.id = "pi_test_123"
        mock.PaymentIntent.create.return_value = mock_intent

        # Mock refund
        mock_refund = MagicMock()
        mock_refund.id = "re_test_123"
        mock.Refund.create.return_value = mock_refund

        # Mock invoice - unique IDs each call
        def _create_invoice(**kwargs):
            m = MagicMock()
            m.id = f"in_test_{next(_inv_counter)}"
            return m
        mock.Invoice.create.side_effect = _create_invoice
        mock.Invoice.pay.return_value = MagicMock(id="in_test_1")
        mock.Invoice.void_invoice.return_value = MagicMock(id="in_test_1")

        # Mock checkout session
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock.checkout.Session.create.return_value = mock_session

        yield mock
