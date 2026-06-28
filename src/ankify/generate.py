"""Card generation and rubric-driven self-review.

`Generator.generate` turns a source (+ optional user notes/scope) into candidate cards;
`Generator.self_review` runs N holistic critique-and-rewrite rounds against the rubric
before the cards are surfaced to the user. Both share the principles in `_PRINCIPLES` so
the programmatic path mirrors what the interactive skill produces.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from pydantic import BaseModel, ValidationError

from .llm import LLM
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
    subdeck: str
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

    def __init__(self, llm: LLM, effort: str | None = None) -> None:
        self.llm = llm
        self.effort = effort  # None -> use the LLM's configured reasoning effort

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
            "{{c1::...}} deletion, optional extra). If the source spans multiple "
            "chapters/sections, set `subdeck` to a clean sub-deck label (e.g. "
            "\"Ch01 - The Market\") relative to the deck; for a single-topic source leave "
            "`subdeck` empty. Always include a short `source_ref` quote/locator and a one-line "
            "`rationale`. Leave unused fields as empty strings."
        )
        user = (
            f"{scope_text}Source ({source.kind}) titled {source.title!r}:\n\n{source.markdown}"
        )
        raw = self.llm.parse(user=user, schema=_RawCardSet, system=system, effort=self.effort)
        cards = _to_cards(raw)
        sid = source.sid()
        for card in cards:
            card.source_id = sid
        return CardSet(cards=cards, round=0)

    def augment(
        self,
        source: Source,
        requests: Sequence[str] = (),
        revisions: Sequence[tuple[Card, str]] = (),
        avoid: Sequence[Card] = (),
    ) -> list[Card]:
        """Create exactly the cards the user asked for, from the same source.

        `requests` are free-text "make a card about X"; `revisions` are (flawed card,
        feedback) pairs to rewrite. `avoid` lists existing cards not to duplicate. Returns
        only the new/revised cards (no broad re-generation, no dropping of requested cards).
        """
        if not requests and not revisions:
            return []
        parts: list[str] = []
        if requests:
            parts.append(
                "Create ONE high-quality card for EACH of these requests:\n"
                + "\n".join(f"- {r}" for r in requests)
            )
        if revisions:
            rev = "\n".join(
                f"- Flawed card: {c.as_qa()}\n  Rewrite per this feedback: {fb}"
                for c, fb in revisions
            )
            parts.append("Rewrite EACH of these into a single better card:\n" + rev)
        if avoid:
            parts.append(
                "Do NOT duplicate these existing cards:\n"
                + "\n".join(f"- {c.as_qa()}" for c in avoid)
            )
        system = (
            f"{_PRINCIPLES}\n\nProduce EXACTLY the cards requested/revised above — one per "
            "request and one per card to rewrite, no extras and no omissions. Ground every "
            "card in the source. Set the appropriate `type` and fill only that type's fields."
        )
        user = (
            "\n\n".join(parts)
            + f"\n\nSource ({source.kind}) titled {source.title!r}:\n\n{source.markdown}"
        )
        raw = self.llm.parse(user=user, schema=_RawCardSet, system=system, effort=self.effort)
        return _to_cards(raw)

    def self_review(
        self, cardset: CardSet, source: Source, notes: str = "", rounds: int = 2
    ) -> CardSet:
        """Critique the whole set against the rubric and rewrite it, `rounds` times.

        Each round drops broken/duplicate cards, refactors T1-style cards (vague,
        non-atomic, shallow), and tightens wording — holistically, so coverage and
        de-duplication are considered together. `source` supplies the text to review against
        (cards carry only a `source_id`), and reviewed cards are re-tagged with it.
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
                f"{note_text}Source ({source.kind}) titled "
                f"{source.title!r}:\n\n{source.markdown}\n\n"
                f"Draft cards:\n\n{rendered}"
            )
            raw = self.llm.parse(user=user, schema=_RawCardSet, system=system, effort=self.effort)
            cards = _to_cards(raw)
            logger.info("self-review round %d: %d cards", r, len(cards))
        sid = source.sid()
        for card in cards:
            card.source_id = sid
        return CardSet(cards=cards, round=rounds)
