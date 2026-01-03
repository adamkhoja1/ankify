"""Tests for TUI card action functionality."""

from unittest.mock import patch

import pytest

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.config import Config
from ankification.tui.app import AnkificationTUI


class TestAcceptCard:
    """Tests for accept card action."""

    def test_accept_card_changes_status(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_accept_card should change card status to ACCEPTED."""
        app = AnkificationTUI(sample_cards, test_config)
        card = app.cards[app.current_index]
        assert card.status == CardStatus.DRAFT

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
        assert card.status == CardStatus.ACCEPTED

    def test_accept_card_adds_to_undo_stack(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_accept_card should add to undo stack."""
        app = AnkificationTUI(sample_cards, test_config)
        assert len(app.undo_stack) == 0

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
        assert len(app.undo_stack) == 1
        assert app.undo_stack[0] == (0, CardStatus.DRAFT)

    def test_accept_already_accepted(
        self, mixed_status_cards: list[BasicCard], test_config: Config
    ) -> None:
        """Accept on already accepted card should still work."""
        app = AnkificationTUI(mixed_status_cards, test_config)
        app.current_index = 1  # Already accepted card

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
        assert app.cards[1].status == CardStatus.ACCEPTED

    def test_accept_empty_cards(self, test_config: Config) -> None:
        """Accept should handle empty cards."""
        app = AnkificationTUI([], test_config)
        # Should not raise (returns early for empty cards)
        app.action_accept_card()


class TestRejectCard:
    """Tests for reject card action."""

    def test_reject_card_changes_status(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_reject_card should change card status to REJECTED."""
        app = AnkificationTUI(sample_cards, test_config)
        card = app.cards[app.current_index]
        assert card.status == CardStatus.DRAFT

        with patch.object(app, "_update_current_card"):
            app.action_reject_card()
        assert card.status == CardStatus.REJECTED

    def test_reject_card_adds_to_undo_stack(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_reject_card should add to undo stack."""
        app = AnkificationTUI(sample_cards, test_config)
        assert len(app.undo_stack) == 0

        with patch.object(app, "_update_current_card"):
            app.action_reject_card()
        assert len(app.undo_stack) == 1
        assert app.undo_stack[0] == (0, CardStatus.DRAFT)

    def test_reject_empty_cards(self, test_config: Config) -> None:
        """Reject should handle empty cards."""
        app = AnkificationTUI([], test_config)
        # Should not raise (returns early for empty cards)
        app.action_reject_card()


class TestUndoAction:
    """Tests for undo action."""

    def test_undo_restores_previous_status(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_undo should restore previous status."""
        app = AnkificationTUI(sample_cards, test_config)
        card = app.cards[0]
        assert card.status == CardStatus.DRAFT

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
            assert card.status == CardStatus.ACCEPTED

            app.action_undo()
            assert card.status == CardStatus.DRAFT

    def test_undo_moves_to_card_index(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_undo should move to the undone card's index."""
        app = AnkificationTUI(sample_cards, test_config)

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
            app.action_next_card()
            assert app.current_index == 1

            app.action_undo()
            assert app.current_index == 0

    def test_undo_pops_from_stack(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_undo should pop from undo stack."""
        app = AnkificationTUI(sample_cards, test_config)

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
            app.action_next_card()
            app.action_reject_card()
            assert len(app.undo_stack) == 2

            app.action_undo()
            assert len(app.undo_stack) == 1

            app.action_undo()
            assert len(app.undo_stack) == 0

    def test_undo_empty_stack(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_undo should do nothing with empty stack."""
        app = AnkificationTUI(sample_cards, test_config)
        assert len(app.undo_stack) == 0

        # Empty undo stack returns early before widget query
        app.action_undo()
        assert app.current_index == 0

    def test_multiple_undos(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Multiple undos should work correctly."""
        app = AnkificationTUI(sample_cards, test_config)

        with patch.object(app, "_update_current_card"):
            # Accept card 0
            app.action_accept_card()
            # Move to card 1 and reject
            app.action_next_card()
            app.action_reject_card()
            # Move to card 2 and accept
            app.action_next_card()
            app.action_accept_card()

            assert app.cards[0].status == CardStatus.ACCEPTED
            assert app.cards[1].status == CardStatus.REJECTED
            assert app.cards[2].status == CardStatus.ACCEPTED
            assert len(app.undo_stack) == 3

            # Undo all three
            app.action_undo()
            assert app.cards[2].status == CardStatus.DRAFT

            app.action_undo()
            assert app.cards[1].status == CardStatus.DRAFT

            app.action_undo()
            assert app.cards[0].status == CardStatus.DRAFT

            assert len(app.undo_stack) == 0


class TestActionSequences:
    """Tests for sequences of actions."""

    def test_accept_then_reject_same_card(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Accept then reject should update status and stack."""
        app = AnkificationTUI(sample_cards, test_config)
        card = app.cards[0]

        with patch.object(app, "_update_current_card"):
            app.action_accept_card()
            assert card.status == CardStatus.ACCEPTED
            assert len(app.undo_stack) == 1

            app.action_reject_card()
            assert card.status == CardStatus.REJECTED
            assert len(app.undo_stack) == 2

            # Undo should restore ACCEPTED (not DRAFT)
            app.action_undo()
            assert card.status == CardStatus.ACCEPTED

    def test_navigate_and_modify(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Navigation and modification should work together."""
        app = AnkificationTUI(sample_cards, test_config)

        with patch.object(app, "_update_current_card"):
            # Accept first, move, accept second
            app.action_accept_card()
            app.action_next_card()
            app.action_accept_card()

            assert app.cards[0].status == CardStatus.ACCEPTED
            assert app.cards[1].status == CardStatus.ACCEPTED
            assert app.cards[2].status == CardStatus.DRAFT
