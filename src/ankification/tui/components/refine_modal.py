"""LLM refinement modal component."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ...cards.models import Card


class RefineModal(ModalScreen[tuple[str, Card] | None]):
    """Modal screen for refining a card with LLM feedback."""

    CSS = """
    RefineModal {
        align: center middle;
    }

    #refine-dialog {
        width: 80;
        height: 20;
        border: thick $primary;
        background: $surface;
    }

    #refine-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        background: $primary;
        color: $text;
        height: 3;
    }

    #refine-content {
        width: 100%;
        height: 1fr;
        padding: 2;
    }

    #refine-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #feedback-input {
        width: 100%;
        margin-bottom: 2;
    }

    #refine-hint {
        color: $text-muted;
        margin-bottom: 1;
    }

    #refine-buttons {
        dock: bottom;
        width: 100%;
        height: 3;
        align: center middle;
    }
    """

    def __init__(self, card: Card) -> None:
        """Initialize refinement modal.

        Args:
            card: Card to refine
        """
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        """Compose refinement modal."""
        with Container(id="refine-dialog"):
            yield Static("🤖 Refine with LLM", id="refine-title")

            with Container(id="refine-content"):
                yield Static("Feedback for refinement:", id="refine-label")
                yield Static(
                    "Examples: 'make it shorter', 'add more detail', 'simplify language'",
                    id="refine-hint",
                )
                yield Input(
                    placeholder="Type your feedback here...",
                    id="feedback-input",
                )

            with Horizontal(id="refine-buttons"):
                yield Button("Submit [Enter]", id="submit-btn", variant="success")
                yield Button("Cancel [Esc]", id="cancel-btn", variant="default")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit-btn":
            feedback_input = self.query_one("#feedback-input", Input)
            feedback = feedback_input.value.strip()

            if feedback:
                self.dismiss((feedback, self.card))
            else:
                # Show error - feedback is required
                feedback_input.border_title = "Feedback required!"
        else:
            self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        submit_btn = self.query_one("#submit-btn", Button)
        await self.on_button_pressed(Button.Pressed(submit_btn))

    def on_key(self, event) -> None:  # type: ignore
        """Handle key press."""
        if event.key == "escape":
            self.dismiss(None)
