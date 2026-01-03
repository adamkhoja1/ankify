"""AnkiConnect API integration."""

from typing import Any

import httpx

from ..cards.models import BasicCard, Card, CardType, ClozeCard


class ExportResult:
    """Result of an export operation."""

    def __init__(self) -> None:
        self.success: int = 0
        self.failed: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"success": self.success, "failed": self.failed, "errors": self.errors}


class AnkiConnectExporter:
    """Export cards via AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765", deck: str = "Default") -> None:
        """Initialize AnkiConnect exporter.

        Args:
            url: AnkiConnect API URL
            deck: Target deck name
        """
        self.url = url
        self.deck = deck

    async def test_connection(self) -> bool:
        """Test connection to AnkiConnect.

        Returns:
            True if connection successful

        Raises:
            RuntimeError: If connection fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    json={"action": "version", "version": 6},
                    timeout=5.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("error") is None
        except Exception as e:
            raise RuntimeError(f"Failed to connect to AnkiConnect: {e}") from e

    async def export(self, cards: list[Card]) -> dict[str, Any]:
        """Export cards to Anki via AnkiConnect.

        Args:
            cards: Cards to export

        Returns:
            Dictionary with success/failure counts and errors list

        Raises:
            ValueError: If no cards provided
            RuntimeError: If export fails
        """
        if not cards:
            raise ValueError("No cards to export")

        result = ExportResult()

        for card in cards:
            try:
                await self._add_card(card)
                result.success += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Card {card.id}: {str(e)}")

        return result.to_dict()

    async def _add_card(self, card: Card) -> None:
        """Add a single card to Anki.

        Args:
            card: Card to add

        Raises:
            RuntimeError: If add fails
        """
        if card.type == CardType.BASIC:
            await self._add_basic_card(card)
        else:
            await self._add_cloze_card(card)

    async def _add_basic_card(self, card: Card) -> None:
        """Add a basic card to Anki.

        Args:
            card: Basic card to add
        """
        assert isinstance(card, BasicCard)

        note = {
            "deckName": self.deck,
            "modelName": "Basic",
            "fields": {"Front": card.front, "Back": card.back},
            "tags": card.tags,
        }

        await self._invoke("addNote", note=note)

    async def _add_cloze_card(self, card: Card) -> None:
        """Add a cloze card to Anki.

        Args:
            card: Cloze card to add
        """
        assert isinstance(card, ClozeCard)

        note = {
            "deckName": self.deck,
            "modelName": "Cloze",
            "fields": {"Text": card.text, "Extra": ""},
            "tags": card.tags,
        }

        await self._invoke("addNote", note=note)

    async def _invoke(self, action: str, **params: Any) -> Any:
        """Invoke AnkiConnect API.

        Args:
            action: API action name
            **params: Action parameters

        Returns:
            API response data (type varies by action)

        Raises:
            RuntimeError: If API call fails
        """
        request_data: dict[str, Any] = {"action": action, "version": 6, "params": params}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url, json=request_data, timeout=10.0
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()

                if data.get("error"):
                    raise RuntimeError(f"AnkiConnect error: {data['error']}")

                return data.get("result")

        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error calling AnkiConnect: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to call AnkiConnect: {e}") from e

    async def create_deck(self, deck_name: str) -> None:
        """Create a new deck in Anki.

        Args:
            deck_name: Name of deck to create

        Raises:
            RuntimeError: If creation fails
        """
        await self._invoke("createDeck", deck=deck_name)

    async def get_deck_names(self) -> list[str]:
        """Get list of all deck names.

        Returns:
            List of deck names

        Raises:
            RuntimeError: If retrieval fails
        """
        result = await self._invoke("deckNames")
        if result is None:
            return []
        # AnkiConnect returns a list of strings for deckNames
        return list(result)
