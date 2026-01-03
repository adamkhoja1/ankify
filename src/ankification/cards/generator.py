"""Card generation orchestration."""

from ..config import Config
from ..fetchers import FetcherManager
from ..llm import LLMManager
from ..storage.database import Database
from .models import Card


class CardGenerator:
    """Orchestrates card generation from content sources."""

    def __init__(
        self,
        config: Config,
        database: Database,
        fetcher_manager: FetcherManager | None = None,
        llm_manager: LLMManager | None = None,
    ) -> None:
        """Initialize card generator.

        Args:
            config: Application configuration
            database: Database instance
            fetcher_manager: Optional fetcher manager (creates default if None)
            llm_manager: Optional LLM manager (creates default if None)
        """
        self.config = config
        self.database = database
        self.fetcher_manager = fetcher_manager or FetcherManager()
        self.llm_manager = llm_manager or LLMManager(config)

    async def generate_from_source(
        self,
        source: str,
        provider: str | None = None,
        card_types: list[str] | None = None,
        count_guidance: str | None = None,
    ) -> list[Card]:
        """Generate cards from a single source.

        Args:
            source: Source to fetch from (URL, file path, or text)
            provider: LLM provider to use (None for config default)
            card_types: Types of cards to generate (None for config default)
            count_guidance: Optional guidance for card count

        Returns:
            List of generated cards

        Raises:
            RuntimeError: If generation fails
        """
        # Fetch content
        content = await self.fetcher_manager.fetch(source)

        # Get LLM provider
        llm_provider = self.llm_manager.get_provider(provider)

        # Use config defaults if not specified
        if card_types is None:
            card_types = self.config.generation.card_types

        if count_guidance is None:
            count_guidance = self.config.generation.count_guidance

        # Generate cards
        cards = await llm_provider.generate_cards(
            content=content,
            source=source,
            card_types=card_types,
            count_guidance=count_guidance,
            user_directives=self.config.generation.user_directives,
        )

        return cards

    async def generate_from_sources(
        self,
        sources: list[str],
        provider: str | None = None,
        card_types: list[str] | None = None,
        count_guidance: str | None = None,
    ) -> dict[str, list[Card]]:
        """Generate cards from multiple sources.

        Args:
            source: Sources to fetch from
            provider: LLM provider to use (None for config default)
            card_types: Types of cards to generate (None for config default)
            count_guidance: Optional guidance for card count

        Returns:
            Dictionary mapping source to list of cards

        Raises:
            RuntimeError: If any generation fails
        """
        results: dict[str, list[Card]] = {}

        for source in sources:
            cards = await self.generate_from_source(
                source, provider, card_types, count_guidance
            )
            results[source] = cards

        return results

    async def create_session(
        self,
        sources: list[str],
        provider: str | None = None,
        card_types: list[str] | None = None,
        count_guidance: str | None = None,
    ) -> str:
        """Generate cards and create a session.

        Args:
            sources: Sources to fetch from
            provider: LLM provider to use (None for config default)
            card_types: Types of cards to generate (None for config default)
            count_guidance: Optional guidance for card count

        Returns:
            Session ID

        Raises:
            RuntimeError: If generation or storage fails
        """
        # Create session
        session_id = await self.database.create_session(sources)

        try:
            # Generate cards from all sources
            all_cards = await self.generate_from_sources(
                sources, provider, card_types, count_guidance
            )

            # Save cards and associate with session
            for source, cards in all_cards.items():
                for card in cards:
                    await self.database.save_card(card)
                    await self.database.add_card_to_session(session_id, card.id)

            return session_id

        except Exception as e:
            # If anything fails, we still have the session record
            # but it won't be marked complete
            raise RuntimeError(f"Failed to generate session: {e}") from e

    async def refine_card(
        self, card_id: str, feedback: str, provider: str | None = None
    ) -> Card:
        """Refine a card based on feedback.

        Args:
            card_id: ID of card to refine
            feedback: User feedback for refinement
            provider: LLM provider to use (None for config default)

        Returns:
            Refined card

        Raises:
            ValueError: If card not found
            RuntimeError: If refinement fails
        """
        # Get card
        card = await self.database.get_card(card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        # Store old version
        old_content = card.to_json()

        # Get LLM provider and refine
        llm_provider = self.llm_manager.get_provider(provider)
        refined_card = await llm_provider.refine_card(card, feedback)

        # Update modification time
        refined_card.mark_modified()

        # Save refined card
        await self.database.save_card(refined_card)

        # Record edit history
        if self.config.storage.keep_history:
            await self.database.record_edit(
                card_id=card_id,
                old_content=old_content,
                new_content=refined_card.to_json(),
                edit_type="llm_refine",
                feedback=feedback,
            )

        return refined_card
