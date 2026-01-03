"""Main TUI application for card review."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from ..cards.models import Card, CardStatus
from ..config import Config
from .components.card_viewer import CardViewer
from .components.editor import EditorModal
from .components.help import HelpModal
from .components.refine_modal import RefineModal
from .components.sidebar import CardSidebar
from .components.summary import SummaryScreen
from .components.tag_editor import TagEditorModal


class AnkificationTUI(App):
    """Textual app for reviewing and editing flashcards."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
    }

    #sidebar {
        width: 25;
        border-right: solid $primary;
    }

    #content {
        width: 1fr;
    }

    .card-status-accepted {
        color: $success;
    }

    .card-status-rejected {
        color: $error;
    }

    .card-status-draft {
        color: $warning;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("j", "next_card", "Next"),
        ("k", "prev_card", "Previous"),
        ("a", "accept_card", "Accept"),
        ("d", "reject_card", "Reject"),
        ("e", "edit_card", "Edit"),
        ("r", "refine_card", "Refine"),
        ("t", "edit_tags", "Tags"),
        ("/", "search", "Search"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("u", "undo", "Undo"),
    ]

    def __init__(self, cards: list[Card], config: Config | None = None) -> None:
        """Initialize TUI app.

        Args:
            cards: List of cards to review
            config: Optional configuration
        """
        super().__init__()
        self.cards = cards
        self.config = config
        self.current_index = 0
        self.sidebar_visible = True
        self.undo_stack: list[tuple[int, CardStatus]] = []
        self.export_choice: str | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with Container(id="main-container"):
            with Horizontal():
                yield CardSidebar(self.cards, id="sidebar")
                with Vertical(id="content"):
                    yield CardViewer(self.cards[0] if self.cards else None)
                    yield Static(self._get_progress_text(), id="progress")
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        self.title = "Ankification Review"
        self.sub_title = f"{len(self.cards)} cards"
        self._update_current_card()

    def _update_current_card(self) -> None:
        """Update display to show current card."""
        if not self.cards:
            return

        card = self.cards[self.current_index]

        # Update card viewer
        viewer = self.query_one(CardViewer)
        viewer.card = card
        viewer.refresh()

        # Update sidebar
        sidebar = self.query_one(CardSidebar)
        sidebar.current_index = self.current_index
        sidebar.refresh()

        # Update progress
        progress = self.query_one("#progress", Static)
        progress.update(self._get_progress_text())

    def _get_progress_text(self) -> str:
        """Get progress bar text."""
        if not self.cards:
            return "No cards"

        total = len(self.cards)
        accepted = sum(1 for c in self.cards if c.status == CardStatus.ACCEPTED)
        rejected = sum(1 for c in self.cards if c.status == CardStatus.REJECTED)
        pending = sum(1 for c in self.cards if c.status == CardStatus.DRAFT)

        progress_pct = (accepted + rejected) / total
        bar_width = 20
        filled = int(progress_pct * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        return (
            f"Progress: [{bar}] "
            f"Accepted: {accepted}  Rejected: {rejected}  Pending: {pending}"
        )

    def action_next_card(self) -> None:
        """Move to next card."""
        if self.current_index < len(self.cards) - 1:
            self.current_index += 1
            self._update_current_card()

    def action_prev_card(self) -> None:
        """Move to previous card."""
        if self.current_index > 0:
            self.current_index -= 1
            self._update_current_card()

    def action_accept_card(self) -> None:
        """Accept current card."""
        if not self.cards:
            return

        card = self.cards[self.current_index]
        old_status = card.status
        card.status = CardStatus.ACCEPTED
        self.undo_stack.append((self.current_index, old_status))
        self._update_current_card()

    def action_reject_card(self) -> None:
        """Reject current card."""
        if not self.cards:
            return

        card = self.cards[self.current_index]
        old_status = card.status
        card.status = CardStatus.REJECTED
        self.undo_stack.append((self.current_index, old_status))
        self._update_current_card()

    def action_undo(self) -> None:
        """Undo last action."""
        if not self.undo_stack:
            return

        index, old_status = self.undo_stack.pop()
        self.cards[index].status = old_status
        self.current_index = index
        self._update_current_card()

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display
        self.sidebar_visible = sidebar.display

    async def action_edit_card(self) -> None:
        """Edit current card."""
        if not self.cards:
            return

        card = self.cards[self.current_index]
        edited_card = await self.push_screen(EditorModal(card), wait_for_dismiss=True)

        if edited_card:
            # Card was modified
            self.cards[self.current_index] = edited_card
            self._update_current_card()
            self.notify("Card updated", severity="information")

    async def action_refine_card(self) -> None:
        """Refine card with LLM."""
        if not self.cards:
            return

        card = self.cards[self.current_index]
        result = await self.push_screen(RefineModal(card), wait_for_dismiss=True)

        if result:
            feedback, card_to_refine = result
            self.notify(f"Refining card with feedback: '{feedback}'...", severity="information")

            # TODO: Actually call LLM provider to refine
            # For now, just show a notification
            self.notify(
                "LLM refinement will be implemented when integrated with CardGenerator",
                severity="warning",
            )

    async def action_edit_tags(self) -> None:
        """Edit card tags."""
        if not self.cards:
            return

        card = self.cards[self.current_index]
        available_tags = self.config.tags.pools if self.config else []

        new_tags = await self.push_screen(
            TagEditorModal(card, available_tags), wait_for_dismiss=True
        )

        if new_tags is not None:
            card.tags = new_tags
            self._update_current_card()
            self.notify(f"Tags updated: {', '.join(new_tags)}", severity="information")

    def action_search(self) -> None:
        """Search/filter cards."""
        # TODO: Implement search modal
        self.notify("Search not yet implemented", severity="warning")

    async def action_show_help(self) -> None:
        """Show help modal."""
        await self.push_screen(HelpModal(), wait_for_dismiss=True)

    async def action_quit(self) -> None:
        """Quit with summary screen."""
        result = await self.push_screen(SummaryScreen(self.cards), wait_for_dismiss=True)

        if result and result != "quit" and result != "review":
            self.export_choice = result
            self.exit()
        elif result == "review":
            # Filter to pending cards
            pending_cards = [c for c in self.cards if c.status == CardStatus.DRAFT]
            if pending_cards:
                # Find first pending card
                for i, card in enumerate(self.cards):
                    if card.status == CardStatus.DRAFT:
                        self.current_index = i
                        self._update_current_card()
                        break
        else:
            # Quit without export
            self.exit()


def run_tui(cards: list[Card], config: Config | None = None) -> tuple[list[Card], str | None]:
    """Run the TUI and return modified cards and export choice.

    Args:
        cards: Cards to review
        config: Optional configuration

    Returns:
        Tuple of (modified cards, export choice)
        Export choice can be: 'csv', 'ankiconnect', 'both', or None
    """
    app = AnkificationTUI(cards, config)
    app.run()
    return cards, app.export_choice
