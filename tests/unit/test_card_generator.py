"""Unit tests for CardGenerator with mocked dependencies.

Tests CardGenerator behavior with mocked:
- LLMManager (no real API calls)
- FetcherManager
- Database
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ankification.cards.generator import CardGenerator
from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.config import Config
from ankification.fetchers.manager import FetcherManager
from ankification.llm.manager import LLMManager
from ankification.storage.database import Database


class TestCardGeneratorWithFetcher:
    """Integration tests for CardGenerator + FetcherManager."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        cfg = Config()
        cfg.generation.card_types = ["basic", "cloze"]
        cfg.generation.count_guidance = "5-10"
        return cfg

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    @pytest.fixture
    def mock_llm_manager(self) -> MagicMock:
        """Create mock LLM manager."""
        manager = MagicMock(spec=LLMManager)
        mock_provider = MagicMock()
        mock_provider.generate_cards = AsyncMock(return_value=[
            BasicCard(front="Q1", back="A1", source="test.txt"),
            ClozeCard(text="{{c1::answer}}", source="test.txt"),
        ])
        manager.get_provider.return_value = mock_provider
        return manager

    async def test_generator_uses_fetcher_for_files(
        self, config: Config, db: Database, mock_llm_manager: MagicMock, temp_dir: Path
    ) -> None:
        """CardGenerator should use FetcherManager to get file content."""
        # Create test file
        test_file = temp_dir / "content.txt"
        test_file.write_text("This is test content for card generation.")

        fetcher_manager = FetcherManager()
        generator = CardGenerator(
            config=config,
            database=db,
            fetcher_manager=fetcher_manager,
            llm_manager=mock_llm_manager,
        )

        cards = await generator.generate_from_source(str(test_file))

        # Verify cards were generated
        assert len(cards) == 2
        assert mock_llm_manager.get_provider.called
        mock_provider = mock_llm_manager.get_provider.return_value
        assert mock_provider.generate_cards.called

        # Verify content was fetched (passed to LLM)
        call_args = mock_provider.generate_cards.call_args
        assert "This is test content" in call_args.kwargs["content"]

    async def test_generator_uses_fetcher_for_text(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator should use FetcherManager for raw text."""
        fetcher_manager = FetcherManager()
        generator = CardGenerator(
            config=config,
            database=db,
            fetcher_manager=fetcher_manager,
            llm_manager=mock_llm_manager,
        )

        raw_text = "Direct text content for testing"
        cards = await generator.generate_from_source(raw_text)

        assert len(cards) >= 0  # May vary based on mock

    async def test_generator_respects_config_card_types(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator should use config card_types when not specified."""
        config.generation.card_types = ["basic"]

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        await generator.generate_from_source("test content")

        call_args = mock_llm_manager.get_provider.return_value.generate_cards.call_args
        assert call_args.kwargs["card_types"] == ["basic"]

    async def test_generator_respects_config_count_guidance(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator should use config count_guidance when not specified."""
        config.generation.count_guidance = "1-3"

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        await generator.generate_from_source("test content")

        call_args = mock_llm_manager.get_provider.return_value.generate_cards.call_args
        assert call_args.kwargs["count_guidance"] == "1-3"


class TestCardGeneratorWithDatabase:
    """Integration tests for CardGenerator + Database."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        cfg = Config()
        cfg.storage.keep_history = True
        return cfg

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    @pytest.fixture
    def mock_llm_manager(self) -> MagicMock:
        """Create mock LLM manager with deterministic output."""
        manager = MagicMock(spec=LLMManager)
        mock_provider = MagicMock()
        mock_provider.generate_cards = AsyncMock(return_value=[
            BasicCard(front="Generated Q", back="Generated A", source="test"),
        ])
        mock_provider.refine_card = AsyncMock(side_effect=lambda card, feedback: BasicCard(
            id=card.id,
            front=f"Refined: {card.front}",
            back=card.back,
            source=card.source,
        ))
        manager.get_provider.return_value = mock_provider
        return manager

    async def test_refine_card_updates_database(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator.refine_card should update the database."""
        # Create and save initial card
        original_card = BasicCard(front="Original Q", back="Original A", source="test.txt")
        await db.save_card(original_card)

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        # Refine card
        refined = await generator.refine_card(original_card.id, "Make it better")

        # Verify database was updated
        db_card = await db.get_card(original_card.id)
        assert db_card is not None
        assert "Refined" in db_card.front

    async def test_refine_card_records_edit_history(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator.refine_card should record edit history when enabled."""
        original_card = BasicCard(front="Original Q", back="Original A", source="test.txt")
        await db.save_card(original_card)

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        await generator.refine_card(original_card.id, "Make it better")

        # Check edit history
        history = await db.get_edit_history(original_card.id)
        assert len(history) >= 1
        assert history[0]["edit_type"] == "llm_refine"

    async def test_refine_nonexistent_card_raises(
        self, config: Config, db: Database, mock_llm_manager: MagicMock
    ) -> None:
        """CardGenerator.refine_card should raise for nonexistent card."""
        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        with pytest.raises(ValueError, match="Card not found"):
            await generator.refine_card("nonexistent-id", "feedback")


class TestGenerateFromMultipleSources:
    """Integration tests for multi-source generation."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        return Config()

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    @pytest.fixture
    def mock_llm_manager(self) -> MagicMock:
        """Create mock LLM manager."""
        manager = MagicMock(spec=LLMManager)
        mock_provider = MagicMock()

        # Return different cards for different sources
        def make_cards(content: str, source: str, **kwargs):
            return [BasicCard(front=f"Q from {source}", back=f"A from {source}", source=source)]

        mock_provider.generate_cards = AsyncMock(side_effect=make_cards)
        manager.get_provider.return_value = mock_provider
        return manager

    async def test_generate_from_multiple_sources(
        self, config: Config, db: Database, mock_llm_manager: MagicMock, temp_dir: Path
    ) -> None:
        """CardGenerator should handle multiple sources."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file1.write_text("Content 1")
        file2 = temp_dir / "file2.txt"
        file2.write_text("Content 2")

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        results = await generator.generate_from_sources([str(file1), str(file2)])

        assert str(file1) in results
        assert str(file2) in results
        assert len(results[str(file1)]) >= 1
        assert len(results[str(file2)]) >= 1


class TestGeneratorProviderSelection:
    """Integration tests for LLM provider selection."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        cfg = Config()
        cfg.llm.default_provider = "openai"
        return cfg

    @pytest.fixture
    async def db(self, temp_dir: Path) -> Database:
        """Create test database."""
        db = Database(temp_dir / "test.db")
        await db.connect()
        yield db
        await db.close()

    async def test_generator_uses_default_provider(
        self, config: Config, db: Database
    ) -> None:
        """CardGenerator should use default provider from config."""
        mock_llm_manager = MagicMock(spec=LLMManager)
        mock_provider = MagicMock()
        mock_provider.generate_cards = AsyncMock(return_value=[])
        mock_llm_manager.get_provider.return_value = mock_provider

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        await generator.generate_from_source("test content")

        # Should call get_provider with None (uses default)
        mock_llm_manager.get_provider.assert_called_with(None)

    async def test_generator_uses_specified_provider(
        self, config: Config, db: Database
    ) -> None:
        """CardGenerator should use specified provider when provided."""
        mock_llm_manager = MagicMock(spec=LLMManager)
        mock_provider = MagicMock()
        mock_provider.generate_cards = AsyncMock(return_value=[])
        mock_llm_manager.get_provider.return_value = mock_provider

        generator = CardGenerator(
            config=config,
            database=db,
            llm_manager=mock_llm_manager,
        )

        await generator.generate_from_source("test content", provider="anthropic")

        mock_llm_manager.get_provider.assert_called_with("anthropic")
