"""Contract tests for Database interface.

These tests verify the Database class implements the expected
interface for storage operations.
"""

import inspect
import tempfile
from pathlib import Path
from typing import get_type_hints

import pytest

from ankification.cards.models import BasicCard, Card, CardStatus, ClozeCard
from ankification.storage.database import Database


class TestDatabaseInterfaceContract:
    """Contract tests for Database interface methods."""

    def test_database_has_connect_method(self) -> None:
        """Database should have a connect method."""
        assert hasattr(Database, "connect")
        assert inspect.iscoroutinefunction(Database.connect)

    def test_database_has_close_method(self) -> None:
        """Database should have a close method."""
        assert hasattr(Database, "close")
        assert inspect.iscoroutinefunction(Database.close)

    def test_database_has_save_card_method(self) -> None:
        """Database should have a save_card method."""
        assert hasattr(Database, "save_card")
        assert inspect.iscoroutinefunction(Database.save_card)

    def test_database_has_get_card_method(self) -> None:
        """Database should have a get_card method."""
        assert hasattr(Database, "get_card")
        assert inspect.iscoroutinefunction(Database.get_card)

    def test_database_has_get_all_cards_method(self) -> None:
        """Database should have a get_all_cards method."""
        assert hasattr(Database, "get_all_cards")
        assert inspect.iscoroutinefunction(Database.get_all_cards)

    def test_database_has_get_cards_by_status_method(self) -> None:
        """Database should have a get_cards_by_status method."""
        assert hasattr(Database, "get_cards_by_status")
        assert inspect.iscoroutinefunction(Database.get_cards_by_status)

    def test_database_has_delete_card_method(self) -> None:
        """Database should have a delete_card method."""
        assert hasattr(Database, "delete_card")
        assert inspect.iscoroutinefunction(Database.delete_card)

    def test_database_has_create_session_method(self) -> None:
        """Database should have a create_session method."""
        assert hasattr(Database, "create_session")
        assert inspect.iscoroutinefunction(Database.create_session)

    def test_database_has_add_card_to_session_method(self) -> None:
        """Database should have an add_card_to_session method."""
        assert hasattr(Database, "add_card_to_session")
        assert inspect.iscoroutinefunction(Database.add_card_to_session)

    def test_database_has_complete_session_method(self) -> None:
        """Database should have a complete_session method."""
        assert hasattr(Database, "complete_session")
        assert inspect.iscoroutinefunction(Database.complete_session)

    def test_database_has_get_sessions_method(self) -> None:
        """Database should have a get_sessions method."""
        assert hasattr(Database, "get_sessions")
        assert inspect.iscoroutinefunction(Database.get_sessions)


class TestDatabaseMethodSignatures:
    """Contract tests for method signature correctness."""

    def test_save_card_signature(self) -> None:
        """save_card should accept a Card parameter."""
        sig = inspect.signature(Database.save_card)
        params = list(sig.parameters.keys())
        assert "card" in params

    def test_get_card_signature(self) -> None:
        """get_card should accept a card_id parameter."""
        sig = inspect.signature(Database.get_card)
        params = list(sig.parameters.keys())
        assert "card_id" in params

    def test_get_cards_by_status_signature(self) -> None:
        """get_cards_by_status should accept a status parameter."""
        sig = inspect.signature(Database.get_cards_by_status)
        params = list(sig.parameters.keys())
        assert "status" in params

    def test_delete_card_signature(self) -> None:
        """delete_card should accept a card_id parameter."""
        sig = inspect.signature(Database.delete_card)
        params = list(sig.parameters.keys())
        assert "card_id" in params

    def test_create_session_signature(self) -> None:
        """create_session should accept required session parameters."""
        sig = inspect.signature(Database.create_session)
        params = list(sig.parameters.keys())
        assert "sources" in params
        assert "provider" in params
        assert "card_types" in params
        assert "count_guidance" in params

    def test_add_card_to_session_signature(self) -> None:
        """add_card_to_session should accept session_id and card_id."""
        sig = inspect.signature(Database.add_card_to_session)
        params = list(sig.parameters.keys())
        assert "session_id" in params
        assert "card_id" in params


class TestDatabaseContextManagerContract:
    """Contract tests for Database context manager support."""

    def test_database_supports_async_context_manager(self) -> None:
        """Database should support async context manager protocol."""
        assert hasattr(Database, "__aenter__")
        assert hasattr(Database, "__aexit__")
        assert inspect.iscoroutinefunction(Database.__aenter__)
        assert inspect.iscoroutinefunction(Database.__aexit__)


class TestDatabaseInitializationContract:
    """Contract tests for Database initialization."""

    def test_database_accepts_path(self) -> None:
        """Database should accept a path in __init__."""
        sig = inspect.signature(Database.__init__)
        params = list(sig.parameters.keys())
        assert "db_path" in params

    def test_database_can_be_instantiated_with_path(self) -> None:
        """Database can be instantiated with a Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            assert db is not None

    def test_database_can_be_instantiated_with_string(self) -> None:
        """Database can be instantiated with a string path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test.db"
            db = Database(db_path)
            assert db is not None


class TestDatabaseOperationContracts:
    """Contract tests for actual database operations."""

    @pytest.fixture
    async def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            await db.connect()
            yield db
            await db.close()

    async def test_save_card_accepts_basic_card(self, db: Database) -> None:
        """save_card should accept BasicCard."""
        card = BasicCard(front="Q", back="A", source="test.txt")
        # Should not raise
        await db.save_card(card)

    async def test_save_card_accepts_cloze_card(self, db: Database) -> None:
        """save_card should accept ClozeCard."""
        card = ClozeCard(text="{{c1::answer}}", source="test.txt")
        await db.save_card(card)

    async def test_get_card_returns_card_or_none(self, db: Database) -> None:
        """get_card should return Card or None."""
        result = await db.get_card("nonexistent-id")
        assert result is None

        card = BasicCard(front="Q", back="A", source="test.txt")
        await db.save_card(card)
        result = await db.get_card(card.id)
        assert isinstance(result, Card)

    async def test_get_all_cards_returns_list(self, db: Database) -> None:
        """get_all_cards should return a list."""
        result = await db.get_all_cards()
        assert isinstance(result, list)

    async def test_get_cards_by_status_returns_list(self, db: Database) -> None:
        """get_cards_by_status should return a list."""
        result = await db.get_cards_by_status(CardStatus.DRAFT)
        assert isinstance(result, list)

    async def test_create_session_returns_string_id(self, db: Database) -> None:
        """create_session should return a string session ID."""
        session_id = await db.create_session(
            sources=["test.txt"],
            provider="openai",
            card_types=["basic"],
            count_guidance="5-10",
        )
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    async def test_get_sessions_returns_list(self, db: Database) -> None:
        """get_sessions should return a list."""
        result = await db.get_sessions()
        assert isinstance(result, list)
