"""Mock fixtures for testing external dependencies."""

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ankification.cards.models import BasicCard, CardType, ClozeCard


# === LLM Provider Mocks ===


class MockLLMResponse:
    """Mock response from LLM providers."""

    def __init__(self, content: str):
        self.content = content
        self.choices = [MagicMock(message=MagicMock(content=content))]


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=MockLLMResponse(
            """[
                {"type": "basic", "front": "Mock question?", "back": "Mock answer"},
                {"type": "cloze", "text": "The {{c1::mock}} answer"}
            ]"""
        )
    )
    return client


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Mock Anthropic client."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text="""[
        {"type": "basic", "front": "Mock question?", "back": "Mock answer"},
        {"type": "cloze", "text": "The {{c1::mock}} answer"}
    ]""")]
    client.messages.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_llm_manager() -> MagicMock:
    """Mock LLMManager that returns predefined cards."""
    manager = MagicMock()

    async def mock_generate(*args: Any, **kwargs: Any) -> list[BasicCard | ClozeCard]:
        return [
            BasicCard(front="Generated Q1", back="Generated A1", source="mock"),
            BasicCard(front="Generated Q2", back="Generated A2", source="mock"),
            ClozeCard(text="{{c1::Generated}} cloze", source="mock"),
        ]

    manager.generate_cards = AsyncMock(side_effect=mock_generate)
    return manager


@pytest.fixture
def mock_llm_manager_error() -> MagicMock:
    """Mock LLMManager that raises errors."""
    manager = MagicMock()
    manager.generate_cards = AsyncMock(side_effect=Exception("LLM API Error"))
    return manager


@pytest.fixture
def mock_llm_manager_empty() -> MagicMock:
    """Mock LLMManager that returns no cards."""
    manager = MagicMock()
    manager.generate_cards = AsyncMock(return_value=[])
    return manager


# === Fetcher Mocks ===


@pytest.fixture
def mock_fetcher_manager() -> MagicMock:
    """Mock FetcherManager that returns predefined content."""
    manager = MagicMock()

    async def mock_fetch(source: str) -> str:
        return f"Mock content from {source}. This is sample text for testing."

    manager.fetch = AsyncMock(side_effect=mock_fetch)
    manager.can_handle = MagicMock(return_value=True)
    return manager


@pytest.fixture
def mock_fetcher_manager_error() -> MagicMock:
    """Mock FetcherManager that raises errors."""
    manager = MagicMock()
    manager.fetch = AsyncMock(side_effect=Exception("Fetch error"))
    return manager


@pytest.fixture
def mock_file_fetcher() -> MagicMock:
    """Mock file fetcher."""
    fetcher = MagicMock()
    fetcher.fetch = AsyncMock(return_value="File content for testing")
    fetcher.can_handle = MagicMock(side_effect=lambda s: not s.startswith("http"))
    return fetcher


@pytest.fixture
def mock_url_fetcher() -> MagicMock:
    """Mock URL fetcher."""
    fetcher = MagicMock()
    fetcher.fetch = AsyncMock(return_value="<html><body>Web content</body></html>")
    fetcher.can_handle = MagicMock(side_effect=lambda s: s.startswith("http"))
    return fetcher


# === HTTP Mocks ===


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Mock httpx client for HTTP requests."""
    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.text = "<html><body>Test content</body></html>"
    response.content = b"<html><body>Test content</body></html>"
    response.headers = {"content-type": "text/html"}
    response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_httpx_client_error() -> MagicMock:
    """Mock httpx client that returns errors."""
    import httpx

    client = MagicMock()
    client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
    return client


# === Database Mocks ===


@pytest.fixture
def mock_database() -> MagicMock:
    """Mock database for testing without actual DB."""
    db = MagicMock()
    db.connect = AsyncMock()
    db.close = AsyncMock()
    db.save_card = AsyncMock()
    db.get_card = AsyncMock(return_value=None)
    db.get_all_cards = AsyncMock(return_value=[])
    db.get_cards_by_status = AsyncMock(return_value=[])
    db.get_cards_by_session = AsyncMock(return_value=[])
    db.delete_card = AsyncMock()
    db.create_session = AsyncMock(return_value="mock-session-id")
    db.add_card_to_session = AsyncMock()
    db.complete_session = AsyncMock()
    db.get_sessions = AsyncMock(return_value=[])
    db.search_cards_by_tag = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_database_with_cards() -> MagicMock:
    """Mock database pre-populated with cards."""
    db = MagicMock()
    cards = [
        BasicCard(front="Q1", back="A1", source="test.txt"),
        BasicCard(front="Q2", back="A2", source="test.txt"),
        ClozeCard(text="{{c1::Cloze}}", source="test.txt"),
    ]

    db.connect = AsyncMock()
    db.close = AsyncMock()
    db.save_card = AsyncMock()
    db.get_card = AsyncMock(side_effect=lambda id: next((c for c in cards if c.id == id), None))
    db.get_all_cards = AsyncMock(return_value=cards)
    db.update_card = AsyncMock()
    db.delete_card = AsyncMock()
    return db


# === WebSocket Mocks ===


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Mock WebSocket connection."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock(return_value="ping")
    ws.close = AsyncMock()
    return ws


# === Card Generator Mocks ===


@pytest.fixture
def mock_card_generator() -> MagicMock:
    """Mock CardGenerator."""
    generator = MagicMock()

    async def mock_generate_from_source(*args: Any, **kwargs: Any) -> list[BasicCard | ClozeCard]:
        return [
            BasicCard(front="Generated Q", back="Generated A", source=kwargs.get("source", "mock")),
        ]

    generator.generate_from_source = AsyncMock(side_effect=mock_generate_from_source)
    return generator


# === Context Manager Mocks ===


@pytest.fixture
def mock_temp_file() -> MagicMock:
    """Mock temporary file context manager."""
    temp_file = MagicMock()
    temp_file.__enter__ = MagicMock(return_value=temp_file)
    temp_file.__exit__ = MagicMock(return_value=False)
    temp_file.name = "/tmp/mock_temp_file"
    temp_file.write = MagicMock()
    temp_file.read = MagicMock(return_value="temp file content")
    return temp_file


# === Patch Helpers ===


@pytest.fixture
def patch_openai():
    """Patch OpenAI client for tests."""
    with patch("openai.AsyncOpenAI") as mock:
        mock.return_value.chat.completions.create = AsyncMock(
            return_value=MockLLMResponse('[]')
        )
        yield mock


@pytest.fixture
def patch_anthropic():
    """Patch Anthropic client for tests."""
    with patch("anthropic.AsyncAnthropic") as mock:
        response = MagicMock()
        response.content = [MagicMock(text='[]')]
        mock.return_value.messages.create = AsyncMock(return_value=response)
        yield mock


@pytest.fixture
def patch_httpx():
    """Patch httpx for tests."""
    with patch("httpx.AsyncClient") as mock:
        response = MagicMock()
        response.status_code = 200
        response.text = "Mock content"
        mock.return_value.__aenter__ = AsyncMock(return_value=mock.return_value)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        mock.return_value.get = AsyncMock(return_value=response)
        yield mock
