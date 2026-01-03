"""Database fixtures for testing."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.storage.database import Database


@pytest.fixture
def temp_db_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for database files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_db_dir: Path) -> Path:
    """Get a temporary database path."""
    return temp_db_dir / "test.db"


@pytest_asyncio.fixture
async def empty_db(temp_db_path: Path) -> AsyncGenerator[Database, None]:
    """Create an empty test database."""
    database = Database(temp_db_path)
    await database.connect()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def db_with_basic_cards(empty_db: Database) -> Database:
    """Database with basic cards only."""
    cards = [
        BasicCard(
            front=f"Basic Question {i}",
            back=f"Basic Answer {i}",
            source="basic_test.txt",
            tags=["basic", f"item{i}"],
            status=CardStatus.DRAFT,
        )
        for i in range(10)
    ]

    # Set various statuses
    cards[0].status = CardStatus.ACCEPTED
    cards[1].status = CardStatus.ACCEPTED
    cards[2].status = CardStatus.ACCEPTED
    cards[3].status = CardStatus.REJECTED
    cards[4].status = CardStatus.REJECTED

    for card in cards:
        await empty_db.save_card(card)

    return empty_db


@pytest_asyncio.fixture
async def db_with_cloze_cards(empty_db: Database) -> Database:
    """Database with cloze cards only."""
    cards = [
        ClozeCard(
            text=f"The {{{{c1::answer{i}}}}} is correct.",
            source="cloze_test.txt",
            tags=["cloze", f"item{i}"],
            status=CardStatus.DRAFT,
        )
        for i in range(10)
    ]

    # Set various statuses
    cards[0].status = CardStatus.ACCEPTED
    cards[1].status = CardStatus.ACCEPTED
    cards[2].status = CardStatus.REJECTED

    for card in cards:
        await empty_db.save_card(card)

    return empty_db


@pytest_asyncio.fixture
async def db_with_mixed_cards(empty_db: Database) -> Database:
    """Database with both basic and cloze cards."""
    basic_cards = [
        BasicCard(
            front=f"Question {i}",
            back=f"Answer {i}",
            source="mixed_test.txt",
            tags=["mixed", "basic"],
        )
        for i in range(5)
    ]

    cloze_cards = [
        ClozeCard(
            text=f"{{{{c1::Cloze{i}}}}} is the answer.",
            source="mixed_test.txt",
            tags=["mixed", "cloze"],
        )
        for i in range(5)
    ]

    # Set statuses
    basic_cards[0].status = CardStatus.ACCEPTED
    basic_cards[1].status = CardStatus.REJECTED
    cloze_cards[0].status = CardStatus.ACCEPTED

    for card in basic_cards + cloze_cards:
        await empty_db.save_card(card)

    return empty_db


@pytest_asyncio.fixture
async def db_with_multiple_sessions(empty_db: Database) -> tuple[Database, list[str]]:
    """Database with multiple sessions and cards."""
    session_ids = []

    # Create first session
    session1_id = await empty_db.create_session(
        sources=["source1.txt"],
        provider="openai",
        card_types=["basic"],
        count_guidance="5-10",
    )
    session_ids.append(session1_id)

    for i in range(3):
        card = BasicCard(
            front=f"Session1 Q{i}",
            back=f"Session1 A{i}",
            source="source1.txt",
        )
        await empty_db.save_card(card)
        await empty_db.add_card_to_session(session1_id, card.id)

    await empty_db.complete_session(session1_id)

    # Create second session
    session2_id = await empty_db.create_session(
        sources=["source2.txt", "source3.txt"],
        provider="anthropic",
        card_types=["basic", "cloze"],
        count_guidance="10-15",
    )
    session_ids.append(session2_id)

    for i in range(2):
        card = BasicCard(
            front=f"Session2 Q{i}",
            back=f"Session2 A{i}",
            source="source2.txt",
        )
        await empty_db.save_card(card)
        await empty_db.add_card_to_session(session2_id, card.id)

    # Leave second session incomplete

    return empty_db, session_ids


@pytest_asyncio.fixture
async def db_with_tags(empty_db: Database) -> Database:
    """Database with cards having various tags for tag filtering tests."""
    tag_configs = [
        (["python", "programming"], CardStatus.ACCEPTED),
        (["python", "basics"], CardStatus.DRAFT),
        (["javascript", "programming"], CardStatus.ACCEPTED),
        (["javascript", "web"], CardStatus.REJECTED),
        (["rust", "programming", "systems"], CardStatus.DRAFT),
        ([], CardStatus.DRAFT),  # Card with no tags
    ]

    for i, (tags, status) in enumerate(tag_configs):
        card = BasicCard(
            front=f"Tag test Q{i}",
            back=f"Tag test A{i}",
            source="tags_test.txt",
            tags=tags,
            status=status,
        )
        await empty_db.save_card(card)

    return empty_db
