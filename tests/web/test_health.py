"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests for /api/health endpoint."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health check should return OK status."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data

    async def test_health_returns_json(self, client: AsyncClient) -> None:
        """Health check should return JSON content type."""
        response = await client.get("/api/health")

        assert "application/json" in response.headers["content-type"]


class TestRootEndpoint:
    """Tests for root / endpoint."""

    async def test_root_returns_html(self, client: AsyncClient) -> None:
        """Root endpoint should return HTML."""
        response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_root_contains_api_info(self, client: AsyncClient) -> None:
        """Root endpoint should contain API information."""
        response = await client.get("/")

        assert "Ankification" in response.text
