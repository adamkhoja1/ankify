"""Card editor modal component."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea

from ...cards.models import BasicCard, Card, ClozeCard


class EditorModal(ModalScreen[Card | None]):
    """Modal screen for editing a card with side-by-side diff view."""

    CSS = """
    EditorModal {
        align: center middle;
    }

    #editor-dialog {
        width: 90;
        height: 35;
        border: thick $primary;
        background: $surface;
    }

    #editor-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        background: $primary;
        color: $text;
        height: 3;
    }

    #editor-content {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    .editor-section {
        margin-bottom: 1;
    }

    .editor-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #editor-buttons {
        dock: bottom;
        width: 100%;
        height: 3;
        align: center middle;
    }

    .diff-container {
        height: auto;
    }

    .original-label {
        color: $warning;
    }

    .edited-label {
        color: $success;
    }
    """

    def __init__(self, card: Card) -> None:
        """Initialize editor modal.

        Args:
            card: Card to edit
        """
        super().__init__()
        self.card = card
        self.original_card = card.model_copy(deep=True)  # Deep copy for comparison

    def compose(self) -> ComposeResult:
        """Compose editor modal."""
        with Container(id="editor-dialog"):
            yield Static("✏️  Edit Card", id="editor-title")

            with Container(id="editor-content"):
                if isinstance(self.card, BasicCard):
                    yield from self._compose_basic_editor()
                else:
                    assert isinstance(self.card, ClozeCard)
                    yield from self._compose_cloze_editor()

            with Horizontal(id="editor-buttons"):
                yield Button("Save [Ctrl+S]", id="save-btn", variant="success")
                yield Button("Cancel [Esc]", id="cancel-btn", variant="default")

    def _compose_basic_editor(self) -> ComposeResult:
        """Compose editor for basic card."""
        assert isinstance(self.card, BasicCard)

        with Vertical():
            # Front field
            with Container(classes="editor-section"):
                yield Static("Front:", classes="editor-label")
                with Horizontal(classes="diff-container"):
                    with Vertical():
                        yield Static("Original:", classes="original-label")
                        yield Static(self.original_card.front, id="front-original")  # type: ignore
                    with Vertical():
                        yield Static("Editing:", classes="edited-label")
                        yield TextArea(self.card.front, id="front-input")

            # Back field
            with Container(classes="editor-section"):
                yield Static("Back:", classes="editor-label")
                with Horizontal(classes="diff-container"):
                    with Vertical():
                        yield Static("Original:", classes="original-label")
                        yield Static(self.original_card.back, id="back-original")  # type: ignore
                    with Vertical():
                        yield Static("Editing:", classes="edited-label")
                        yield TextArea(self.card.back, id="back-input")

    def _compose_cloze_editor(self) -> ComposeResult:
        """Compose editor for cloze card."""
        assert isinstance(self.card, ClozeCard)

        with Vertical():
            with Container(classes="editor-section"):
                yield Static("Text (use {{c1::text}} for cloze):", classes="editor-label")
                with Horizontal(classes="diff-container"):
                    with Vertical():
                        yield Static("Original:", classes="original-label")
                        yield Static(self.original_card.text, id="text-original")  # type: ignore
                    with Vertical():
                        yield Static("Editing:", classes="edited-label")
                        yield TextArea(self.card.text, id="text-input")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "save-btn":
            # Update card from inputs
            if isinstance(self.card, BasicCard):
                front_input = self.query_one("#front-input", TextArea)
                back_input = self.query_one("#back-input", TextArea)
                self.card.front = front_input.text
                self.card.back = back_input.text
            else:
                assert isinstance(self.card, ClozeCard)
                text_input = self.query_one("#text-input", TextArea)
                self.card.text = text_input.text

            self.card.mark_modified()
            self.dismiss(self.card)
        else:
            self.dismiss(None)

    async def on_key(self, event) -> None:  # type: ignore
        """Handle key press."""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "ctrl+s":
            # Trigger save
            save_btn = self.query_one("#save-btn", Button)
            await self.on_button_pressed(Button.Pressed(save_btn))
