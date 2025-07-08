import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# Use SQLite in-memory for tests
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
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
def client(db_session):
    """Create a test client with a fresh database."""
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
    with patch("app.services.stripe_service.stripe") as mock:
        # Mock customer creation
        mock_customer = MagicMock()
        mock_customer.id = "cus_test_123"
        mock.Customer.create.return_value = mock_customer
        mock.Customer.modify.return_value = mock_customer
        mock.Customer.delete.return_value = None

        # Mock product and price creation
        mock_product = MagicMock()
        mock_product.id = "prod_test_123"
        mock.Product.create.return_value = mock_product

        mock_price = MagicMock()
        mock_price.id = "price_test_123"
        mock.Price.create.return_value = mock_price

        # Mock subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_123"
        mock_subscription.__getitem__ = lambda self, key: {"items": {"data": [MagicMock(id="si_test")]}}[key]
        mock.Subscription.create.return_value = mock_subscription
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

        # Mock invoice
        mock_invoice = MagicMock()
        mock_invoice.id = "in_test_123"
        mock.Invoice.create.return_value = mock_invoice
        mock.Invoice.pay.return_value = mock_invoice
        mock.Invoice.void_invoice.return_value = mock_invoice

        # Mock checkout session
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock.checkout.Session.create.return_value = mock_session

        yield mock
