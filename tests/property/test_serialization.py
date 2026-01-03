"""Property-based tests for serialization roundtrips."""

import json
from datetime import datetime
from typing import Any

from hypothesis import assume, given, settings

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard

from .strategies import (
    any_card_strategy,
    basic_card_strategy,
    cloze_card_strategy,
    tag_list,
)


class TestBasicCardSerialization:
    """Property tests for BasicCard serialization."""

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_roundtrip(self, card: BasicCard) -> None:
        """to_dict -> from_dict preserves all card data."""
        card_dict = card.to_dict()

        # Reconstruct card from dict
        restored = BasicCard(
            id=card_dict["id"],
            front=card_dict["front"],
            back=card_dict["back"],
            source=card_dict["source"],
            tags=card_dict["tags"],
            status=CardStatus(card_dict["status"]),
        )

        assert restored.id == card.id
        assert restored.front == card.front
        assert restored.back == card.back
        assert restored.source == card.source
        assert restored.tags == card.tags
        assert restored.status == card.status
        assert restored.type == card.type

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_is_json_serializable(self, card: BasicCard) -> None:
        """to_dict output can be JSON serialized and deserialized."""
        card_dict = card.to_dict()

        # Should not raise
        json_str = json.dumps(card_dict)
        restored_dict = json.loads(json_str)

        assert restored_dict == card_dict

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_contains_required_fields(self, card: BasicCard) -> None:
        """to_dict output contains all required fields."""
        card_dict = card.to_dict()

        required_fields = {"id", "type", "front", "back", "source", "tags", "status"}
        assert required_fields.issubset(card_dict.keys())

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_type_is_basic(self, card: BasicCard) -> None:
        """to_dict type field is always 'basic'."""
        card_dict = card.to_dict()
        assert card_dict["type"] == "basic"


class TestClozeCardSerialization:
    """Property tests for ClozeCard serialization."""

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_roundtrip(self, card: ClozeCard) -> None:
        """to_dict -> from_dict preserves all card data."""
        card_dict = card.to_dict()

        restored = ClozeCard(
            id=card_dict["id"],
            text=card_dict["text"],
            source=card_dict["source"],
            tags=card_dict["tags"],
            status=CardStatus(card_dict["status"]),
        )

        assert restored.id == card.id
        assert restored.text == card.text
        assert restored.source == card.source
        assert restored.tags == card.tags
        assert restored.status == card.status
        assert restored.type == card.type

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_is_json_serializable(self, card: ClozeCard) -> None:
        """to_dict output can be JSON serialized and deserialized."""
        card_dict = card.to_dict()

        json_str = json.dumps(card_dict)
        restored_dict = json.loads(json_str)

        assert restored_dict == card_dict

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_contains_required_fields(self, card: ClozeCard) -> None:
        """to_dict output contains all required fields."""
        card_dict = card.to_dict()

        required_fields = {"id", "type", "text", "source", "tags", "status"}
        assert required_fields.issubset(card_dict.keys())

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_to_dict_type_is_cloze(self, card: ClozeCard) -> None:
        """to_dict type field is always 'cloze'."""
        card_dict = card.to_dict()
        assert card_dict["type"] == "cloze"


class TestTagSerialization:
    """Property tests for tag serialization."""

    @given(tags=tag_list)
    @settings(max_examples=50)
    def test_tags_serialization_preserves_order(self, tags: list[str]) -> None:
        """Tags are serialized in order."""
        card = BasicCard(front="Q", back="A", source="test.txt", tags=tags)
        card_dict = card.to_dict()

        assert card_dict["tags"] == tags

    @given(tags=tag_list)
    @settings(max_examples=50)
    def test_tags_json_roundtrip(self, tags: list[str]) -> None:
        """Tags survive JSON serialization."""
        card = BasicCard(front="Q", back="A", source="test.txt", tags=tags)
        card_dict = card.to_dict()

        json_str = json.dumps(card_dict)
        restored = json.loads(json_str)

        assert restored["tags"] == tags


class TestMixedCardSerialization:
    """Property tests for mixed card collections."""

    @given(any_card_strategy())
    @settings(max_examples=100)
    def test_type_field_matches_card_type(self, card: BasicCard | ClozeCard) -> None:
        """Serialized type field matches actual card type."""
        card_dict = card.to_dict()

        if isinstance(card, BasicCard):
            assert card_dict["type"] == "basic"
        else:
            assert card_dict["type"] == "cloze"

    @given(any_card_strategy())
    @settings(max_examples=100)
    def test_id_preserved_in_serialization(self, card: BasicCard | ClozeCard) -> None:
        """Card ID is preserved through serialization."""
        original_id = card.id
        card_dict = card.to_dict()

        assert card_dict["id"] == original_id


class TestStatusSerialization:
    """Property tests for status serialization."""

    @given(basic_card_strategy())
    @settings(max_examples=50)
    def test_status_serializes_to_string(self, card: BasicCard) -> None:
        """Status serializes to string value."""
        card_dict = card.to_dict()
        assert isinstance(card_dict["status"], str)
        assert card_dict["status"] in ["draft", "accepted", "rejected"]

    @given(basic_card_strategy())
    @settings(max_examples=50)
    def test_status_roundtrip(self, card: BasicCard) -> None:
        """Status survives serialization roundtrip."""
        original_status = card.status
        card_dict = card.to_dict()
        restored_status = CardStatus(card_dict["status"])

        assert restored_status == original_status
