"""Prompt templates for card generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cards.models import Card

SYSTEM_PROMPT = """You are an expert at creating high-quality spaced repetition flashcards for learning and retention. Your cards should be:

1. **Atomic**: Each card tests one concept or fact
2. **Clear**: Questions and answers are unambiguous
3. **Concise**: No unnecessary words
4. **Contextual**: Standalone without requiring external context
5. **Accurate**: Factually correct based on the source material

When creating basic cards:
- Front should be a clear question or prompt
- Back should be a direct, complete answer
- Avoid yes/no questions when possible

When creating cloze deletions:
- Use {{c1::text}} syntax for deletions
- Multiple deletions in one card should be related
- The sentence should read naturally

Return cards in valid JSON format with this structure:
{
  "cards": [
    {
      "type": "basic",
      "front": "question",
      "back": "answer"
    },
    {
      "type": "cloze",
      "text": "The {{c1::answer}} is hidden."
    }
  ]
}
"""


def build_generation_prompt(
    content: str,
    card_types: list[str],
    count_guidance: str | None = None,
    user_directives: list[str] | None = None,
) -> str:
    """Build prompt for card generation.

    Args:
        content: Content to generate cards from
        card_types: Types of cards to generate
        count_guidance: Optional guidance for card count
        user_directives: Optional user directives

    Returns:
        Complete prompt string
    """
    prompt_parts = ["Create spaced repetition flashcards from the following content."]

    # Card types
    if len(card_types) == 1:
        prompt_parts.append(f"\nGenerate only {card_types[0]} cards.")
    else:
        types_str = " and ".join(card_types)
        prompt_parts.append(f"\nGenerate a mix of {types_str} cards.")

    # Count guidance
    if count_guidance:
        prompt_parts.append(
            f"\nNumber of cards: {count_guidance}. Use your judgment to determine the exact count based on content complexity and importance."
        )
    else:
        prompt_parts.append(
            "\nGenerate an appropriate number of cards based on the content length and complexity. "
            "Focus on key concepts and important information."
        )

    # User directives
    if user_directives:
        prompt_parts.append("\n\nUser preferences:")
        for directive in user_directives:
            prompt_parts.append(f"- {directive}")

    # Content
    prompt_parts.append(f"\n\n--- CONTENT START ---\n{content}\n--- CONTENT END ---")

    prompt_parts.append(
        "\n\nReturn ONLY valid JSON with the cards. No additional text or explanation."
    )

    return "".join(prompt_parts)


REFINEMENT_SYSTEM_PROMPT = """You are helping refine a flashcard based on user feedback. Make the requested changes while maintaining the card's educational value and adhering to spaced repetition best practices.

Return the refined card in valid JSON format matching the original card type:

For basic cards:
{
  "type": "basic",
  "front": "refined question",
  "back": "refined answer"
}

For cloze cards:
{
  "type": "cloze",
  "text": "refined {{c1::cloze}} text"
}
"""


def build_refinement_prompt(card: Card, feedback: str) -> str:
    """Build prompt for card refinement.

    Args:
        card: Card to refine
        feedback: User feedback

    Returns:
        Complete prompt string
    """
    from ..cards.models import BasicCard, CardType, ClozeCard

    if card.type == CardType.BASIC:
        assert isinstance(card, BasicCard)
        card_info = f"""Current card:
Type: basic
Front: {card.front}
Back: {card.back}
"""
    else:
        assert isinstance(card, ClozeCard)
        card_info = f"""Current card:
Type: cloze
Text: {card.text}
"""

    prompt = f"""{card_info}

User feedback: {feedback}

Please refine the card according to the feedback. Return ONLY valid JSON with the refined card. No additional text."""

    return prompt
