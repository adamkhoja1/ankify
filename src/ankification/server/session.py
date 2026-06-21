"""Review-session state: a persisted working set of cards plus the user's decisions.

A session holds the source, the user's notes, a history of generation rounds, and the
per-card accept/edit/discard decisions. It is the shared artifact between the skill (which
seeds it and can regenerate), the review web app, and the Anki import. Persisted as JSON so
a review is resumable.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..models import Card, CardSet, ReviewAction, ReviewDecision, Source


class ReviewSession(BaseModel):
    source: Source
    notes: str = ""
    deck: str = ""
    rounds: list[CardSet] = Field(default_factory=list)
    decisions: dict[str, ReviewDecision] = Field(default_factory=dict)

    @property
    def current(self) -> CardSet | None:
        return self.rounds[-1] if self.rounds else None

    def current_cards(self) -> list[Card]:
        return self.current.cards if self.current else []

    def approved_cards(self) -> list[Card]:
        """Accepted cards (edited versions where the user edited), in current-round order."""
        approved: list[Card] = []
        for card in self.current_cards():
            decision = self.decisions.get(card.id)
            if decision is None or decision.action is ReviewAction.DISCARD:
                continue
            if decision.action is ReviewAction.EDIT and decision.edited_card is not None:
                approved.append(decision.edited_card)
            else:
                approved.append(card)
        return approved

    def pending_count(self) -> int:
        return sum(1 for c in self.current_cards() if c.id not in self.decisions)

    def feedback(self) -> list[str]:
        return [d.feedback for d in self.decisions.values() if d.feedback]

    def discarded_cards(self) -> list[Card]:
        out: list[Card] = []
        for card in self.current_cards():
            d = self.decisions.get(card.id)
            if d is not None and d.action is ReviewAction.DISCARD:
                out.append(card)
        return out


class SessionStore:
    """Loads and saves a `ReviewSession` to a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> ReviewSession:
        return ReviewSession.model_validate_json(self.path.read_text())

    def save(self, session: ReviewSession) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(session.model_dump_json(indent=2))
