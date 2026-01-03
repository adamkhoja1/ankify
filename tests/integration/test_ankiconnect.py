"""Integration tests for AnkiConnect export.

These tests require Anki to be running with AnkiConnect addon installed.
Tests will fail if AnkiConnect is not available - this is intentional.

Prerequisites:
1. Anki must be running
2. AnkiConnect addon must be installed (code: 2055492159)
3. AnkiConnect must be listening on localhost:8765

Run with: pytest tests/integration/test_ankiconnect.py -v
"""

import pytest

from ankification.cards.models import BasicCard, ClozeCard
from ankification.export.anki_connect import AnkiConnectExporter


@pytest.mark.integration
class TestAnkiConnectExporterReal:
    """Integration tests for AnkiConnect exporter with real Anki.

    Requires: Anki running with AnkiConnect addon
    """

    @pytest.fixture
    def exporter(self) -> AnkiConnectExporter:
        """Create real AnkiConnect exporter."""
        return AnkiConnectExporter()

    async def test_connection(self, exporter: AnkiConnectExporter) -> None:
        """Should successfully connect to AnkiConnect."""
        connected = await exporter.test_connection()
        assert connected is True

    async def test_get_deck_names(self, exporter: AnkiConnectExporter) -> None:
        """Should retrieve deck names from Anki."""
        decks = await exporter.get_deck_names()

        assert isinstance(decks, list)
        # Default deck always exists
        assert "Default" in decks

    async def test_get_model_names(self, exporter: AnkiConnectExporter) -> None:
        """Should retrieve note type names from Anki."""
        models = await exporter.get_model_names()

        assert isinstance(models, list)
        # Basic note type usually exists
        assert len(models) > 0

    async def test_create_deck(self, exporter: AnkiConnectExporter) -> None:
        """Should create a new deck in Anki."""
        deck_name = "Ankification_Test_Deck_12345"

        # Create deck
        await exporter.create_deck(deck_name)

        # Verify it exists
        decks = await exporter.get_deck_names()
        assert deck_name in decks

        # Cleanup - delete the test deck
        await exporter.delete_deck(deck_name)

    async def test_export_basic_card(self, exporter: AnkiConnectExporter) -> None:
        """Should export a basic card to Anki."""
        test_deck = "Ankification_Test_Basic"
        await exporter.create_deck(test_deck)

        card = BasicCard(
            front="Test Question from Ankification?",
            back="Test Answer from Ankification",
            source="integration_test",
            tags=["ankification", "test"],
        )

        try:
            note_id = await exporter.export_card(card, deck=test_deck)

            assert note_id is not None
            assert isinstance(note_id, int)

            # Verify the note was created
            note_info = await exporter.get_note_info(note_id)
            assert note_info is not None

        finally:
            # Cleanup
            await exporter.delete_deck(test_deck, cards_too=True)

    async def test_export_cloze_card(self, exporter: AnkiConnectExporter) -> None:
        """Should export a cloze card to Anki."""
        test_deck = "Ankification_Test_Cloze"
        await exporter.create_deck(test_deck)

        card = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the {{c2::cell}}.",
            source="integration_test",
            tags=["ankification", "test", "biology"],
        )

        try:
            note_id = await exporter.export_card(card, deck=test_deck)

            assert note_id is not None
            assert isinstance(note_id, int)

        finally:
            await exporter.delete_deck(test_deck, cards_too=True)

    async def test_export_multiple_cards(self, exporter: AnkiConnectExporter) -> None:
        """Should export multiple cards to Anki."""
        test_deck = "Ankification_Test_Batch"
        await exporter.create_deck(test_deck)

        cards = [
            BasicCard(front=f"Q{i}", back=f"A{i}", source="test", tags=["batch"])
            for i in range(3)
        ]

        try:
            results = await exporter.export_cards(cards, deck=test_deck)

            assert len(results) == 3
            assert all(r["success"] for r in results)
            assert all(r["note_id"] is not None for r in results)

        finally:
            await exporter.delete_deck(test_deck, cards_too=True)

    async def test_export_with_tags(self, exporter: AnkiConnectExporter) -> None:
        """Should preserve tags when exporting to Anki."""
        test_deck = "Ankification_Test_Tags"
        await exporter.create_deck(test_deck)

        card = BasicCard(
            front="Tagged Question?",
            back="Tagged Answer",
            source="test",
            tags=["python", "programming", "test"],
        )

        try:
            note_id = await exporter.export_card(card, deck=test_deck)
            note_info = await exporter.get_note_info(note_id)

            # Verify tags were applied
            assert "python" in note_info["tags"]
            assert "programming" in note_info["tags"]

        finally:
            await exporter.delete_deck(test_deck, cards_too=True)


@pytest.mark.integration
class TestAnkiConnectErrorHandling:
    """Tests for AnkiConnect error handling.

    Requires: Anki running with AnkiConnect addon
    """

    @pytest.fixture
    def exporter(self) -> AnkiConnectExporter:
        """Create AnkiConnect exporter."""
        return AnkiConnectExporter()

    async def test_export_to_nonexistent_deck_creates_it(
        self, exporter: AnkiConnectExporter
    ) -> None:
        """Exporting to non-existent deck should create it."""
        deck_name = "Ankification_Auto_Create_Test"

        # Ensure deck doesn't exist
        decks = await exporter.get_deck_names()
        if deck_name in decks:
            await exporter.delete_deck(deck_name, cards_too=True)

        card = BasicCard(front="Q", back="A", source="test")

        try:
            await exporter.export_card(card, deck=deck_name)

            # Deck should now exist
            decks = await exporter.get_deck_names()
            assert deck_name in decks

        finally:
            await exporter.delete_deck(deck_name, cards_too=True)

    async def test_duplicate_card_handling(
        self, exporter: AnkiConnectExporter
    ) -> None:
        """Should handle duplicate cards appropriately."""
        test_deck = "Ankification_Test_Duplicates"
        await exporter.create_deck(test_deck)

        card = BasicCard(
            front="Duplicate Question?",
            back="Answer",
            source="test",
        )

        try:
            # Export same card twice
            note_id_1 = await exporter.export_card(card, deck=test_deck)
            # Second export might update or skip depending on implementation
            note_id_2 = await exporter.export_card(card, deck=test_deck)

            # Both should succeed (either same note updated or duplicate allowed)
            assert note_id_1 is not None

        finally:
            await exporter.delete_deck(test_deck, cards_too=True)
