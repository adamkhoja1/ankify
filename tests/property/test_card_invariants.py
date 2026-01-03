"""Property-based tests for card model invariants."""

import uuid

from hypothesis import assume, given, settings

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard

from .strategies import (
    basic_card_strategy,
    card_status,
    card_text,
    cloze_card_strategy,
    source,
    tag_list,
)


class TestBasicCardInvariants:
    """Property-based tests for BasicCard invariants."""

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_type_is_always_basic(self, card: BasicCard) -> None:
        """BasicCard.type is always CardType.BASIC."""
        assert card.type == CardType.BASIC

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_id_is_valid_uuid(self, card: BasicCard) -> None:
        """Card ID is always a valid UUID string."""
        # Should not raise
        uuid.UUID(card.id)

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_id_is_unique_per_instance(self, card: BasicCard) -> None:
        """Each card instance has a unique ID."""
        other_card = BasicCard(front="Q", back="A", source="test.txt")
        assert card.id != other_card.id

    @given(front=card_text, back=card_text, src=source)
    @settings(max_examples=50)
    def test_front_back_source_preserved(self, front: str, back: str, src: str) -> None:
        """Front, back, and source are preserved exactly."""
        card = BasicCard(front=front, back=back, source=src)
        assert card.front == front
        assert card.back == back
        assert card.source == src

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_tags_is_always_list(self, card: BasicCard) -> None:
        """Tags is always a list (never None or other type)."""
        assert isinstance(card.tags, list)
        assert all(isinstance(t, str) for t in card.tags)

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_status_is_valid_enum(self, card: BasicCard) -> None:
        """Status is always a valid CardStatus enum value."""
        assert isinstance(card.status, CardStatus)
        assert card.status in [CardStatus.DRAFT, CardStatus.ACCEPTED, CardStatus.REJECTED]

    @given(basic_card_strategy())
    @settings(max_examples=100)
    def test_created_at_before_or_equal_modified_at(self, card: BasicCard) -> None:
        """created_at is always <= modified_at."""
        assert card.created_at <= card.modified_at

    @given(tags=tag_list)
    @settings(max_examples=50)
    def test_tags_preserved_in_order(self, tags: list[str]) -> None:
        """Tags list order is preserved."""
        card = BasicCard(front="Q", back="A", source="test.txt", tags=tags)
        assert card.tags == tags

    @given(status=card_status)
    @settings(max_examples=10)
    def test_status_preserved(self, status: CardStatus) -> None:
        """Status is preserved when set."""
        card = BasicCard(front="Q", back="A", source="test.txt", status=status)
        assert card.status == status


class TestClozeCardInvariants:
    """Property-based tests for ClozeCard invariants."""

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_type_is_always_cloze(self, card: ClozeCard) -> None:
        """ClozeCard.type is always CardType.CLOZE."""
        assert card.type == CardType.CLOZE

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_id_is_valid_uuid(self, card: ClozeCard) -> None:
        """Card ID is always a valid UUID string."""
        uuid.UUID(card.id)

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_text_contains_cloze_deletion(self, card: ClozeCard) -> None:
        """Cloze card text contains at least one cloze deletion."""
        # Cloze deletions are in format {{c1::text}}
        assert "{{c" in card.text
        assert "::" in card.text
        assert "}}" in card.text

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_tags_is_always_list(self, card: ClozeCard) -> None:
        """Tags is always a list."""
        assert isinstance(card.tags, list)
        assert all(isinstance(t, str) for t in card.tags)

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_status_is_valid_enum(self, card: ClozeCard) -> None:
        """Status is always a valid CardStatus enum value."""
        assert isinstance(card.status, CardStatus)

    @given(cloze_card_strategy())
    @settings(max_examples=100)
    def test_created_at_before_or_equal_modified_at(self, card: ClozeCard) -> None:
        """created_at is always <= modified_at."""
        assert card.created_at <= card.modified_at


class TestCardTypeDistinction:
    """Tests ensuring card types remain distinct."""

    @given(basic_card_strategy())
    @settings(max_examples=50)
    def test_basic_card_is_not_cloze(self, card: BasicCard) -> None:
        """BasicCard is never a ClozeCard."""
        assert not isinstance(card, ClozeCard)
        assert card.type != CardType.CLOZE

    @given(cloze_card_strategy())
    @settings(max_examples=50)
    def test_cloze_card_is_not_basic(self, card: ClozeCard) -> None:
        """ClozeCard is never a BasicCard."""
        assert not isinstance(card, BasicCard)
        assert card.type != CardType.BASIC

    @given(basic_card_strategy(), cloze_card_strategy())
    @settings(max_examples=50)
    def test_different_types_have_different_ids(
        self, basic: BasicCard, cloze: ClozeCard
    ) -> None:
        """Different card instances have different IDs."""
        assert basic.id != cloze.id


class TestStatusTransitions:
    """Tests for card status transitions."""

    @given(basic_card_strategy())
    @settings(max_examples=50)
    def test_status_can_be_changed(self, card: BasicCard) -> None:
        """Card status can be changed to any valid status."""
        for new_status in CardStatus:
            card.status = new_status
            assert card.status == new_status

    @given(basic_card_strategy(), card_status)
    @settings(max_examples=50)
    def test_status_change_idempotent(self, card: BasicCard, status: CardStatus) -> None:
        """Setting the same status twice has no additional effect."""
        card.status = status
        first_status = card.status
        card.status = status
        assert card.status == first_status
