"""Pydantic models for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field

from ...cards.models import Card, CardStatus, CardType


class CardResponse(BaseModel):
    """Response model for card data."""

    id: str
    type: str
    content: dict
    source: str
    status: str
    tags: list[str]
    created_at: datetime
    modified_at: datetime

    @classmethod
    def from_card(cls, card: Card) -> "CardResponse":
        """Convert Card to CardResponse."""
        return cls(
            id=card.id,
            type=card.type.value,
            content=card.to_dict(),
            source=card.source,
            status=card.status.value,
            tags=card.tags,
            created_at=card.created_at,
            modified_at=card.modified_at,
        )


class CardUpdate(BaseModel):
    """Request model for updating a card."""

    front: str | None = None
    back: str | None = None
    text: str | None = None  # For cloze cards
    tags: list[str] | None = None


class StatusUpdate(BaseModel):
    """Request model for updating card status."""

    status: CardStatus


class CardFilters(BaseModel):
    """Query parameters for filtering cards."""

    status: CardStatus | None = None
    session_id: str | None = None
    search: str | None = None
    tags: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SessionResponse(BaseModel):
    """Response model for session data."""

    id: str
    sources: list[str]
    provider: str
    card_types: list[str]
    count_guidance: str
    created_at: datetime
    completed_at: datetime | None
    card_count: int
    accepted_count: int
    rejected_count: int
    pending_count: int


class GenerateRequest(BaseModel):
    """Request model for generating cards."""

    sources: list[str] = Field(min_length=1)
    provider: str = Field(default="openai")
    card_types: list[CardType] = Field(default=[CardType.BASIC, CardType.CLOZE])
    count_guidance: str = Field(default="10-15")
    tags: list[str] = Field(default_factory=list)
    user_directives: str | None = None


class RefineRequest(BaseModel):
    """Request model for refining a card with LLM."""

    card_id: str
    feedback: str


class ExportRequest(BaseModel):
    """Request model for exporting cards."""

    card_ids: list[str] | None = None  # None means all accepted cards
    session_id: str | None = None
    format: str = Field(default="csv")  # "csv", "ankiconnect", or "both"
    deck_name: str = Field(default="Ankification")
