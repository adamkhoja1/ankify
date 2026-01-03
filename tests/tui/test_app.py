"""Tests for TUI app initialization and structure."""

import pytest

from ankification.cards.models import BasicCard, CardStatus, ClozeCard
from ankification.config import Config
from ankification.tui.app import AnkificationTUI


class TestAnkificationTUIInit:
    """Tests for TUI app initialization."""

    def test_app_initializes_with_cards(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should initialize with provided cards."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.cards == sample_cards
        assert len(app.cards) == 3

    def test_app_initializes_with_config(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should store config."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.config == test_config

    def test_app_initializes_with_none_config(
        self, sample_cards: list[BasicCard | ClozeCard]
    ) -> None:
        """App should handle None config."""
        app = AnkificationTUI(sample_cards, None)

        assert app.config is None

    def test_app_starts_at_first_card(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should start with current_index at 0."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.current_index == 0

    def test_app_sidebar_visible_by_default(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Sidebar should be visible by default."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.sidebar_visible is True

    def test_app_empty_undo_stack(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Undo stack should start empty."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.undo_stack == []

    def test_app_no_export_choice(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Export choice should be None initially."""
        app = AnkificationTUI(sample_cards, test_config)

        assert app.export_choice is None


class TestAnkificationTUIBindings:
    """Tests for TUI key bindings configuration."""

    def test_app_has_quit_binding(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have quit binding."""
        app = AnkificationTUI(sample_cards, test_config)

        # BINDINGS are tuples of (key, action, description)
        binding_keys = [b[0] for b in app.BINDINGS]
        assert "q" in binding_keys

    def test_app_has_navigation_bindings(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have navigation bindings (j/k)."""
        app = AnkificationTUI(sample_cards, test_config)

        binding_keys = [b[0] for b in app.BINDINGS]
        assert "j" in binding_keys
        assert "k" in binding_keys

    def test_app_has_status_bindings(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have accept/reject bindings."""
        app = AnkificationTUI(sample_cards, test_config)

        binding_keys = [b[0] for b in app.BINDINGS]
        assert "a" in binding_keys
        assert "d" in binding_keys

    def test_app_has_edit_bindings(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have edit bindings."""
        app = AnkificationTUI(sample_cards, test_config)

        binding_keys = [b[0] for b in app.BINDINGS]
        assert "e" in binding_keys
        assert "r" in binding_keys
        assert "t" in binding_keys

    def test_app_has_undo_binding(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have undo binding."""
        app = AnkificationTUI(sample_cards, test_config)

        binding_keys = [b[0] for b in app.BINDINGS]
        assert "u" in binding_keys

    def test_app_has_help_binding(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """App should have help binding."""
        app = AnkificationTUI(sample_cards, test_config)

        binding_keys = [b[0] for b in app.BINDINGS]
        assert "?" in binding_keys


class TestAnkificationTUIEmptyCards:
    """Tests for TUI with empty card list."""

    def test_app_handles_empty_cards(self, test_config: Config) -> None:
        """App should handle empty card list."""
        app = AnkificationTUI([], test_config)

        assert app.cards == []
        assert app.current_index == 0

    def test_progress_text_empty_cards(self, test_config: Config) -> None:
        """Progress text should handle empty cards."""
        app = AnkificationTUI([], test_config)
        text = app._get_progress_text()

        assert "No cards" in text


class TestAnkificationTUIProgressText:
    """Tests for progress text generation."""

    def test_progress_text_all_draft(
        self, sample_cards: list[BasicCard | ClozeCard], test_config: Config
    ) -> None:
        """Progress text should show pending count for draft cards."""
        app = AnkificationTUI(sample_cards, test_config)
        text = app._get_progress_text()

        assert "Pending:" in text
        assert "Accepted:" in text
        assert "Rejected:" in text

    def test_progress_text_mixed_status(
        self, mixed_status_cards: list[BasicCard], test_config: Config
    ) -> None:
        """Progress text should show accurate counts."""
        app = AnkificationTUI(mixed_status_cards, test_config)
        text = app._get_progress_text()

        # 1 accepted, 1 rejected, 2 pending
        assert "Accepted: 1" in text
        assert "Rejected: 1" in text
        assert "Pending: 2" in text
