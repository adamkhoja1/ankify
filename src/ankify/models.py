"""Core data models for ankify.

A `Card` is the unit produced, reviewed, and imported. A `CardSet` ties cards to the
`Source` they came from. `Verdict`/`ProbeResult` capture rubric judgments (see
`docs/RUBRIC.md`). `ReviewDecision` records a human's accept/edit/discard during review.
"""

from __future__ import annotations

import hashlib
import uuid
from enum import Enum

from pydantic import BaseModel, Field, model_validator

CLOZE_MARKER = "{{c"


class CardType(str, Enum):
    BASIC = "basic"
    CLOZE = "cloze"
    REVERSIBLE = "reversible"


class Card(BaseModel):
    """A single flashcard.

    Basic and reversible cards use `front`/`back`. Cloze cards use `cloze_text` (with
    Anki `{{c1::...}}` markers) plus optional `extra`. Reversible cards are imported as
    two notes (front→back and back→front).
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: CardType = CardType.BASIC
    front: str = ""
    back: str = ""
    cloze_text: str = ""
    extra: str = ""
    tags: list[str] = Field(default_factory=list)
    subdeck: str = ""  # sub-deck relative to the session deck, e.g. "Ch01 - The Market"
    source_ref: str = ""  # short anchoring quote/locator from the source
    rationale: str = ""  # why this card exists; not imported into Anki

    @model_validator(mode="after")
    def _validate_shape(self) -> Card:
        if self.type is CardType.CLOZE:
            if not self.cloze_text.strip():
                raise ValueError("cloze card requires cloze_text")
            if CLOZE_MARKER not in self.cloze_text:
                raise ValueError("cloze_text must contain a {{c1::...}} deletion")
        else:
            if not self.front.strip() or not self.back.strip():
                raise ValueError(f"{self.type.value} card requires non-empty front and back")
        return self

    def prompt_text(self) -> str:
        """The question side, as a judge/probe sees it."""
        return self.cloze_text if self.type is CardType.CLOZE else self.front

    def answer_text(self) -> str:
        return self.extra if self.type is CardType.CLOZE else self.back

    def as_qa(self) -> str:
        """Render as the `Q. ... / A. ...` form the prompts expect."""
        if self.type is CardType.CLOZE:
            body = f"Cloze: {self.cloze_text}"
            return f"{body}\n(extra: {self.extra})" if self.extra else body
        return f"Q. {self.front}\nA. {self.back}"


class Source(BaseModel):
    """The material cards are generated from, normalized to markdown.

    Sources are stored once in a content-addressed registry (see `SourceStore`) and
    referenced from rounds by `sid()`, so the (often large) `markdown` is never duplicated
    across rounds or embedded in the review session itself.
    """

    title: str
    kind: str = "markdown"  # markdown | highlight | arxiv | url | pdf | ...
    markdown: str = ""
    uri: str = ""

    def sid(self) -> str:
        """Stable content id used to de-duplicate sources in the store."""
        blob = f"{self.title}\x00{self.kind}\x00{self.uri}\x00{self.markdown}"
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


class CardSet(BaseModel):
    source_id: str = ""  # id into the SourceStore; "" if no source recorded
    cards: list[Card] = Field(default_factory=list)
    round: int = 0  # which generation round produced this set

    def by_id(self, card_id: str) -> Card | None:
        return next((c for c in self.cards if c.id == card_id), None)


class Tier(str, Enum):
    T0 = "T0"  # off-target
    T1 = "T1"  # needs refactor
    T2 = "T2"  # needs polish
    T3 = "T3"  # ready

    @property
    def usable(self) -> bool:
        return self in (Tier.T2, Tier.T3)


class ProbeName(str, Enum):
    LACKS_CONTEXT = "lacks_context"
    MULTIPLE_RESPONSES = "multiple_responses"
    SHALLOW = "shallow"
    WORDY = "wordy"
    NARROW = "narrow"


class ProbeResult(BaseModel):
    probe: ProbeName
    failed: bool
    reason: str = ""


class Verdict(BaseModel):
    tier: Tier
    probes: list[ProbeResult] = Field(default_factory=list)
    reason: str = ""

    @property
    def usable(self) -> bool:
        return self.tier.usable

    @property
    def failed_probes(self) -> list[ProbeName]:
        return [p.probe for p in self.probes if p.failed]

    @property
    def clean(self) -> bool:
        """Usable tier and no probe failures — ready to surface to the user."""
        return self.usable and not self.failed_probes


class ReviewAction(str, Enum):
    ACCEPT = "accept"
    EDIT = "edit"
    DISCARD = "discard"


class ReviewDecision(BaseModel):
    card_id: str
    action: ReviewAction
    edited_card: Card | None = None
    feedback: str = ""
