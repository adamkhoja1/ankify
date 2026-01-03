"""OpenAI LLM provider."""

import json

from openai import AsyncOpenAI

from ..cards.models import BasicCard, Card, ClozeCard
from .base import BaseLLMProvider
from .prompts import (
    REFINEMENT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_generation_prompt,
    build_refinement_prompt,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider for card generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use
            temperature: Sampling temperature
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    async def generate_cards(
        self,
        content: str,
        source: str,
        card_types: list[str],
        count_guidance: str | None = None,
        user_directives: list[str] | None = None,
    ) -> list[Card]:
        """Generate flashcards using OpenAI."""
        prompt = build_generation_prompt(
            content, card_types, count_guidance, user_directives
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            content_str = response.choices[0].message.content
            if not content_str:
                raise RuntimeError("Empty response from OpenAI")

            data = json.loads(content_str)
            cards = self._parse_cards(data, source)

            if not cards:
                raise RuntimeError("No cards generated")

            return cards

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from OpenAI: {e}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI card generation failed: {e}") from e

    async def refine_card(self, card: Card, feedback: str) -> Card:
        """Refine a card using OpenAI."""
        prompt = build_refinement_prompt(card, feedback)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            content_str = response.choices[0].message.content
            if not content_str:
                raise RuntimeError("Empty response from OpenAI")

            data = json.loads(content_str)
            refined_card = self._parse_single_card(data, card.source)

            # Preserve ID and other metadata
            refined_card.id = card.id
            refined_card.tags = card.tags
            refined_card.created_at = card.created_at
            refined_card.status = card.status

            return refined_card

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from OpenAI: {e}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI card refinement failed: {e}") from e

    def _parse_cards(self, data: dict, source: str) -> list[Card]:
        """Parse cards from API response.

        Args:
            data: JSON response data
            source: Source identifier

        Returns:
            List of parsed cards
        """
        cards = []

        if "cards" not in data:
            raise ValueError("Response missing 'cards' field")

        for card_data in data["cards"]:
            card = self._parse_single_card(card_data, source)
            cards.append(card)

        return cards

    def _parse_single_card(self, card_data: dict, source: str) -> Card:
        """Parse a single card from data.

        Args:
            card_data: Card JSON data
            source: Source identifier

        Returns:
            Parsed card
        """
        card_type = card_data.get("type", "").lower()

        if card_type == "basic":
            if "front" not in card_data or "back" not in card_data:
                raise ValueError("Basic card missing 'front' or 'back' field")
            return BasicCard(
                front=card_data["front"].strip(),
                back=card_data["back"].strip(),
                source=source,
            )
        elif card_type == "cloze":
            if "text" not in card_data:
                raise ValueError("Cloze card missing 'text' field")
            return ClozeCard(text=card_data["text"].strip(), source=source)
        else:
            raise ValueError(f"Unknown card type: {card_type}")

    @property
    def name(self) -> str:
        """Get provider name."""
        return "openai"
