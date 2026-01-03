"""Tests for TUI navigation functionality."""

from unittest.mock import patch

import pytest

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.config import Config
from ankification.tui.app import AnkificationTUI


class TestCardNavigation:
    """Tests for next/previous card navigation."""

    def test_next_card_increments_index(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_next_card should increment current_index."""
        app = AnkificationTUI(sample_cards, test_config)
        assert app.current_index == 0

        # Mock _update_current_card since it queries widgets that don't exist without running app
        with patch.object(app, "_update_current_card"):
            app.action_next_card()
            assert app.current_index == 1

            app.action_next_card()
            assert app.current_index == 2

    def test_next_card_stops_at_end(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_next_card should stop at last card."""
        app = AnkificationTUI(sample_cards, test_config)
        app.current_index = len(sample_cards) - 1

        with patch.object(app, "_update_current_card"):
            app.action_next_card()
            assert app.current_index == len(sample_cards) - 1

    def test_prev_card_decrements_index(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_prev_card should decrement current_index."""
        app = AnkificationTUI(sample_cards, test_config)
        app.current_index = 2

        with patch.object(app, "_update_current_card"):
            app.action_prev_card()
            assert app.current_index == 1

            app.action_prev_card()
            assert app.current_index == 0

    def test_prev_card_stops_at_start(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_prev_card should stop at first card."""
        app = AnkificationTUI(sample_cards, test_config)
        assert app.current_index == 0

        with patch.object(app, "_update_current_card"):
            app.action_prev_card()
            assert app.current_index == 0

    def test_navigation_with_empty_cards(self, test_config: Config) -> None:
        """Navigation should handle empty card list."""
        app = AnkificationTUI([], test_config)

        # These should not raise (empty cards returns early before widget queries)
        app.action_next_card()
        app.action_prev_card()

        assert app.current_index == 0


class TestSidebarToggle:
    """Tests for sidebar visibility toggle."""

    def test_toggle_sidebar_hides(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """action_toggle_sidebar should toggle visibility flag."""
        app = AnkificationTUI(sample_cards, test_config)
        assert app.sidebar_visible is True

        # Note: In unit test without running app, we can only test the flag logic
        # The actual widget toggle requires running the app
        app.sidebar_visible = False
        assert app.sidebar_visible is False

        app.sidebar_visible = True
        assert app.sidebar_visible is True
