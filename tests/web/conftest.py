"""Web API test fixtures."""

import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.config import Config
from ankification.storage.database import Database
from ankification.web.app import create_app


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Get temporary database path for web tests."""
    return temp_dir / "web_test.db"


@pytest.fixture
def test_config(temp_db_path: Path, temp_dir: Path) -> Config:
    """Create test configuration."""
    cfg = Config()
    cfg.storage.database_path = str(temp_db_path)
    cfg.export.csv.output_dir = str(temp_dir / "export")
    return cfg


@pytest_asyncio.fixture
async def test_db(temp_db_path: Path) -> AsyncGenerator[Database, None]:
    """Create test database."""
    db = Database(temp_db_path)
    await db.connect()
    yield db
    await db.close()


@pytest.fixture
def app(test_config: Config, temp_db_path: Path, monkeypatch):
    """Create test FastAPI application with mocked config."""
    # Monkeypatch the get_config dependency to use test config
    from ankification.web import dependencies

    def mock_get_config():
        return test_config

    async def mock_get_db():
        db = Database(temp_db_path)
        await db.connect()
        try:
            yield db
        finally:
            await db.close()

    monkeypatch.setattr(dependencies, "get_config", mock_get_config)
    # Note: get_db is an async generator, so we need to handle it carefully

    return create_app()


@pytest_asyncio.fixture
async def client(app, temp_db_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    # Initialize database before tests
    db = Database(temp_db_path)
    await db.connect()
    await db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_with_cards(
    app, temp_db_path: Path
) -> AsyncGenerator[tuple[AsyncClient, list[BasicCard]], None]:
    """Create test client with pre-populated cards."""
    db = Database(temp_db_path)
    await db.connect()

    cards = [
        BasicCard(
            front=f"Question {i}",
            back=f"Answer {i}",
            source="test.txt",
            tags=["test"],
            status=CardStatus.DRAFT,
        )
        for i in range(5)
    ]
    # Set some statuses
    cards[0].status = CardStatus.ACCEPTED
    cards[1].status = CardStatus.ACCEPTED
    cards[2].status = CardStatus.REJECTED

    for card in cards:
        await db.save_card(card)

    await db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, cards


@pytest_asyncio.fixture
async def client_with_session(
    app, temp_db_path: Path
) -> AsyncGenerator[tuple[AsyncClient, str, list[BasicCard]], None]:
    """Create test client with pre-populated session and cards."""
    db = Database(temp_db_path)
    await db.connect()

    # Create session
    session_id = await db.create_session(
        sources=["test.txt"],
        provider="openai",
        card_types=["basic"],
        count_guidance="5-10",
    )

    # Create cards and link to session
    cards = [
        BasicCard(front=f"Session Q{i}", back=f"Session A{i}", source="test.txt")
        for i in range(3)
    ]

    for card in cards:
        await db.save_card(card)
        await db.add_card_to_session(session_id, card.id)

    await db.complete_session(session_id)
    await db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_id, cards
