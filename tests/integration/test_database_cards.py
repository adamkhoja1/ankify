"""Integration tests for Database + Card model interactions.

Tests the data flow between card models and database storage.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.storage.database import Database


class TestDatabaseCardRoundtrip:
    """Integration tests for card save/retrieve operations."""

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    async def test_basic_card_roundtrip_preserves_all_fields(
        self, db: Database
    ) -> None:
        """BasicCard should survive database roundtrip with all fields intact."""
        original = BasicCard(
            front="What is Python?",
            back="A programming language",
            source="python.txt",
            tags=["programming", "python"],
            status=CardStatus.ACCEPTED,
        )

        await db.save_card(original)
        retrieved = await db.get_card(original.id)

        assert retrieved is not None
        assert retrieved.id == original.id
        assert retrieved.type == CardType.BASIC
        assert retrieved.front == original.front
        assert retrieved.back == original.back
        assert retrieved.source == original.source
        assert retrieved.tags == original.tags
        assert retrieved.status == original.status

    async def test_cloze_card_roundtrip_preserves_all_fields(
        self, db: Database
    ) -> None:
        """ClozeCard should survive database roundtrip with all fields intact."""
        original = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of {{c2::the cell}}.",
            source="biology.txt",
            tags=["biology", "cells"],
            status=CardStatus.DRAFT,
        )

        await db.save_card(original)
        retrieved = await db.get_card(original.id)

        assert retrieved is not None
        assert retrieved.id == original.id
        assert retrieved.type == CardType.CLOZE
        assert retrieved.text == original.text
        assert retrieved.source == original.source
        assert retrieved.tags == original.tags
        assert retrieved.status == original.status

    async def test_card_id_persists_across_save(self, db: Database) -> None:
        """Card ID should not change when saved."""
        card = BasicCard(front="Q", back="A", source="test.txt")
        original_id = card.id

        await db.save_card(card)
        await db.save_card(card)  # Save again (update)

        retrieved = await db.get_card(original_id)
        assert retrieved is not None
        assert retrieved.id == original_id


class TestDatabaseStatusOperations:
    """Integration tests for status-based queries."""

    @pytest.fixture
    async def db_with_cards(self, temp_dir: Path) -> Database:
        """Create database with cards of various statuses."""
        db = Database(temp_dir / "test.db")
        await db.connect()

        # Create cards with different statuses
        cards = [
            BasicCard(front=f"Draft {i}", back=f"A{i}", source="test.txt", status=CardStatus.DRAFT)
            for i in range(3)
        ]
        cards.extend([
            BasicCard(front=f"Accepted {i}", back=f"A{i}", source="test.txt", status=CardStatus.ACCEPTED)
            for i in range(2)
        ])
        cards.append(
            BasicCard(front="Rejected", back="A", source="test.txt", status=CardStatus.REJECTED)
        )

        for card in cards:
            await db.save_card(card)

        yield db
        await db.close()

    async def test_get_cards_by_status_draft(self, db_with_cards: Database) -> None:
        """get_cards_by_status should return only draft cards."""
        drafts = await db_with_cards.get_cards_by_status(CardStatus.DRAFT)

        assert len(drafts) == 3
        assert all(c.status == CardStatus.DRAFT for c in drafts)

    async def test_get_cards_by_status_accepted(self, db_with_cards: Database) -> None:
        """get_cards_by_status should return only accepted cards."""
        accepted = await db_with_cards.get_cards_by_status(CardStatus.ACCEPTED)

        assert len(accepted) == 2
        assert all(c.status == CardStatus.ACCEPTED for c in accepted)

    async def test_get_cards_by_status_rejected(self, db_with_cards: Database) -> None:
        """get_cards_by_status should return only rejected cards."""
        rejected = await db_with_cards.get_cards_by_status(CardStatus.REJECTED)

        assert len(rejected) == 1
        assert rejected[0].status == CardStatus.REJECTED

    async def test_status_update_persists(self, db_with_cards: Database) -> None:
        """Status changes should persist in database."""
        drafts = await db_with_cards.get_cards_by_status(CardStatus.DRAFT)
        card = drafts[0]

        # Update status
        card.status = CardStatus.ACCEPTED
        await db_with_cards.save_card(card)

        # Verify change persisted
        retrieved = await db_with_cards.get_card(card.id)
        assert retrieved is not None
        assert retrieved.status == CardStatus.ACCEPTED


class TestDatabaseTagOperations:
    """Integration tests for tag-based queries."""

    @pytest.fixture
    async def db_with_tagged_cards(self, temp_dir: Path) -> Database:
        """Create database with tagged cards."""
        db = Database(temp_dir / "test.db")
        await db.connect()

        cards = [
            BasicCard(front="Python Q", back="A", source="test.txt", tags=["python", "programming"]),
            BasicCard(front="JS Q", back="A", source="test.txt", tags=["javascript", "programming"]),
            BasicCard(front="Math Q", back="A", source="test.txt", tags=["math"]),
            BasicCard(front="Both Q", back="A", source="test.txt", tags=["python", "math"]),
        ]

        for card in cards:
            await db.save_card(card)

        yield db
        await db.close()

    async def test_search_cards_by_tag_single(
        self, db_with_tagged_cards: Database
    ) -> None:
        """search_cards_by_tag should find cards with specific tag."""
        python_cards = await db_with_tagged_cards.search_cards_by_tag("python")

        assert len(python_cards) == 2
        assert all("python" in c.tags for c in python_cards)

    async def test_search_cards_by_tag_common(
        self, db_with_tagged_cards: Database
    ) -> None:
        """search_cards_by_tag should find all cards with common tag."""
        programming_cards = await db_with_tagged_cards.search_cards_by_tag("programming")

        assert len(programming_cards) == 2

    async def test_search_cards_by_tag_not_found(
        self, db_with_tagged_cards: Database
    ) -> None:
        """search_cards_by_tag should return empty for non-existent tag."""
        cards = await db_with_tagged_cards.search_cards_by_tag("nonexistent")

        assert len(cards) == 0


class TestDatabaseSessionIntegration:
    """Integration tests for session + card operations."""

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    async def test_session_card_association(self, db: Database) -> None:
        """Cards can be associated with sessions."""
        session_id = await db.create_session(
            sources=["test.txt"],
            provider="openai",
            card_types=["basic"],
            count_guidance="5-10",
        )

        card = BasicCard(front="Q", back="A", source="test.txt")
        await db.save_card(card)
        await db.add_card_to_session(session_id, card.id)

        session_cards = await db.get_cards_by_session(session_id)
        assert len(session_cards) == 1
        assert session_cards[0].id == card.id

    async def test_session_multiple_cards(self, db: Database) -> None:
        """Multiple cards can be associated with one session."""
        session_id = await db.create_session(
            sources=["test.txt"],
            provider="openai",
            card_types=["basic", "cloze"],
            count_guidance="10-15",
        )

        cards = [
            BasicCard(front=f"Q{i}", back=f"A{i}", source="test.txt")
            for i in range(5)
        ]

        for card in cards:
            await db.save_card(card)
            await db.add_card_to_session(session_id, card.id)

        session_cards = await db.get_cards_by_session(session_id)
        assert len(session_cards) == 5

    async def test_complete_session(self, db: Database) -> None:
        """Sessions can be marked as complete."""
        session_id = await db.create_session(
            sources=["test.txt"],
            provider="openai",
            card_types=["basic"],
            count_guidance="5-10",
        )

        await db.complete_session(session_id)

        sessions = await db.get_sessions()
        session = next((s for s in sessions if s["id"] == session_id), None)
        assert session is not None
        assert session["completed_at"] is not None


class TestDatabaseMixedCardTypes:
    """Integration tests for handling both BasicCard and ClozeCard."""

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    async def test_mixed_card_storage_and_retrieval(self, db: Database) -> None:
        """Both BasicCard and ClozeCard can be stored and retrieved."""
        basic = BasicCard(front="Q", back="A", source="test.txt")
        cloze = ClozeCard(text="{{c1::answer}}", source="test.txt")

        await db.save_card(basic)
        await db.save_card(cloze)

        all_cards = await db.get_all_cards()

        assert len(all_cards) == 2

        basic_retrieved = await db.get_card(basic.id)
        cloze_retrieved = await db.get_card(cloze.id)

        assert isinstance(basic_retrieved, BasicCard)
        assert isinstance(cloze_retrieved, ClozeCard)

    async def test_card_type_preserved_in_retrieval(self, db: Database) -> None:
        """Card type should be correctly preserved in database."""
        basic = BasicCard(front="Q", back="A", source="test.txt")
        cloze = ClozeCard(text="{{c1::answer}}", source="test.txt")

        await db.save_card(basic)
        await db.save_card(cloze)

        basic_retrieved = await db.get_card(basic.id)
        cloze_retrieved = await db.get_card(cloze.id)

        assert basic_retrieved.type == CardType.BASIC
        assert cloze_retrieved.type == CardType.CLOZE
