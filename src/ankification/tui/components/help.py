"""Help modal component."""

from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class HelpModal(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 80;
        height: 30;
        border: thick $primary;
        background: $surface;
    }

    #help-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        background: $primary;
        color: $text;
        height: 3;
    }

    #help-content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    .help-section {
        margin: 1 2;
    }

    .help-section-title {
        text-style: bold;
        color: $accent;
    }

    .help-shortcut {
        margin-left: 2;
    }

    #help-close {
        dock: bottom;
        width: 100%;
        height: 3;
    }
    """

    SHORTCUTS = {
        "Navigation": [
            ("j / ↓", "Next card"),
            ("k / ↑", "Previous card"),
            ("g", "Go to first card"),
            ("G", "Go to last card"),
            ("Ctrl+D", "Page down (5 cards)"),
            ("Ctrl+U", "Page up (5 cards)"),
        ],
        "Actions": [
            ("a", "Accept card"),
            ("d", "Reject card"),
            ("e", "Edit card"),
            ("r", "Refine with LLM"),
            ("t", "Edit tags"),
            ("u", "Undo last action"),
            ("Space", "Toggle accept/pending"),
            ("Shift+Space", "Toggle reject/pending"),
        ],
        "View": [
            ("Ctrl+B", "Toggle sidebar"),
            ("/", "Search/filter cards"),
            ("n", "Next search result"),
            ("N", "Previous result"),
            ("?", "Show this help"),
            ("q", "Quit"),
        ],
        "Bulk Actions": [
            ("v", "Enter select mode"),
            ("j/k in select", "Extend selection"),
            ("a in select", "Accept selected"),
            ("d in select", "Reject selected"),
            ("t in select", "Tag selected"),
            ("Esc", "Exit select mode"),
        ],
    }

    def compose(self) -> ComposeResult:
        """Compose help modal."""
        with Container(id="help-dialog"):
            yield Static("⌨️  Keyboard Shortcuts", id="help-title")

            with Container(id="help-content"):
                for section, shortcuts in self.SHORTCUTS.items():
                    with Container(classes="help-section"):
                        yield Static(section, classes="help-section-title")
                        for key, description in shortcuts:
                            yield Static(
                                f"  {key:20} {description}",
                                classes="help-shortcut",
                            )

            yield Button("Close [Esc]", id="help-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.app.pop_screen()

    def on_key(self, event) -> None:  # type: ignore
        """Handle key press."""
        if event.key == "escape":
            self.app.pop_screen()
