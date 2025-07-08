"""Tests for customer endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestCustomerEndpoints:
    """Test suite for /api/v1/customers endpoints."""

    def test_create_customer(self, client, mock_stripe):
        """Test creating a new customer."""
        response = client.post(
            "/api/v1/customers",
            json={
                "email": "test@example.com",
                "name": "Test User",
                "currency": "usd",
                "country": "US",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["currency"] == "usd"
        assert data["is_active"] is True
        assert data["id"] is not None

    def test_create_duplicate_customer(self, client, mock_stripe):
        """Test creating a customer with duplicate email fails."""
        # Create first customer
        client.post(
            "/api/v1/customers",
            json={"email": "dupe@example.com", "name": "First"},
        )
        # Try duplicate
        response = client.post(
            "/api/v1/customers",
            json={"email": "dupe@example.com", "name": "Second"},
        )
        assert response.status_code == 409

    def test_get_customer(self, client, mock_stripe):
        """Test getting a customer by ID."""
        # Create customer
        create_response = client.post(
            "/api/v1/customers",
            json={"email": "get@example.com", "name": "Get User"},
        )
        customer_id = create_response.json()["id"]

        # Get customer
        response = client.get(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "get@example.com"

    def test_get_customer_not_found(self, client):
        """Test getting a non-existent customer returns 404."""
        response = client.get("/api/v1/customers/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_list_customers(self, client, mock_stripe):
        """Test listing customers with pagination."""
        # Create a few customers
        for i in range(3):
            client.post(
                "/api/v1/customers",
                json={"email": f"list{i}@example.com", "name": f"User {i}"},
            )

        response = client.get("/api/v1/customers?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["customers"]) == 3

    def test_update_customer(self, client, mock_stripe):
        """Test updating a customer."""
        create_response = client.post(
            "/api/v1/customers",
            json={"email": "update@example.com", "name": "Old Name"},
        )
        customer_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/customers/{customer_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_delete_customer(self, client, mock_stripe):
        """Test soft-deleting a customer."""
        create_response = client.post(
            "/api/v1/customers",
            json={"email": "delete@example.com", "name": "Delete Me"},
        )
        customer_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 204

        # Verify customer is deactivated
        get_response = client.get(f"/api/v1/customers/{customer_id}")
        assert get_response.json()["is_active"] is False
