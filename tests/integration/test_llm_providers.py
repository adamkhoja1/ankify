"""Integration tests for LLM providers with real API calls.

These tests require actual API keys to be configured:
- OPENAI_API_KEY for OpenAI tests
- ANTHROPIC_API_KEY for Anthropic tests
- GOOGLE_API_KEY or GEMINI_API_KEY for Gemini tests

Tests will fail if the required environment variables are not set.
This is intentional - failing tests show what needs to be configured.

Run with: pytest tests/integration/test_llm_providers.py -v
"""

import pytest

from ankification.cards.models import BasicCard, CardType, ClozeCard
from ankification.config import Config
from ankification.llm.anthropic_provider import AnthropicProvider
from ankification.llm.openai_provider import OpenAIProvider

# Gemini provider may not exist yet
try:
    from ankification.llm.gemini_provider import GeminiProvider
    HAS_GEMINI = True
except ImportError:
    GeminiProvider = None  # type: ignore
    HAS_GEMINI = False


@pytest.mark.integration
class TestOpenAIProviderReal:
    """Integration tests for OpenAI provider with real API.

    Requires: OPENAI_API_KEY environment variable
    """

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create real OpenAI provider."""
        config = Config()
        return OpenAIProvider(config)

    async def test_generate_basic_cards(self, provider: OpenAIProvider) -> None:
        """OpenAI should generate basic flashcards from content."""
        content = """
        Python is a high-level programming language created by Guido van Rossum.
        It emphasizes code readability with significant indentation.
        Python supports multiple programming paradigms including procedural,
        object-oriented, and functional programming.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["basic"],
            count_guidance="2-3",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, BasicCard) for c in cards)
        # Cards should have actual content
        for card in cards:
            assert len(card.front) > 10
            assert len(card.back) > 5

    async def test_generate_cloze_cards(self, provider: OpenAIProvider) -> None:
        """OpenAI should generate cloze deletion cards."""
        content = """
        The mitochondria is the powerhouse of the cell.
        It produces ATP through cellular respiration.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["cloze"],
            count_guidance="1-2",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, ClozeCard) for c in cards)
        # Cloze cards should have proper syntax
        for card in cards:
            assert "{{c1::" in card.text

    async def test_refine_card(self, provider: OpenAIProvider) -> None:
        """OpenAI should refine cards based on feedback."""
        original = BasicCard(
            front="What is Python?",
            back="A language",
            source="test",
        )

        refined = await provider.refine_card(
            card=original,
            feedback="Make the answer more detailed and educational",
        )

        assert isinstance(refined, BasicCard)
        assert refined.front  # Should have front
        assert len(refined.back) > len(original.back)  # Should be more detailed


@pytest.mark.integration
class TestAnthropicProviderReal:
    """Integration tests for Anthropic provider with real API.

    Requires: ANTHROPIC_API_KEY environment variable
    """

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create real Anthropic provider."""
        config = Config()
        return AnthropicProvider(config)

    async def test_generate_basic_cards(self, provider: AnthropicProvider) -> None:
        """Anthropic should generate basic flashcards from content."""
        content = """
        Machine learning is a subset of artificial intelligence.
        It enables systems to learn and improve from experience.
        Common types include supervised, unsupervised, and reinforcement learning.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["basic"],
            count_guidance="2-3",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, BasicCard) for c in cards)
        for card in cards:
            assert len(card.front) > 10
            assert len(card.back) > 5

    async def test_generate_cloze_cards(self, provider: AnthropicProvider) -> None:
        """Anthropic should generate cloze deletion cards."""
        content = """
        DNA stands for deoxyribonucleic acid.
        It contains genetic instructions for development.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["cloze"],
            count_guidance="1-2",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, ClozeCard) for c in cards)
        for card in cards:
            assert "{{c1::" in card.text

    async def test_refine_card(self, provider: AnthropicProvider) -> None:
        """Anthropic should refine cards based on feedback."""
        original = BasicCard(
            front="What is ML?",
            back="Machine learning",
            source="test",
        )

        refined = await provider.refine_card(
            card=original,
            feedback="Expand the answer to explain what machine learning actually does",
        )

        assert isinstance(refined, BasicCard)
        assert len(refined.back) > len(original.back)


@pytest.mark.integration
@pytest.mark.skipif(not HAS_GEMINI, reason="GeminiProvider not implemented")
class TestGeminiProviderReal:
    """Integration tests for Gemini provider with real API.

    Requires: GOOGLE_API_KEY or GEMINI_API_KEY environment variable

    Note: This class is skipped if GeminiProvider doesn't exist (not implemented yet).
    """

    @pytest.fixture
    def provider(self) -> GeminiProvider:
        """Create real Gemini provider."""
        config = Config()
        return GeminiProvider(config)

    async def test_generate_basic_cards(self, provider: GeminiProvider) -> None:
        """Gemini should generate basic flashcards from content."""
        content = """
        The solar system consists of the Sun and objects bound by gravity.
        It includes eight planets, dwarf planets, moons, and asteroids.
        The four inner planets are rocky; the outer four are gas giants.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["basic"],
            count_guidance="2-3",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, BasicCard) for c in cards)
        for card in cards:
            assert len(card.front) > 10
            assert len(card.back) > 5

    async def test_generate_cloze_cards(self, provider: GeminiProvider) -> None:
        """Gemini should generate cloze deletion cards."""
        content = """
        Water has the chemical formula H2O.
        It consists of two hydrogen atoms bonded to one oxygen atom.
        """

        cards = await provider.generate_cards(
            content=content,
            source="test",
            card_types=["cloze"],
            count_guidance="1-2",
        )

        assert len(cards) >= 1
        assert all(isinstance(c, ClozeCard) for c in cards)
        for card in cards:
            assert "{{c1::" in card.text


@pytest.mark.integration
class TestProviderConsistency:
    """Tests that verify all providers produce consistent output formats.

    Requires: At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY
    """

    async def test_cards_have_required_fields(self) -> None:
        """All available providers should produce cards with required fields."""
        config = Config()
        content = "Python is a programming language known for its simplicity."

        # Test with OpenAI (most commonly available)
        provider = OpenAIProvider(config)
        cards = await provider.generate_cards(
            content=content,
            source="consistency_test",
            card_types=["basic"],
            count_guidance="1",
        )

        assert len(cards) >= 1, "Should generate at least 1 card"

        for card in cards:
            assert card.id, "Card missing id"
            assert card.source == "consistency_test", "Card has wrong source"
            assert card.type == CardType.BASIC, "Card has wrong type"
            assert isinstance(card, BasicCard), "Should return BasicCard"
            assert card.front, "Card missing front"
            assert card.back, "Card missing back"
