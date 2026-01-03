"""Property-based tests for database operations."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.storage.database import Database

from .strategies import (
    any_card_strategy,
    basic_card_strategy,
    card_status,
    cloze_card_strategy,
    session_params_strategy,
    tag_list,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


class TestDatabaseSaveGetRoundtrip:
    """Property tests for database save/get operations."""

    @given(basic_card_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_basic_card_roundtrip(self, card: BasicCard) -> None:
        """Saving and retrieving a BasicCard preserves all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                await db.save_card(card)
                retrieved = await db.get_card(card.id)

                assert retrieved is not None
                assert retrieved.id == card.id
                assert retrieved.type == CardType.BASIC
                assert retrieved.front == card.front
                assert retrieved.back == card.back
                assert retrieved.source == card.source
                assert retrieved.tags == card.tags
                assert retrieved.status == card.status
            finally:
                await db.close()

    @given(cloze_card_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_cloze_card_roundtrip(self, card: ClozeCard) -> None:
        """Saving and retrieving a ClozeCard preserves all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                await db.save_card(card)
                retrieved = await db.get_card(card.id)

                assert retrieved is not None
                assert retrieved.id == card.id
                assert retrieved.type == CardType.CLOZE
                assert retrieved.text == card.text
                assert retrieved.source == card.source
                assert retrieved.tags == card.tags
                assert retrieved.status == card.status
            finally:
                await db.close()

    @given(any_card_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_card_id_stable_after_save(self, card: BasicCard | ClozeCard) -> None:
        """Card ID doesn't change after saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                original_id = card.id
                await db.save_card(card)

                assert card.id == original_id
            finally:
                await db.close()


class TestDatabaseTagOperations:
    """Property tests for tag-related database operations."""

    @given(tags=tag_list)
    @settings(max_examples=30, deadline=None)
    async def test_tags_preserved_in_database(self, tags: list[str]) -> None:
        """Tags are preserved when saving and retrieving cards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                card = BasicCard(front="Q", back="A", source="test.txt", tags=tags)
                await db.save_card(card)
                retrieved = await db.get_card(card.id)

                assert retrieved is not None
                assert retrieved.tags == tags
            finally:
                await db.close()


class TestDatabaseStatusOperations:
    """Property tests for status-related database operations."""

    @given(status=card_status)
    @settings(max_examples=10, deadline=None)
    async def test_status_preserved_in_database(self, status: CardStatus) -> None:
        """Card status is preserved when saving and retrieving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                card = BasicCard(front="Q", back="A", source="test.txt", status=status)
                await db.save_card(card)
                retrieved = await db.get_card(card.id)

                assert retrieved is not None
                assert retrieved.status == status
            finally:
                await db.close()

    @given(initial=card_status, updated=card_status)
    @settings(max_examples=20, deadline=None)
    async def test_status_update_works(
        self, initial: CardStatus, updated: CardStatus
    ) -> None:
        """Card status can be updated in database via save_card."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                card = BasicCard(front="Q", back="A", source="test.txt", status=initial)
                await db.save_card(card)

                card.status = updated
                await db.save_card(card)  # save_card handles both insert and update

                retrieved = await db.get_card(card.id)
                assert retrieved is not None
                assert retrieved.status == updated
            finally:
                await db.close()


class TestDatabaseCardListing:
    """Property tests for card listing operations."""

    @given(st.lists(basic_card_strategy(), min_size=0, max_size=10))
    @settings(max_examples=20, deadline=None)
    async def test_get_all_returns_all_saved(self, cards: list[BasicCard]) -> None:
        """get_all_cards returns all saved cards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                for card in cards:
                    await db.save_card(card)

                all_cards = await db.get_all_cards()

                # Check all our cards are there
                saved_ids = {c.id for c in cards}
                retrieved_ids = {c.id for c in all_cards}

                assert saved_ids == retrieved_ids
            finally:
                await db.close()


class TestDatabaseSessionProperties:
    """Property tests for session operations."""

    @given(session_params_strategy())
    @settings(max_examples=20, deadline=None)
    async def test_session_creation_returns_id(self, params: dict) -> None:
        """Creating a session returns a valid session ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                session_id = await db.create_session(**params)

                assert session_id is not None
                assert isinstance(session_id, str)
                assert len(session_id) > 0
            finally:
                await db.close()

    @given(session_params_strategy())
    @settings(max_examples=20, deadline=None)
    async def test_session_ids_unique(self, params: dict) -> None:
        """Each session gets a unique ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()

            try:
                session1 = await db.create_session(**params)
                session2 = await db.create_session(**params)

                assert session1 != session2
            finally:
                await db.close()


# Import CardType for tests
from ankification.cards.models import CardType
