"""Card data models."""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CardStatus(str, Enum):
    """Card status enumeration."""

    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class CardType(str, Enum):
    """Card type enumeration."""

    BASIC = "basic"
    CLOZE = "cloze"


class BasicCard(BaseModel):
    """Basic flashcard with front and back."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CardType = Field(default=CardType.BASIC, frozen=True)
    front: str = Field(..., description="Question or prompt")
    back: str = Field(..., description="Answer or explanation")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(..., description="Source document/URL")
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    status: CardStatus = Field(default=CardStatus.DRAFT)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "front": self.front,
            "back": self.back,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "status": self.status.value,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasicCard":
        """Create from dictionary."""
        # Convert string dates back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("modified_at"), str):
            data["modified_at"] = datetime.fromisoformat(data["modified_at"])

        # Convert string enums
        if isinstance(data.get("type"), str):
            data["type"] = CardType(data["type"])
        if isinstance(data.get("status"), str):
            data["status"] = CardStatus(data["status"])

        return cls(**data)

    def mark_modified(self) -> None:
        """Update modification timestamp."""
        self.modified_at = datetime.now()


class ClozeCard(BaseModel):
    """Cloze deletion flashcard."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CardType = Field(default=CardType.CLOZE, frozen=True)
    text: str = Field(..., description="Text with {{c1::cloze}} markers")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(..., description="Source document/URL")
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    status: CardStatus = Field(default=CardStatus.DRAFT)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "text": self.text,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "status": self.status.value,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClozeCard":
        """Create from dictionary."""
        # Convert string dates back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("modified_at"), str):
            data["modified_at"] = datetime.fromisoformat(data["modified_at"])

        # Convert string enums
        if isinstance(data.get("type"), str):
            data["type"] = CardType(data["type"])
        if isinstance(data.get("status"), str):
            data["status"] = CardStatus(data["status"])

        return cls(**data)

    def mark_modified(self) -> None:
        """Update modification timestamp."""
        self.modified_at = datetime.now()


# Union type for cards
Card = BasicCard | ClozeCard


def card_from_dict(data: dict[str, Any]) -> Card:
    """Create a card from dictionary, automatically detecting type.

    Args:
        data: Dictionary representation of card

    Returns:
        BasicCard or ClozeCard instance
    """
    card_type = CardType(data.get("type", "basic"))
    if card_type == CardType.BASIC:
        return BasicCard.from_dict(data)
    else:
        return ClozeCard.from_dict(data)


def card_from_json(json_str: str) -> Card:
    """Create a card from JSON string.

    Args:
        json_str: JSON representation of card

    Returns:
        BasicCard or ClozeCard instance
    """
    data = json.loads(json_str)
    return card_from_dict(data)
