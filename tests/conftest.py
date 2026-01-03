"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.config import Config
from ankification.config.manager import ConfigManager
from ankification.storage.database import Database

# Import modular fixtures - makes them available to all tests
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.cards",
    "tests.fixtures.config",
    "tests.fixtures.mocks",
]


# === Pytest Hooks ===


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    # Markers are defined in pyproject.toml


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-apply markers based on test file location."""
    for item in items:
        path_str = str(item.fspath)
        if "/unit/" in path_str:
            item.add_marker(pytest.mark.unit)
        elif "/property/" in path_str:
            item.add_marker(pytest.mark.property)
        elif "/contract/" in path_str:
            item.add_marker(pytest.mark.contract)
        elif "/integration/" in path_str:
            item.add_marker(pytest.mark.integration)
        elif "/web/" in path_str:
            item.add_marker(pytest.mark.web)
        elif "/cli/" in path_str:
            item.add_marker(pytest.mark.cli)
        elif "/tui/" in path_str:
            item.add_marker(pytest.mark.tui)
        elif "/e2e/" in path_str:
            item.add_marker(pytest.mark.e2e)


# === Directory Fixtures ===


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Get a temporary database path."""
    return temp_dir / "test.db"


# === Database Fixtures ===


@pytest_asyncio.fixture
async def db(temp_db_path: Path) -> AsyncGenerator[Database, None]:
    """Create and connect to test database."""
    database = Database(temp_db_path)
    await database.connect()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def db_with_cards(db: Database) -> Database:
    """Database pre-populated with sample cards."""
    # Add various basic cards
    basic_cards = [
        BasicCard(
            front=f"Question {i}",
            back=f"Answer {i}",
            source="test.txt",
            tags=["test", f"card{i}"],
        )
        for i in range(5)
    ]

    # Add some with different statuses
    basic_cards[0].status = CardStatus.ACCEPTED
    basic_cards[1].status = CardStatus.ACCEPTED
    basic_cards[2].status = CardStatus.REJECTED

    for card in basic_cards:
        await db.save_card(card)

    # Add cloze cards
    cloze_cards = [
        ClozeCard(
            text=f"The answer is {{{{c1::value{i}}}}}.",
            source="test.txt",
            tags=["cloze", f"card{i}"],
        )
        for i in range(3)
    ]

    for card in cloze_cards:
        await db.save_card(card)

    return db


@pytest_asyncio.fixture
async def db_with_session(db: Database) -> tuple[Database, str]:
    """Database with a session and cards."""
    session_id = await db.create_session(
        sources=["test.txt", "sample.md"],
        provider="openai",
        card_types=["basic", "cloze"],
        count_guidance="5-10",
    )

    # Add cards to session
    for i in range(3):
        card = BasicCard(
            front=f"Session Question {i}",
            back=f"Session Answer {i}",
            source="test.txt",
        )
        await db.save_card(card)
        await db.add_card_to_session(session_id, card.id)

    return db, session_id


# === Config Fixtures ===


@pytest.fixture
def config() -> Config:
    """Default test configuration."""
    return Config()


@pytest.fixture
def config_with_temp_storage(temp_dir: Path) -> Config:
    """Config with temp database path."""
    cfg = Config()
    cfg.storage.database_path = str(temp_dir / "test.db")
    cfg.export.csv.output_dir = str(temp_dir / "export")
    return cfg


@pytest.fixture
def config_manager(temp_dir: Path) -> ConfigManager:
    """ConfigManager with temp config file."""
    config_path = temp_dir / "config.yaml"
    return ConfigManager(config_path=config_path)


# === Card Fixtures ===


@pytest.fixture
def basic_card() -> BasicCard:
    """Sample basic card."""
    return BasicCard(
        front="What is Python?",
        back="A high-level programming language.",
        source="test.txt",
        tags=["programming", "python"],
    )


@pytest.fixture
def cloze_card() -> ClozeCard:
    """Sample cloze card."""
    return ClozeCard(
        text="Python was created by {{c1::Guido van Rossum}}.",
        source="test.txt",
        tags=["programming", "python"],
    )


@pytest.fixture
def accepted_basic_card() -> BasicCard:
    """Basic card with accepted status."""
    return BasicCard(
        front="Accepted question",
        back="Accepted answer",
        source="test.txt",
        status=CardStatus.ACCEPTED,
    )


@pytest.fixture
def rejected_basic_card() -> BasicCard:
    """Basic card with rejected status."""
    return BasicCard(
        front="Rejected question",
        back="Rejected answer",
        source="test.txt",
        status=CardStatus.REJECTED,
    )


@pytest.fixture
def card_batch() -> list[BasicCard | ClozeCard]:
    """Batch of mixed cards with various statuses."""
    cards: list[BasicCard | ClozeCard] = [
        BasicCard(front="Q1", back="A1", source="test.txt", status=CardStatus.DRAFT),
        BasicCard(front="Q2", back="A2", source="test.txt", status=CardStatus.ACCEPTED),
        BasicCard(front="Q3", back="A3", source="test.txt", status=CardStatus.REJECTED),
        ClozeCard(text="{{c1::Cloze1}}", source="test.txt", status=CardStatus.DRAFT),
        ClozeCard(text="{{c1::Cloze2}}", source="test.txt", status=CardStatus.ACCEPTED),
    ]
    return cards


# === File Fixtures ===


@pytest.fixture
def sample_text_file(temp_dir: Path) -> Path:
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a sample text file.\nIt has multiple lines.")
    return file_path


@pytest.fixture
def sample_markdown_file(temp_dir: Path) -> Path:
    """Create a sample markdown file."""
    file_path = temp_dir / "sample.md"
    content = """# Sample Markdown

This is a **markdown** file with _formatting_.

## Section 1
Some content here.

## Section 2
More content.
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def empty_file(temp_dir: Path) -> Path:
    """Create an empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.write_text("")
    return file_path


@pytest.fixture
def sample_html() -> str:
    """Sample HTML content."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <script>console.log('test');</script>
        <style>body { color: black; }</style>
    </head>
    <body>
        <h1>Main Title</h1>
        <p>This is a paragraph.</p>
        <p>Another paragraph with <strong>bold text</strong>.</p>
        <div>Some content in a div.</div>
    </body>
    </html>
    """


@pytest.fixture
def sample_content() -> str:
    """Sample content for card generation."""
    return """
    Introduction to Python Programming

    Python is a high-level, interpreted programming language known for its
    simplicity and readability. It was created by Guido van Rossum and first
    released in 1991.

    Key Features:
    - Easy to learn and use
    - Extensive standard library
    - Cross-platform compatibility
    - Large community support

    Python is widely used in web development, data science, artificial
    intelligence, and automation.
    """
