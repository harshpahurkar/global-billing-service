"""Tests for the X-API-Key authentication dependency."""


class TestAPIKeyAuth:
    """Verify that protected endpoints reject unauthenticated and bad-key requests."""

    def test_missing_api_key_rejected(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/v1/customers")
        assert response.status_code == 401
        assert "X-API-Key" in response.json()["error"]["message"]

    def test_invalid_api_key_rejected(self, unauthenticated_client):
        response = unauthenticated_client.get(
            "/api/v1/customers",
            headers={"X-API-Key": "gbs_not-a-real-key"},
        )
        assert response.status_code == 401

    def test_inactive_api_key_rejected(self, db_session, unauthenticated_client):
        from app.core.security import generate_api_key, hash_api_key
        from app.models.api_key import APIKey

        plain = generate_api_key()
        db_session.add(APIKey(name="disabled", hashed_key=hash_api_key(plain), is_active=False))
        db_session.commit()

        response = unauthenticated_client.get(
            "/api/v1/customers",
            headers={"X-API-Key": plain},
        )
        assert response.status_code == 401

    def test_health_endpoint_is_public(self, unauthenticated_client):
        response = unauthenticated_client.get("/health")
        assert response.status_code == 200

    def test_valid_api_key_accepted(self, client):
        # The `client` fixture pre-sets a valid X-API-Key header.
        response = client.get("/api/v1/customers")
        assert response.status_code == 200

    def test_last_used_at_is_updated(self, db_session, client):
        from app.models.api_key import APIKey

        client.get("/api/v1/customers")
        key = db_session.query(APIKey).first()
        assert key.last_used_at is not None
