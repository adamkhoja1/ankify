"""TUI test fixtures."""

import pytest

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.config import Config
from ankification.tui.app import AnkificationTUI


@pytest.fixture
def sample_cards() -> list[BasicCard | ClozeCard]:
    """Create sample cards for TUI testing."""
    return [
        BasicCard(
            front="What is Python?",
            back="A programming language",
            source="test.txt",
            tags=["python", "programming"],
            status=CardStatus.DRAFT,
        ),
        BasicCard(
            front="What is 2 + 2?",
            back="4",
            source="test.txt",
            tags=["math"],
            status=CardStatus.DRAFT,
        ),
        ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source="biology.txt",
            tags=["biology"],
            status=CardStatus.DRAFT,
        ),
    ]


@pytest.fixture
def mixed_status_cards() -> list[BasicCard]:
    """Create cards with mixed statuses."""
    return [
        BasicCard(front="Q1", back="A1", source="test.txt", status=CardStatus.DRAFT),
        BasicCard(front="Q2", back="A2", source="test.txt", status=CardStatus.ACCEPTED),
        BasicCard(front="Q3", back="A3", source="test.txt", status=CardStatus.REJECTED),
        BasicCard(front="Q4", back="A4", source="test.txt", status=CardStatus.DRAFT),
    ]


@pytest.fixture
def test_config() -> Config:
    """Create test configuration for TUI."""
    config = Config()
    config.tags.pools = ["tag1", "tag2", "python", "programming"]
    return config


@pytest.fixture
def tui_app(sample_cards: list[BasicCard | ClozeCard], test_config: Config) -> AnkificationTUI:
    """Create TUI app instance for testing."""
    return AnkificationTUI(sample_cards, test_config)


@pytest.fixture
def tui_app_with_mixed_cards(
    mixed_status_cards: list[BasicCard], test_config: Config
) -> AnkificationTUI:
    """Create TUI app with mixed status cards."""
    return AnkificationTUI(mixed_status_cards, test_config)
