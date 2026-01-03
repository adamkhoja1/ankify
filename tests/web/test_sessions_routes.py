"""Tests for session management API routes."""

import pytest
from httpx import AsyncClient

from ankification.cards.models import BasicCard


class TestListSessions:
    """Tests for GET /api/sessions."""

    async def test_list_sessions_empty(self, client: AsyncClient) -> None:
        """Listing sessions on empty database returns empty list."""
        response = await client.get("/api/sessions")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_sessions_with_data(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Listing sessions returns session data."""
        client, session_id, cards = client_with_session

        response = await client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == session_id for s in data)


class TestGetSession:
    """Tests for GET /api/sessions/{session_id}."""

    async def test_get_session_success(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Getting existing session returns session data."""
        client, session_id, cards = client_with_session

        response = await client.get(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id

    async def test_get_session_not_found(self, client: AsyncClient) -> None:
        """Getting nonexistent session returns 404."""
        response = await client.get("/api/sessions/nonexistent-id")

        assert response.status_code == 404

    async def test_session_response_has_statistics(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Session response includes card statistics."""
        client, session_id, cards = client_with_session

        response = await client.get(f"/api/sessions/{session_id}")
        data = response.json()

        assert "card_count" in data
        assert "accepted_count" in data
        assert "rejected_count" in data
        assert "pending_count" in data


class TestGetSessionCards:
    """Tests for GET /api/sessions/{session_id}/cards."""

    async def test_get_session_cards_success(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Getting session cards returns card list."""
        client, session_id, cards = client_with_session

        response = await client.get(f"/api/sessions/{session_id}/cards")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(cards)

    async def test_get_session_cards_not_found(self, client: AsyncClient) -> None:
        """Getting cards for nonexistent session returns 404."""
        response = await client.get("/api/sessions/nonexistent/cards")

        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /api/sessions/{session_id}."""

    async def test_delete_session_success(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Deleting session works."""
        client, session_id, cards = client_with_session

        response = await client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    async def test_delete_session_removes_cards(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Deleting session also removes associated cards."""
        client, session_id, cards = client_with_session
        card_ids = [c.id for c in cards]

        await client.delete(f"/api/sessions/{session_id}")

        # Verify cards are gone
        for card_id in card_ids:
            response = await client.get(f"/api/cards/{card_id}")
            assert response.status_code == 404

    async def test_delete_session_not_found(self, client: AsyncClient) -> None:
        """Deleting nonexistent session returns 404."""
        response = await client.delete("/api/sessions/nonexistent")

        assert response.status_code == 404


class TestSessionResponseFormat:
    """Tests for session response data format."""

    async def test_session_response_has_required_fields(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Session response contains all required fields."""
        client, session_id, _ = client_with_session

        response = await client.get(f"/api/sessions/{session_id}")
        data = response.json()

        required_fields = [
            "id",
            "sources",
            "provider",
            "card_types",
            "count_guidance",
            "created_at",
            "completed_at",
            "card_count",
            "accepted_count",
            "rejected_count",
            "pending_count",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_session_sources_is_list(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Session sources should be a list."""
        client, session_id, _ = client_with_session

        response = await client.get(f"/api/sessions/{session_id}")
        data = response.json()

        assert isinstance(data["sources"], list)

    async def test_session_card_types_is_list(
        self, client_with_session: tuple[AsyncClient, str, list[BasicCard]]
    ) -> None:
        """Session card_types should be a list."""
        client, session_id, _ = client_with_session

        response = await client.get(f"/api/sessions/{session_id}")
        data = response.json()

        assert isinstance(data["card_types"], list)
