"""Anthropic Claude LLM provider."""

import json

from anthropic import AsyncAnthropic

from ..cards.models import BasicCard, Card, ClozeCard
from .base import BaseLLMProvider
from .prompts import (
    REFINEMENT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_generation_prompt,
    build_refinement_prompt,
)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider for card generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use
            temperature: Sampling temperature
        """
        self.client = AsyncAnthropic(api_key=api_key)
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
        """Generate flashcards using Claude."""
        prompt = build_generation_prompt(
            content, card_types, count_guidance, user_directives
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content_blocks = response.content
            if not content_blocks:
                raise RuntimeError("Empty response from Claude")

            # Extract text from content blocks
            text = ""
            for block in content_blocks:
                if block.type == "text":
                    text += block.text

            if not text:
                raise RuntimeError("No text content in Claude response")

            # Parse JSON from response
            data = self._extract_json(text)
            cards = self._parse_cards(data, source)

            if not cards:
                raise RuntimeError("No cards generated")

            return cards

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from Claude: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Claude card generation failed: {e}") from e

    async def refine_card(self, card: Card, feedback: str) -> Card:
        """Refine a card using Claude."""
        prompt = build_refinement_prompt(card, feedback)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=self.temperature,
                system=REFINEMENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content_blocks = response.content
            if not content_blocks:
                raise RuntimeError("Empty response from Claude")

            # Extract text
            text = ""
            for block in content_blocks:
                if block.type == "text":
                    text += block.text

            if not text:
                raise RuntimeError("No text content in Claude response")

            # Parse JSON
            data = self._extract_json(text)
            refined_card = self._parse_single_card(data, card.source)

            # Preserve ID and other metadata
            refined_card.id = card.id
            refined_card.tags = card.tags
            refined_card.created_at = card.created_at
            refined_card.status = card.status

            return refined_card

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from Claude: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Claude card refinement failed: {e}") from e

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from text, handling markdown code blocks.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON data
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                json_str = text[start:end].strip()
                return json.loads(json_str)

        # Try extracting from generic code block
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                json_str = text[start:end].strip()
                return json.loads(json_str)

        # Last resort: try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)

        raise json.JSONDecodeError("Could not extract JSON from response", text, 0)

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
        return "anthropic"
