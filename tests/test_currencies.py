"""Tests for currency and health endpoints."""


class TestCurrencyEndpoints:
    """Test suite for /api/v1/currencies endpoints."""

    def test_list_currencies(self, client):
        """Test listing all supported currencies."""
        response = client.get("/api/v1/currencies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 39
        # Verify key currencies are present
        codes = [c["code"] for c in data["currencies"]]
        assert "usd" in codes
        assert "eur" in codes
        assert "gbp" in codes
        assert "jpy" in codes
        assert "inr" in codes

    def test_currency_has_required_fields(self, client):
        """Test that each currency has all required fields."""
        response = client.get("/api/v1/currencies")
        for currency in response.json()["currencies"]:
            assert "code" in currency
            assert "name" in currency
            assert "symbol" in currency
            assert "min_charge_amount" in currency


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_check(self, client):
        """Test the health check endpoint returns healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
