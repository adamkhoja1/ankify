"""Card generation and rubric-driven self-review.

`Generator.generate` turns a source (+ optional user notes/scope) into candidate cards;
`Generator.self_review` runs N holistic critique-and-rewrite rounds against the rubric
before the cards are surfaced to the user. Both share the principles in `_PRINCIPLES` so
the programmatic path mirrors what the interactive skill produces.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ValidationError

from .llm import LLM, Effort
from .models import Card, CardSet, CardType, Source

logger = logging.getLogger(__name__)

# Shared card-writing principles (condensed from docs/RUBRIC.md). Kept in sync with the
# skill's principles.md so the eval reflects the skill.
_PRINCIPLES = """\
You write spaced-repetition flashcards that are *meaningful* (worth remembering long-term)
and *stable* (reliably recallable months later, reviewed in isolation without the source).

Apply stringency to the QUESTION; the answer may add brief context. Each card must:
- Atomic: test exactly one retrieval target. Split bundled facts into separate cards.
- Single unambiguous answer: no sets/lists, no subjective qualifiers ("primary/key/main"),
  no indefinite "a/an", no open "why is X important". Attribution or enumeration rescues
  breadth ("the four conditions Jacobs lists", "according to Kahneman").
- Self-contained: resolve "this/that/the system"; name the source when the answer depends
  on a specific framing. Prefer source-anchored wording over generic paraphrase.
- Not yes/no: demand generative recall, not a 50% guess.
- Faithful: the answer must be supported by the source; never invent details.
- Tests understanding, not pattern-matching; capture the "why/how" when the source explains it.
- Concise: no padding; necessary technical terms are fine.
- Worth memorizing: skip throwaway trivia and instantly re-derivable facts.

Card types: prefer Basic Q&A. Use a Cloze card (Anki `{{c1::...}}` deletion in `cloze_text`)
when a fill-in-the-blank on a specific term/phrase is genuinely the cleaner test. Use a
Reversible pair only for true bidirectional associations (term <-> definition).

Prefer fewer excellent cards over many shallow ones.\
"""


class _RawCard(BaseModel):
    type: CardType
    front: str
    back: str
    cloze_text: str
    extra: str
    source_ref: str
    rationale: str
    tags: list[str]


class _RawCardSet(BaseModel):
    cards: list[_RawCard]


def _to_cards(raw: _RawCardSet) -> list[Card]:
    cards: list[Card] = []
    for rc in raw.cards:
        try:
            cards.append(Card(**rc.model_dump()))
        except ValidationError as exc:
            logger.warning("dropping malformed generated card (%s): %s", rc.type, exc)
    return cards


class Generator:
    """Generates and self-reviews cards from a source via an `LLM`."""

    def __init__(self, llm: LLM, effort: Effort = "high") -> None:
        self.llm = llm
        self.effort = effort

    def generate(
        self,
        source: Source,
        notes: str = "",
        count_hint: int | None = None,
        allow_cloze: bool = True,
    ) -> CardSet:
        scope = []
        if notes:
            scope.append(f"User notes / scope (follow these):\n{notes}")
        if count_hint:
            scope.append(f"Aim for roughly {count_hint} cards, prioritizing quality.")
        if not allow_cloze:
            scope.append("Do not produce cloze cards; use Basic/reversible only.")
        scope_text = ("\n\n".join(scope) + "\n\n") if scope else ""

        coverage = (
            "This source is a single highlighted excerpt the reader chose to remember. "
            "Target cards on exactly what THIS excerpt says (its specific claim/detail), "
            "not the broader topic; off-target cards are worse than none."
            if source.kind == "highlight"
            else "Return cards covering the most important, durable ideas in the source."
        )
        system = (
            f"{_PRINCIPLES}\n\n{coverage} For each card set the appropriate `type` and "
            "fill only the fields "
            "that type uses (Basic/reversible: front+back; cloze: cloze_text with a "
            "{{c1::...}} deletion, optional extra). Always include a short `source_ref` "
            "quote/locator and a one-line `rationale`. Leave unused fields as empty strings."
        )
        user = (
            f"{scope_text}Source ({source.kind}) titled {source.title!r}:\n\n{source.markdown}"
        )
        raw = self.llm.parse(user=user, schema=_RawCardSet, system=system, effort=self.effort)
        return CardSet(source=source, cards=_to_cards(raw), round=0)

    def self_review(self, cardset: CardSet, notes: str = "", rounds: int = 2) -> CardSet:
        """Critique the whole set against the rubric and rewrite it, `rounds` times.

        Each round drops broken/duplicate cards, refactors T1-style cards (vague,
        non-atomic, shallow), and tightens wording — holistically, so coverage and
        de-duplication are considered together.
        """
        cards = cardset.cards
        system = (
            f"{_PRINCIPLES}\n\nYou are reviewing a draft card set against these principles. "
            "Improve it: DROP cards that are off-target, duplicative, or not worth "
            "memorizing; REWRITE cards that are vague, non-atomic, ambiguous, shallow, or "
            "wordy (split one card into several if needed); KEEP excellent cards unchanged. "
            "Stay faithful to the source. Return the full improved set."
        )
        for r in range(1, rounds + 1):
            if not cards:
                break
            rendered = "\n\n".join(
                f"[{i}] {c.as_qa()}" for i, c in enumerate(cards)
            )
            note_text = f"User notes / scope:\n{notes}\n\n" if notes else ""
            user = (
                f"{note_text}Source ({cardset.source.kind}) titled "
                f"{cardset.source.title!r}:\n\n{cardset.source.markdown}\n\n"
                f"Draft cards:\n\n{rendered}"
            )
            raw = self.llm.parse(user=user, schema=_RawCardSet, system=system, effort=self.effort)
            cards = _to_cards(raw)
            logger.info("self-review round %d: %d cards", r, len(cards))
        return CardSet(source=cardset.source, cards=cards, round=rounds)
