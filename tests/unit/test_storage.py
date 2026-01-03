"""Unit tests for storage layer."""

import json

import pytest
import pytest_asyncio

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.storage.database import Database


class TestDatabase:
    """Tests for Database."""

    @pytest_asyncio.fixture
    async def db(self, temp_dir):
        """Create and connect to test database."""
        db_path = temp_dir / "test.db"
        database = Database(db_path)
        await database.connect()
        yield database
        await database.close()

    @pytest.fixture
    def sample_basic_card(self):
        """Create a sample basic card."""
        return BasicCard(
            front="What is Python?",
            back="A programming language",
            source="test.txt",
            tags=["programming", "python"],
        )

    @pytest.fixture
    def sample_cloze_card(self):
        """Create a sample cloze card."""
        return ClozeCard(
            text="The capital of {{c1::France}} is {{c2::Paris}}.",
            source="test.txt",
            tags=["geography"],
        )

    @pytest.mark.asyncio
    async def test_database_connection(self, db):
        """Test database connects successfully."""
        assert db._connection is not None

    @pytest.mark.asyncio
    async def test_save_basic_card(self, db, sample_basic_card):
        """Test saving a basic card."""
        await db.save_card(sample_basic_card)

        # Retrieve and verify
        retrieved = await db.get_card(sample_basic_card.id)
        assert retrieved is not None
        assert retrieved.front == sample_basic_card.front
        assert retrieved.back == sample_basic_card.back
        assert set(retrieved.tags) == set(sample_basic_card.tags)

    @pytest.mark.asyncio
    async def test_save_cloze_card(self, db, sample_cloze_card):
        """Test saving a cloze card."""
        await db.save_card(sample_cloze_card)

        retrieved = await db.get_card(sample_cloze_card.id)
        assert retrieved is not None
        assert isinstance(retrieved, ClozeCard)
        assert retrieved.text == sample_cloze_card.text

    @pytest.mark.asyncio
    async def test_update_card(self, db, sample_basic_card):
        """Test updating an existing card."""
        await db.save_card(sample_basic_card)

        # Update card
        sample_basic_card.front = "Updated question"
        sample_basic_card.status = CardStatus.ACCEPTED
        await db.save_card(sample_basic_card)

        # Verify update
        retrieved = await db.get_card(sample_basic_card.id)
        assert retrieved.front == "Updated question"
        assert retrieved.status == CardStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_get_nonexistent_card(self, db):
        """Test getting a card that doesn't exist."""
        result = await db.get_card("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_card(self, db, sample_basic_card):
        """Test deleting a card."""
        await db.save_card(sample_basic_card)
        await db.delete_card(sample_basic_card.id)

        result = await db.get_card(sample_basic_card.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cards_by_status(self, db, sample_basic_card, sample_cloze_card):
        """Test getting cards by status."""
        # Save cards with different statuses
        sample_basic_card.status = CardStatus.ACCEPTED
        sample_cloze_card.status = CardStatus.DRAFT

        await db.save_card(sample_basic_card)
        await db.save_card(sample_cloze_card)

        # Query by status
        accepted = await db.get_cards_by_status(CardStatus.ACCEPTED)
        draft = await db.get_cards_by_status(CardStatus.DRAFT)

        assert len(accepted) == 1
        assert len(draft) == 1
        assert accepted[0].id == sample_basic_card.id
        assert draft[0].id == sample_cloze_card.id

    @pytest.mark.asyncio
    async def test_create_session(self, db):
        """Test creating a session."""
        sources = ["file1.txt", "file2.txt"]
        session_id = await db.create_session(sources)

        assert isinstance(session_id, str)
        assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_add_card_to_session(self, db, sample_basic_card):
        """Test adding a card to a session."""
        # Create session and card
        session_id = await db.create_session(["test.txt"])
        await db.save_card(sample_basic_card)

        # Add card to session
        await db.add_card_to_session(session_id, sample_basic_card.id)

        # Retrieve cards in session
        cards = await db.get_cards_by_session(session_id)
        assert len(cards) == 1
        assert cards[0].id == sample_basic_card.id

    @pytest.mark.asyncio
    async def test_complete_session(self, db):
        """Test marking a session as completed."""
        session_id = await db.create_session(["test.txt"])
        await db.complete_session(session_id)

        sessions = await db.get_sessions()
        assert len(sessions) == 1
        assert sessions[0]["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_get_sessions(self, db):
        """Test getting recent sessions."""
        # Create multiple sessions
        await db.create_session(["file1.txt"])
        await db.create_session(["file2.txt"])
        await db.create_session(["file3.txt"])

        sessions = await db.get_sessions(limit=2)
        assert len(sessions) == 2

        # Verify session data
        assert "sources" in sessions[0]
        assert "created_at" in sessions[0]
        assert isinstance(sessions[0]["sources"], list)

    @pytest.mark.asyncio
    async def test_record_edit(self, db, sample_basic_card):
        """Test recording edit history."""
        await db.save_card(sample_basic_card)

        old_content = sample_basic_card.to_json()
        sample_basic_card.front = "Updated"
        new_content = sample_basic_card.to_json()

        await db.record_edit(
            sample_basic_card.id,
            old_content,
            new_content,
            "manual",
            feedback=None,
        )

        history = await db.get_edit_history(sample_basic_card.id)
        assert len(history) == 1
        assert history[0]["edit_type"] == "manual"

    @pytest.mark.asyncio
    async def test_record_llm_edit(self, db, sample_basic_card):
        """Test recording LLM refinement in history."""
        await db.save_card(sample_basic_card)

        old_content = sample_basic_card.to_json()
        sample_basic_card.front = "Refined question"
        new_content = sample_basic_card.to_json()

        await db.record_edit(
            sample_basic_card.id,
            old_content,
            new_content,
            "llm_refine",
            feedback="make it shorter",
        )

        history = await db.get_edit_history(sample_basic_card.id)
        assert len(history) == 1
        assert history[0]["edit_type"] == "llm_refine"
        assert history[0]["feedback"] == "make it shorter"

    @pytest.mark.asyncio
    async def test_get_card_count_by_status(self, db, sample_basic_card):
        """Test getting card counts by status."""
        # Create cards with different statuses
        card1 = sample_basic_card
        card1.status = CardStatus.ACCEPTED

        card2 = BasicCard(front="Q2", back="A2", source="test.txt")
        card2.status = CardStatus.DRAFT

        card3 = BasicCard(front="Q3", back="A3", source="test.txt")
        card3.status = CardStatus.ACCEPTED

        await db.save_card(card1)
        await db.save_card(card2)
        await db.save_card(card3)

        counts = await db.get_card_count_by_status()
        assert counts[CardStatus.ACCEPTED.value] == 2
        assert counts[CardStatus.DRAFT.value] == 1

    @pytest.mark.asyncio
    async def test_search_cards_by_tag(self, db):
        """Test searching cards by tag."""
        # Create cards with different tags
        card1 = BasicCard(
            front="Q1", back="A1", source="test.txt", tags=["python", "programming"]
        )
        card2 = BasicCard(
            front="Q2", back="A2", source="test.txt", tags=["javascript", "programming"]
        )
        card3 = BasicCard(front="Q3", back="A3", source="test.txt", tags=["python"])

        await db.save_card(card1)
        await db.save_card(card2)
        await db.save_card(card3)

        # Search by tag
        python_cards = await db.search_cards_by_tag("python")
        programming_cards = await db.search_cards_by_tag("programming")

        assert len(python_cards) == 2
        assert len(programming_cards) == 2

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_dir):
        """Test using database as context manager."""
        db_path = temp_dir / "test.db"

        async with Database(db_path) as db:
            card = BasicCard(front="Q", back="A", source="test.txt")
            await db.save_card(card)

            retrieved = await db.get_card(card.id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_operations_without_connection_raise(self, temp_dir):
        """Test that operations without connection raise error."""
        db_path = temp_dir / "test.db"
        db = Database(db_path)

        card = BasicCard(front="Q", back="A", source="test.txt")

        with pytest.raises(RuntimeError, match="not connected"):
            await db.save_card(card)
