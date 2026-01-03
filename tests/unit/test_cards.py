"""Unit tests for card models."""

import json
from datetime import datetime

import pytest

from ankification.cards.models import (
    BasicCard,
    CardStatus,
    CardType,
    ClozeCard,
    card_from_dict,
    card_from_json,
)


class TestBasicCard:
    """Tests for BasicCard model."""

    def test_create_basic_card(self):
        """Test creating a basic card."""
        card = BasicCard(
            front="What is Python?",
            back="A programming language",
            source="test.txt",
        )

        assert card.front == "What is Python?"
        assert card.back == "A programming language"
        assert card.source == "test.txt"
        assert card.type == CardType.BASIC
        assert card.status == CardStatus.DRAFT
        assert isinstance(card.id, str)
        assert isinstance(card.created_at, datetime)

    def test_basic_card_with_tags(self):
        """Test basic card with tags."""
        card = BasicCard(
            front="Question",
            back="Answer",
            source="test.txt",
            tags=["programming", "python"],
        )

        assert card.tags == ["programming", "python"]

    def test_to_dict(self):
        """Test converting card to dictionary."""
        card = BasicCard(
            front="Question", back="Answer", source="test.txt", tags=["tag1"]
        )

        data = card.to_dict()

        assert data["front"] == "Question"
        assert data["back"] == "Answer"
        assert data["source"] == "test.txt"
        assert data["tags"] == ["tag1"]
        assert data["type"] == "basic"
        assert data["status"] == "draft"
        assert isinstance(data["created_at"], str)

    def test_to_json(self):
        """Test converting card to JSON."""
        card = BasicCard(front="Question", back="Answer", source="test.txt")

        json_str = card.to_json()
        data = json.loads(json_str)

        assert data["front"] == "Question"
        assert data["back"] == "Answer"

    def test_from_dict(self):
        """Test creating card from dictionary."""
        data = {
            "id": "test-id",
            "type": "basic",
            "front": "Question",
            "back": "Answer",
            "source": "test.txt",
            "tags": ["tag1"],
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00",
            "status": "draft",
        }

        card = BasicCard.from_dict(data)

        assert card.id == "test-id"
        assert card.front == "Question"
        assert card.back == "Answer"
        assert isinstance(card.created_at, datetime)

    def test_mark_modified_updates_timestamp(self):
        """Test that mark_modified updates timestamp."""
        card = BasicCard(front="Question", back="Answer", source="test.txt")

        original_time = card.modified_at
        card.mark_modified()

        assert card.modified_at > original_time


class TestClozeCard:
    """Tests for ClozeCard model."""

    def test_create_cloze_card(self):
        """Test creating a cloze card."""
        card = ClozeCard(
            text="The capital of France is {{c1::Paris}}.",
            source="test.txt",
        )

        assert "{{c1::Paris}}" in card.text
        assert card.source == "test.txt"
        assert card.type == CardType.CLOZE
        assert card.status == CardStatus.DRAFT

    def test_cloze_card_with_multiple_deletions(self):
        """Test cloze card with multiple deletions."""
        card = ClozeCard(
            text="{{c1::Python}} is a {{c2::programming language}}.",
            source="test.txt",
        )

        assert "{{c1::Python}}" in card.text
        assert "{{c2::programming language}}" in card.text

    def test_to_dict(self):
        """Test converting cloze card to dictionary."""
        card = ClozeCard(
            text="{{c1::Test}}", source="test.txt", tags=["cloze", "test"]
        )

        data = card.to_dict()

        assert data["text"] == "{{c1::Test}}"
        assert data["type"] == "cloze"
        assert data["tags"] == ["cloze", "test"]

    def test_to_json(self):
        """Test converting cloze card to JSON."""
        card = ClozeCard(text="{{c1::Test}}", source="test.txt")

        json_str = card.to_json()
        data = json.loads(json_str)

        assert data["text"] == "{{c1::Test}}"
        assert data["type"] == "cloze"

    def test_from_dict(self):
        """Test creating cloze card from dictionary."""
        data = {
            "id": "test-id",
            "type": "cloze",
            "text": "{{c1::Test}}",
            "source": "test.txt",
            "tags": [],
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00",
            "status": "accepted",
        }

        card = ClozeCard.from_dict(data)

        assert card.id == "test-id"
        assert card.text == "{{c1::Test}}"
        assert card.status == CardStatus.ACCEPTED


class TestCardHelpers:
    """Tests for card helper functions."""

    def test_card_from_dict_basic(self):
        """Test card_from_dict with basic card."""
        data = {
            "type": "basic",
            "front": "Q",
            "back": "A",
            "source": "test.txt",
            "tags": [],
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00",
            "status": "draft",
        }

        card = card_from_dict(data)

        assert isinstance(card, BasicCard)
        assert card.front == "Q"

    def test_card_from_dict_cloze(self):
        """Test card_from_dict with cloze card."""
        data = {
            "type": "cloze",
            "text": "{{c1::Test}}",
            "source": "test.txt",
            "tags": [],
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00",
            "status": "draft",
        }

        card = card_from_dict(data)

        assert isinstance(card, ClozeCard)
        assert card.text == "{{c1::Test}}"

    def test_card_from_json_basic(self):
        """Test card_from_json with basic card."""
        json_str = json.dumps(
            {
                "type": "basic",
                "front": "Q",
                "back": "A",
                "source": "test.txt",
                "tags": [],
                "created_at": "2024-01-01T12:00:00",
                "modified_at": "2024-01-01T12:00:00",
                "status": "draft",
            }
        )

        card = card_from_json(json_str)

        assert isinstance(card, BasicCard)
        assert card.front == "Q"

    def test_card_from_json_cloze(self):
        """Test card_from_json with cloze card."""
        json_str = json.dumps(
            {
                "type": "cloze",
                "text": "{{c1::Test}}",
                "source": "test.txt",
                "tags": [],
                "created_at": "2024-01-01T12:00:00",
                "modified_at": "2024-01-01T12:00:00",
                "status": "draft",
            }
        )

        card = card_from_json(json_str)

        assert isinstance(card, ClozeCard)
        assert card.text == "{{c1::Test}}"


class TestCardStatus:
    """Tests for CardStatus enum."""

    def test_status_values(self):
        """Test card status values."""
        assert CardStatus.DRAFT.value == "draft"
        assert CardStatus.ACCEPTED.value == "accepted"
        assert CardStatus.REJECTED.value == "rejected"


class TestCardType:
    """Tests for CardType enum."""

    def test_type_values(self):
        """Test card type values."""
        assert CardType.BASIC.value == "basic"
        assert CardType.CLOZE.value == "cloze"
