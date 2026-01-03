"""Base LLM provider interface."""

from abc import ABC, abstractmethod

from ..cards.models import Card


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_cards(
        self,
        content: str,
        source: str,
        card_types: list[str],
        count_guidance: str | None = None,
        user_directives: list[str] | None = None,
    ) -> list[Card]:
        """Generate flashcards from content.

        Args:
            content: Text content to generate cards from
            source: Source identifier (URL, file path, etc.)
            card_types: Types of cards to generate ('basic', 'cloze', or both)
            count_guidance: Optional guidance for number of cards
            user_directives: Optional list of user directives/preferences

        Returns:
            List of generated cards

        Raises:
            RuntimeError: If generation fails
        """
        pass

    @abstractmethod
    async def refine_card(self, card: Card, feedback: str) -> Card:
        """Refine a card based on user feedback.

        Args:
            card: Card to refine
            feedback: User feedback (e.g., "make it shorter", "focus on X")

        Returns:
            Refined card

        Raises:
            RuntimeError: If refinement fails
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this provider.

        Returns:
            Provider name
        """
        pass
