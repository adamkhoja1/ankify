"""Factory classes for generating test data."""

import uuid
from datetime import datetime
from typing import Any

import factory
from faker import Faker

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.config import Config

fake = Faker()


class BasicCardFactory(factory.Factory):
    """Factory for generating BasicCard instances."""

    class Meta:
        model = BasicCard

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    front = factory.LazyFunction(lambda: fake.sentence().rstrip(".") + "?")
    back = factory.LazyFunction(fake.paragraph)
    source = factory.LazyFunction(lambda: f"{fake.word()}.txt")
    tags = factory.LazyFunction(lambda: [fake.word() for _ in range(2)])
    created_at = factory.LazyFunction(datetime.now)
    modified_at = factory.LazyFunction(datetime.now)
    status = CardStatus.DRAFT

    class Params:
        accepted = factory.Trait(status=CardStatus.ACCEPTED)
        rejected = factory.Trait(status=CardStatus.REJECTED)


class ClozeCardFactory(factory.Factory):
    """Factory for generating ClozeCard instances."""

    class Meta:
        model = ClozeCard

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    text = factory.LazyFunction(
        lambda: f"The {fake.word()} is {{{{c1::{fake.word()}}}}}."
    )
    source = factory.LazyFunction(lambda: f"{fake.word()}.txt")
    tags = factory.LazyFunction(lambda: [fake.word() for _ in range(2)])
    created_at = factory.LazyFunction(datetime.now)
    modified_at = factory.LazyFunction(datetime.now)
    status = CardStatus.DRAFT

    class Params:
        accepted = factory.Trait(status=CardStatus.ACCEPTED)
        rejected = factory.Trait(status=CardStatus.REJECTED)


class CardBatchFactory:
    """Factory for generating batches of cards."""

    @staticmethod
    def create_mixed_batch(
        basic_count: int = 5,
        cloze_count: int = 3,
        accepted_ratio: float = 0.5,
    ) -> list[BasicCard | ClozeCard]:
        """Create a mixed batch of cards with various statuses.

        Args:
            basic_count: Number of basic cards to create
            cloze_count: Number of cloze cards to create
            accepted_ratio: Ratio of cards to mark as accepted

        Returns:
            List of mixed cards
        """
        cards: list[BasicCard | ClozeCard] = []

        for i in range(basic_count):
            if i < basic_count * accepted_ratio:
                cards.append(BasicCardFactory.build(accepted=True))
            else:
                cards.append(BasicCardFactory.build())

        for i in range(cloze_count):
            if i < cloze_count * accepted_ratio:
                cards.append(ClozeCardFactory.build(accepted=True))
            else:
                cards.append(ClozeCardFactory.build())

        return cards

    @staticmethod
    def create_basic_batch(
        count: int = 5,
        source: str = "test.txt",
        tags: list[str] | None = None,
    ) -> list[BasicCard]:
        """Create a batch of basic cards.

        Args:
            count: Number of cards to create
            source: Source to assign to all cards
            tags: Tags to assign to all cards

        Returns:
            List of basic cards
        """
        return [
            BasicCardFactory.build(source=source, tags=tags or [])
            for _ in range(count)
        ]

    @staticmethod
    def create_cloze_batch(
        count: int = 3,
        source: str = "test.txt",
        tags: list[str] | None = None,
    ) -> list[ClozeCard]:
        """Create a batch of cloze cards.

        Args:
            count: Number of cards to create
            source: Source to assign to all cards
            tags: Tags to assign to all cards

        Returns:
            List of cloze cards
        """
        return [
            ClozeCardFactory.build(source=source, tags=tags or [])
            for _ in range(count)
        ]


class ConfigFactory:
    """Factory for creating test configurations."""

    @staticmethod
    def build(
        default_provider: str = "openai",
        database_path: str | None = None,
        **overrides: Any,
    ) -> Config:
        """Build a test configuration.

        Args:
            default_provider: Default LLM provider
            database_path: Database path (optional)
            **overrides: Additional config overrides using dot notation

        Returns:
            Config instance
        """
        config = Config()
        config.llm.default_provider = default_provider

        if database_path:
            config.storage.database_path = database_path

        # Apply nested overrides
        for key, value in overrides.items():
            parts = key.split(".")
            obj: Any = config
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)

        return config

    @staticmethod
    def build_with_temp_db(temp_dir: str) -> Config:
        """Build config with temporary database.

        Args:
            temp_dir: Temporary directory path

        Returns:
            Config instance
        """
        return ConfigFactory.build(
            database_path=f"{temp_dir}/test.db",
            **{"export.csv.output_dir": f"{temp_dir}/export"},
        )


class SessionDataFactory:
    """Factory for generating session-related test data."""

    @staticmethod
    def build_session_params(
        sources: list[str] | None = None,
        provider: str = "openai",
        card_types: list[str] | None = None,
        count_guidance: str = "5-10",
    ) -> dict[str, Any]:
        """Build parameters for creating a session.

        Args:
            sources: Source URLs/files
            provider: LLM provider
            card_types: Card types to generate
            count_guidance: Card count guidance

        Returns:
            Dictionary of session parameters
        """
        return {
            "sources": sources or [f"{fake.word()}.txt"],
            "provider": provider,
            "card_types": card_types or ["basic", "cloze"],
            "count_guidance": count_guidance,
        }


class GenerateRequestFactory:
    """Factory for generating API request data."""

    @staticmethod
    def build(
        sources: list[str] | None = None,
        provider: str = "openai",
        card_types: list[str] | None = None,
        count_guidance: str = "5-10",
        tags: list[str] | None = None,
        user_directives: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build generate request data.

        Args:
            sources: Content sources
            provider: LLM provider
            card_types: Card types to generate
            count_guidance: Card count guidance
            tags: Tags to apply
            user_directives: Custom generation directives

        Returns:
            Dictionary suitable for GenerateRequest
        """
        return {
            "sources": sources or ["Sample content for testing."],
            "provider": provider,
            "card_types": card_types or ["basic", "cloze"],
            "count_guidance": count_guidance,
            "tags": tags or [],
            "user_directives": user_directives or [],
        }
