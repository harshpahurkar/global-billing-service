"""Tests for plan management endpoints."""



class TestPlanEndpoints:
    """Test suite for /api/v1/plans endpoints."""

    def test_create_plan(self, client, mock_stripe):
        """Test creating a new plan."""
        response = client.post(
            "/api/v1/plans",
            json={
                "name": "Basic Plan",
                "description": "Entry level plan",
                "amount": 9.99,
                "currency": "usd",
                "interval": "monthly",
                "trial_days": 14,
                "features": '["feature1", "feature2"]',
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Basic Plan"
        assert data["amount"] == 9.99
        assert data["interval"] == "monthly"
        assert data["trial_days"] == 14

    def test_list_plans(self, client, mock_stripe):
        """Test listing plans."""
        # Create plans
        for name, amount in [("Basic", 9.99), ("Pro", 29.99), ("Enterprise", 99.99)]:
            client.post(
                "/api/v1/plans",
                json={"name": name, "amount": amount, "currency": "usd", "interval": "monthly"},
            )

        response = client.get("/api/v1/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_get_plan(self, client, mock_stripe):
        """Test getting a plan by ID."""
        create_response = client.post(
            "/api/v1/plans",
            json={"name": "Test Plan", "amount": 19.99, "currency": "usd", "interval": "monthly"},
        )
        plan_id = create_response.json()["id"]

        response = client.get(f"/api/v1/plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Plan"

    def test_update_plan(self, client, mock_stripe):
        """Test updating a plan."""
        create_response = client.post(
            "/api/v1/plans",
            json={"name": "Old Name", "amount": 9.99, "currency": "usd", "interval": "monthly"},
        )
        plan_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/plans/{plan_id}",
            json={"name": "New Name", "description": "Updated description"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_deactivate_plan(self, client, mock_stripe):
        """Test deactivating a plan."""
        create_response = client.post(
            "/api/v1/plans",
            json={"name": "Deactivate Me", "amount": 9.99, "currency": "usd", "interval": "monthly"},
        )
        plan_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/plans/{plan_id}")
        assert response.status_code == 204

        # Verify plan is deactivated (should not show in active list)
        list_response = client.get("/api/v1/plans?active_only=true")
        plan_ids = [p["id"] for p in list_response.json()["plans"]]
        assert plan_id not in plan_ids
