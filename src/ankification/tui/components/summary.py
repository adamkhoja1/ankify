"""Summary screen shown on quit."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ...cards.models import Card, CardStatus


class SummaryScreen(ModalScreen[str | None]):
    """Summary screen showing review results and export options."""

    CSS = """
    SummaryScreen {
        align: center middle;
    }

    #summary-dialog {
        width: 70;
        height: 25;
        border: thick $success;
        background: $surface;
    }

    #summary-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        background: $success;
        color: $text;
        height: 3;
    }

    #summary-content {
        width: 100%;
        height: 1fr;
        padding: 2;
    }

    .summary-section {
        margin-bottom: 2;
    }

    .summary-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .stat-line {
        margin-left: 2;
    }

    .stat-accepted {
        color: $success;
    }

    .stat-rejected {
        color: $error;
    }

    .stat-pending {
        color: $warning;
    }

    #export-options {
        margin-top: 2;
    }

    #summary-buttons {
        dock: bottom;
        width: 100%;
        height: 5;
        align: center middle;
    }

    .button-row {
        width: 100%;
        align: center middle;
    }
    """

    def __init__(self, cards: list[Card]) -> None:
        """Initialize summary screen.

        Args:
            cards: List of all cards reviewed
        """
        super().__init__()
        self.cards = cards
        self._calculate_stats()

    def _calculate_stats(self) -> None:
        """Calculate statistics from cards."""
        self.total = len(self.cards)
        self.accepted = sum(1 for c in self.cards if c.status == CardStatus.ACCEPTED)
        self.rejected = sum(1 for c in self.cards if c.status == CardStatus.REJECTED)
        self.pending = sum(1 for c in self.cards if c.status == CardStatus.DRAFT)

        self.accepted_pct = (
            int(self.accepted / self.total * 100) if self.total > 0 else 0
        )
        self.rejected_pct = (
            int(self.rejected / self.total * 100) if self.total > 0 else 0
        )
        self.pending_pct = (
            int(self.pending / self.total * 100) if self.total > 0 else 0
        )

    def compose(self) -> ComposeResult:
        """Compose summary screen."""
        with Container(id="summary-dialog"):
            yield Static("✓ Review Complete", id="summary-title")

            with Container(id="summary-content"):
                # Statistics section
                with Container(classes="summary-section"):
                    yield Static("Session Summary:", classes="summary-label")
                    yield Static(
                        f"  Total cards:     {self.total}",
                        classes="stat-line",
                    )
                    yield Static(
                        f"  Accepted:        {self.accepted} ({self.accepted_pct}%)",
                        classes="stat-line stat-accepted",
                    )
                    yield Static(
                        f"  Rejected:        {self.rejected} ({self.rejected_pct}%)",
                        classes="stat-line stat-rejected",
                    )
                    yield Static(
                        f"  Still pending:   {self.pending} ({self.pending_pct}%)",
                        classes="stat-line stat-pending",
                    )

                # Export options
                with Container(id="export-options"):
                    yield Static(
                        f"Export {self.accepted} accepted cards?",
                        classes="summary-label",
                    )

            with Vertical(id="summary-buttons"):
                with Horizontal(classes="button-row"):
                    yield Button("[1] CSV", id="export-csv", variant="success")
                    yield Button(
                        "[2] AnkiConnect", id="export-anki", variant="success"
                    )
                    yield Button("[3] Both", id="export-both", variant="primary")

                with Horizontal(classes="button-row"):
                    if self.pending > 0:
                        yield Button(
                            "[r] Review Pending", id="review-pending", variant="warning"
                        )
                    yield Button(
                        "[q] Quit Without Export", id="quit-no-export", variant="default"
                    )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_id = event.button.id

        if button_id == "export-csv":
            self.dismiss("csv")
        elif button_id == "export-anki":
            self.dismiss("ankiconnect")
        elif button_id == "export-both":
            self.dismiss("both")
        elif button_id == "review-pending":
            self.dismiss("review")
        elif button_id == "quit-no-export":
            self.dismiss("quit")

    def on_key(self, event) -> None:  # type: ignore
        """Handle key press."""
        if event.key == "1":
            self.dismiss("csv")
        elif event.key == "2":
            self.dismiss("ankiconnect")
        elif event.key == "3":
            self.dismiss("both")
        elif event.key == "r":
            self.dismiss("review")
        elif event.key == "q":
            self.dismiss("quit")
        elif event.key == "escape":
            self.dismiss("quit")
