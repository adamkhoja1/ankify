"""Tests for card management API routes."""

import pytest
from httpx import AsyncClient

from ankification.cards.models import BasicCard, CardStatus


class TestListCards:
    """Tests for GET /api/cards."""

    async def test_list_cards_empty(self, client: AsyncClient) -> None:
        """Listing cards on empty database returns empty list."""
        response = await client.get("/api/cards")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_cards_returns_all(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Listing cards returns all cards."""
        client, cards = client_with_cards
        response = await client.get("/api/cards")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(cards)

    async def test_list_cards_filter_by_status(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Filtering by status returns correct cards."""
        client, cards = client_with_cards

        # Filter by accepted
        response = await client.get("/api/cards", params={"status": "accepted"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # We set 2 cards to accepted
        assert all(c["status"] == "accepted" for c in data)

    async def test_list_cards_pagination(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Pagination parameters work correctly."""
        client, cards = client_with_cards

        # Limit
        response = await client.get("/api/cards", params={"limit": 2})
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Offset
        response = await client.get("/api/cards", params={"offset": 3})
        assert response.status_code == 200
        assert len(response.json()) == 2  # 5 - 3 = 2


class TestGetCard:
    """Tests for GET /api/cards/{card_id}."""

    async def test_get_card_success(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Getting existing card returns card data."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.get(f"/api/cards/{card_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == card_id
        assert data["type"] == "basic"

    async def test_get_card_not_found(self, client: AsyncClient) -> None:
        """Getting nonexistent card returns 404."""
        response = await client.get("/api/cards/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateCardStatus:
    """Tests for PATCH /api/cards/{card_id}/status."""

    async def test_update_status_to_accepted(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Updating status to accepted works."""
        client, cards = client_with_cards
        card_id = cards[3].id  # A draft card

        response = await client.patch(
            f"/api/cards/{card_id}/status",
            json={"status": "accepted"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    async def test_update_status_to_rejected(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Updating status to rejected works."""
        client, cards = client_with_cards
        card_id = cards[0].id  # An accepted card

        response = await client.patch(
            f"/api/cards/{card_id}/status",
            json={"status": "rejected"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    async def test_update_status_not_found(self, client: AsyncClient) -> None:
        """Updating nonexistent card returns 404."""
        response = await client.patch(
            "/api/cards/nonexistent/status",
            json={"status": "accepted"},
        )

        assert response.status_code == 404


class TestUpdateCard:
    """Tests for PUT /api/cards/{card_id}."""

    async def test_update_card_front_back(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Updating card front/back works."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.put(
            f"/api/cards/{card_id}",
            json={"front": "New question?", "back": "New answer"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"]["front"] == "New question?"
        assert data["content"]["back"] == "New answer"

    async def test_update_card_tags(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Updating card tags works."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.put(
            f"/api/cards/{card_id}",
            json={"tags": ["new-tag", "another-tag"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "new-tag" in data["tags"]
        assert "another-tag" in data["tags"]

    async def test_update_card_not_found(self, client: AsyncClient) -> None:
        """Updating nonexistent card returns 404."""
        response = await client.put(
            "/api/cards/nonexistent",
            json={"front": "new"},
        )

        assert response.status_code == 404


class TestDeleteCard:
    """Tests for DELETE /api/cards/{card_id}."""

    async def test_delete_card_success(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Deleting card works."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.delete(f"/api/cards/{card_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify card is gone
        get_response = await client.get(f"/api/cards/{card_id}")
        assert get_response.status_code == 404

    async def test_delete_card_not_found(self, client: AsyncClient) -> None:
        """Deleting nonexistent card returns 404."""
        response = await client.delete("/api/cards/nonexistent")

        assert response.status_code == 404


class TestCardResponseFormat:
    """Tests for card response data format."""

    async def test_card_response_has_required_fields(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Card response contains all required fields."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.get(f"/api/cards/{card_id}")
        data = response.json()

        assert "id" in data
        assert "type" in data
        assert "content" in data
        assert "source" in data
        assert "status" in data
        assert "tags" in data
        assert "created_at" in data
        assert "modified_at" in data

    async def test_card_response_content_format(
        self, client_with_cards: tuple[AsyncClient, list[BasicCard]]
    ) -> None:
        """Card content is properly formatted."""
        client, cards = client_with_cards
        card_id = cards[0].id

        response = await client.get(f"/api/cards/{card_id}")
        data = response.json()

        # Basic card should have front and back in content
        assert "front" in data["content"]
        assert "back" in data["content"]
