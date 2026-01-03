"""Tag editor modal component."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ...cards.models import Card


class TagEditorModal(ModalScreen[list[str] | None]):
    """Modal screen for editing card tags."""

    CSS = """
    TagEditorModal {
        align: center middle;
    }

    #tag-dialog {
        width: 70;
        height: 25;
        border: thick $primary;
        background: $surface;
    }

    #tag-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        background: $primary;
        color: $text;
        height: 3;
    }

    #tag-content {
        width: 100%;
        height: 1fr;
        padding: 2;
    }

    #tag-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #current-tags {
        margin-bottom: 2;
        padding: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #tag-input {
        width: 100%;
        margin-bottom: 1;
    }

    #available-tags {
        margin-top: 1;
        padding: 1;
        border: solid $primary;
        background: $surface-darken-1;
        height: 10;
        overflow-y: auto;
    }

    .tag-item {
        margin-left: 1;
    }

    .tag-current {
        color: $success;
    }

    .tag-available {
        color: $text-muted;
    }

    #tag-buttons {
        dock: bottom;
        width: 100%;
        height: 3;
        align: center middle;
    }
    """

    def __init__(self, card: Card, available_tags: list[str]) -> None:
        """Initialize tag editor modal.

        Args:
            card: Card to edit tags for
            available_tags: List of available tags from config
        """
        super().__init__()
        self.card = card
        self.available_tags = available_tags
        self.current_tags = card.tags.copy()

    def compose(self) -> ComposeResult:
        """Compose tag editor modal."""
        with Container(id="tag-dialog"):
            yield Static("🏷️  Edit Tags", id="tag-title")

            with Container(id="tag-content"):
                yield Static("Current tags:", id="tag-label")
                yield Static(
                    ", ".join(self.current_tags) if self.current_tags else "(none)",
                    id="current-tags",
                )

                yield Static("Add tag:", classes="tag-label")
                yield Input(
                    placeholder="Type tag name or select below...",
                    id="tag-input",
                )

                yield Static("Available tags (click to add):", classes="tag-label")
                with Container(id="available-tags"):
                    yield from self._render_available_tags()

            with Horizontal(id="tag-buttons"):
                yield Button("Done [Enter]", id="done-btn", variant="success")
                yield Button("Clear All", id="clear-btn", variant="warning")
                yield Button("Cancel [Esc]", id="cancel-btn", variant="default")

    def _render_available_tags(self) -> ComposeResult:
        """Render list of available tags."""
        with Vertical():
            for tag in sorted(self.available_tags):
                status = " (current)" if tag in self.current_tags else ""
                is_current = tag in self.current_tags
                classes = "tag-item tag-current" if is_current else "tag-item tag-available"
                yield Static(f"• {tag}{status}", classes=classes)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle tag input submission."""
        tag = event.value.strip()
        if tag and tag not in self.current_tags:
            self.current_tags.append(tag)
            self._update_current_tags_display()

            # Clear input
            event.input.value = ""

    def _update_current_tags_display(self) -> None:
        """Update the current tags display."""
        current_tags_widget = self.query_one("#current-tags", Static)
        current_tags_widget.update(
            ", ".join(self.current_tags) if self.current_tags else "(none)"
        )

        # Refresh available tags to show updated status
        available_container = self.query_one("#available-tags", Container)
        available_container.remove_children()
        with available_container:
            for tag in sorted(self.available_tags):
                status = " (current)" if tag in self.current_tags else ""
                is_current = tag in self.current_tags
                classes = "tag-item tag-current" if is_current else "tag-item tag-available"
                available_container.mount(Static(f"• {tag}{status}", classes=classes))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "done-btn":
            self.dismiss(self.current_tags)
        elif event.button.id == "clear-btn":
            self.current_tags = []
            self._update_current_tags_display()
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:  # type: ignore
        """Handle key press."""
        if event.key == "escape":
            self.dismiss(None)
