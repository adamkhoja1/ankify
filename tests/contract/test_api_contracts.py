"""Contract tests for API request/response models.

These tests verify that Pydantic models validate correctly
and follow the expected schema contracts.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.web.models.api import (
    CardFilters,
    CardResponse,
    CardUpdate,
    ExportRequest,
    GenerateRequest,
    RefineRequest,
    SessionResponse,
    StatusUpdate,
)


class TestGenerateRequestContract:
    """Contract tests for GenerateRequest model."""

    def test_minimal_valid_request(self) -> None:
        """GenerateRequest with minimal fields should be valid."""
        request = GenerateRequest(sources=["content.txt"])
        assert request.sources == ["content.txt"]

    def test_sources_required(self) -> None:
        """sources field is required."""
        with pytest.raises(ValidationError):
            GenerateRequest()

    def test_sources_cannot_be_empty(self) -> None:
        """sources must have at least one item."""
        with pytest.raises(ValidationError):
            GenerateRequest(sources=[])

    def test_default_provider(self) -> None:
        """Default provider should be 'openai'."""
        request = GenerateRequest(sources=["test.txt"])
        assert request.provider == "openai"

    def test_default_card_types(self) -> None:
        """Default card_types should include basic and cloze."""
        request = GenerateRequest(sources=["test.txt"])
        assert CardType.BASIC in request.card_types
        assert CardType.CLOZE in request.card_types

    def test_default_count_guidance(self) -> None:
        """Default count_guidance should be set."""
        request = GenerateRequest(sources=["test.txt"])
        assert request.count_guidance == "10-15"

    def test_default_tags_empty(self) -> None:
        """Default tags should be empty list."""
        request = GenerateRequest(sources=["test.txt"])
        assert request.tags == []

    def test_full_request(self) -> None:
        """Full request with all fields should be valid."""
        request = GenerateRequest(
            sources=["file1.txt", "file2.txt"],
            provider="anthropic",
            card_types=[CardType.BASIC],
            count_guidance="5-10",
            tags=["tag1", "tag2"],
            user_directives="Focus on key concepts",
        )
        assert len(request.sources) == 2
        assert request.provider == "anthropic"


class TestCardResponseContract:
    """Contract tests for CardResponse model."""

    def test_from_basic_card(self) -> None:
        """CardResponse should correctly convert BasicCard."""
        card = BasicCard(
            front="Question?",
            back="Answer",
            source="test.txt",
            tags=["tag1"],
            status=CardStatus.DRAFT,
        )
        response = CardResponse.from_card(card)

        assert response.id == card.id
        assert response.type == "basic"
        assert response.source == "test.txt"
        assert response.status == "draft"
        assert response.tags == ["tag1"]

    def test_from_cloze_card(self) -> None:
        """CardResponse should correctly convert ClozeCard."""
        card = ClozeCard(
            text="{{c1::answer}}",
            source="test.txt",
            tags=["cloze-tag"],
            status=CardStatus.ACCEPTED,
        )
        response = CardResponse.from_card(card)

        assert response.id == card.id
        assert response.type == "cloze"
        assert response.status == "accepted"

    def test_response_includes_timestamps(self) -> None:
        """CardResponse should include timestamps."""
        card = BasicCard(front="Q", back="A", source="test.txt")
        response = CardResponse.from_card(card)

        assert isinstance(response.created_at, datetime)
        assert isinstance(response.modified_at, datetime)

    def test_response_content_is_dict(self) -> None:
        """CardResponse content should be a dictionary."""
        card = BasicCard(front="Q", back="A", source="test.txt")
        response = CardResponse.from_card(card)

        assert isinstance(response.content, dict)


class TestCardUpdateContract:
    """Contract tests for CardUpdate model."""

    def test_all_fields_optional(self) -> None:
        """All fields in CardUpdate should be optional."""
        update = CardUpdate()
        assert update.front is None
        assert update.back is None
        assert update.text is None
        assert update.tags is None

    def test_partial_update(self) -> None:
        """CardUpdate should allow partial updates."""
        update = CardUpdate(front="New question")
        assert update.front == "New question"
        assert update.back is None

    def test_tags_update(self) -> None:
        """CardUpdate should allow tags update."""
        update = CardUpdate(tags=["new-tag", "another-tag"])
        assert update.tags == ["new-tag", "another-tag"]


class TestStatusUpdateContract:
    """Contract tests for StatusUpdate model."""

    def test_status_required(self) -> None:
        """status field is required."""
        with pytest.raises(ValidationError):
            StatusUpdate()

    def test_accepts_draft_status(self) -> None:
        """StatusUpdate should accept DRAFT status."""
        update = StatusUpdate(status=CardStatus.DRAFT)
        assert update.status == CardStatus.DRAFT

    def test_accepts_accepted_status(self) -> None:
        """StatusUpdate should accept ACCEPTED status."""
        update = StatusUpdate(status=CardStatus.ACCEPTED)
        assert update.status == CardStatus.ACCEPTED

    def test_accepts_rejected_status(self) -> None:
        """StatusUpdate should accept REJECTED status."""
        update = StatusUpdate(status=CardStatus.REJECTED)
        assert update.status == CardStatus.REJECTED


class TestCardFiltersContract:
    """Contract tests for CardFilters model."""

    def test_all_fields_optional(self) -> None:
        """All filter fields should be optional."""
        filters = CardFilters()
        assert filters.status is None
        assert filters.session_id is None
        assert filters.search is None
        assert filters.tags is None

    def test_default_limit(self) -> None:
        """Default limit should be set."""
        filters = CardFilters()
        assert filters.limit == 100

    def test_default_offset(self) -> None:
        """Default offset should be 0."""
        filters = CardFilters()
        assert filters.offset == 0

    def test_limit_minimum(self) -> None:
        """Limit should have minimum of 1."""
        with pytest.raises(ValidationError):
            CardFilters(limit=0)

    def test_limit_maximum(self) -> None:
        """Limit should have maximum of 1000."""
        with pytest.raises(ValidationError):
            CardFilters(limit=1001)

    def test_offset_minimum(self) -> None:
        """Offset should have minimum of 0."""
        with pytest.raises(ValidationError):
            CardFilters(offset=-1)


class TestSessionResponseContract:
    """Contract tests for SessionResponse model."""

    def test_required_fields(self) -> None:
        """SessionResponse should require specific fields."""
        # Should raise if required fields missing
        with pytest.raises(ValidationError):
            SessionResponse()

    def test_valid_session_response(self) -> None:
        """Valid SessionResponse should be constructable."""
        response = SessionResponse(
            id="session-123",
            sources=["file1.txt"],
            provider="openai",
            card_types=["basic"],
            count_guidance="5-10",
            created_at=datetime.now(),
            completed_at=None,
            card_count=10,
            accepted_count=5,
            rejected_count=2,
            pending_count=3,
        )
        assert response.id == "session-123"
        assert response.completed_at is None

    def test_completed_at_optional(self) -> None:
        """completed_at should be optional (None for incomplete sessions)."""
        response = SessionResponse(
            id="session-123",
            sources=["file.txt"],
            provider="openai",
            card_types=["basic"],
            count_guidance="5-10",
            created_at=datetime.now(),
            completed_at=None,
            card_count=0,
            accepted_count=0,
            rejected_count=0,
            pending_count=0,
        )
        assert response.completed_at is None


class TestRefineRequestContract:
    """Contract tests for RefineRequest model."""

    def test_card_id_required(self) -> None:
        """card_id is required."""
        with pytest.raises(ValidationError):
            RefineRequest(feedback="make it shorter")

    def test_feedback_required(self) -> None:
        """feedback is required."""
        with pytest.raises(ValidationError):
            RefineRequest(card_id="card-123")

    def test_valid_refine_request(self) -> None:
        """Valid RefineRequest should be constructable."""
        request = RefineRequest(
            card_id="card-123",
            feedback="Make the question more specific",
        )
        assert request.card_id == "card-123"
        assert request.feedback == "Make the question more specific"


class TestExportRequestContract:
    """Contract tests for ExportRequest model."""

    def test_all_fields_optional_with_defaults(self) -> None:
        """ExportRequest should have sensible defaults."""
        request = ExportRequest()
        assert request.card_ids is None
        assert request.session_id is None
        assert request.format == "csv"
        assert request.deck_name == "Ankification"

    def test_format_options(self) -> None:
        """ExportRequest should accept valid formats."""
        for fmt in ["csv", "ankiconnect", "both"]:
            request = ExportRequest(format=fmt)
            assert request.format == fmt

    def test_custom_deck_name(self) -> None:
        """ExportRequest should accept custom deck name."""
        request = ExportRequest(deck_name="My Custom Deck")
        assert request.deck_name == "My Custom Deck"
