"""Review-session state: a persisted working set of cards plus the user's decisions.

A session holds the user's notes, a history of generation rounds, and the per-card
accept/edit/discard decisions. Rounds reference their source by id; the source text itself
lives in a separate, content-addressed `SourceStore` (so it is stored once and never
embedded in the session). It is the shared artifact between the skill (which seeds it and
can regenerate), the review web app, and the Anki import. Persisted as JSON so a review is
resumable.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from ..models import Card, CardSet, ReviewAction, ReviewDecision, Source


class ReviewSession(BaseModel):
    notes: str = ""
    deck: str = ""
    rounds: list[CardSet] = Field(default_factory=list)
    decisions: dict[str, ReviewDecision] = Field(default_factory=dict)
    requests: list[str] = Field(default_factory=list)  # queued "make a new card about X"

    def carried_cards(self) -> list[Card]:
        """Cards to carry into the next round, in current-round order: pending (undecided)
        and accepted cards as-is, edited cards as their edited version. Discards are dropped
        (unless revised via feedback, which is added separately)."""
        carried: list[Card] = []
        for card in self.current_cards():
            decision = self.decisions.get(card.id)
            if decision is None or decision.action is ReviewAction.ACCEPT:
                carried.append(card)
            elif decision.action is ReviewAction.EDIT and decision.edited_card is not None:
                carried.append(decision.edited_card)
            elif decision.action is ReviewAction.EDIT:
                carried.append(card)
            # DISCARD: dropped
        return carried

    def revisions(self) -> list[tuple[Card, str]]:
        """Discarded cards that carry feedback — (card, feedback) to revise next round."""
        out: list[tuple[Card, str]] = []
        for card in self.current_cards():
            d = self.decisions.get(card.id)
            if d is not None and d.action is ReviewAction.DISCARD and d.feedback:
                out.append((card, d.feedback))
        return out

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


class SourceStore:
    """Content-addressed registry of `Source`s, persisted as `{sid: source}` JSON.

    Each distinct source is stored once (keyed by `Source.sid()`); rounds reference it by id.
    Keeping source text here — out of the session file — means the (often large, sometimes
    copyrighted) markdown is never duplicated across rounds and can be git-ignored on its own.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Source]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text())
        return {sid: Source.model_validate(data) for sid, data in raw.items()}

    def add(self, source: Source) -> str:
        """Store `source` if unseen and return its id (idempotent on identical content)."""
        sid = source.sid()
        sources = self.load()
        if sid not in sources:
            sources[sid] = source
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({k: v.model_dump() for k, v in sources.items()}, indent=2)
            )
        return sid

    def get(self, sid: str) -> Source | None:
        return self.load().get(sid)
