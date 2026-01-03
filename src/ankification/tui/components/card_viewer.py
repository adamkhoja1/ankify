"""Card viewer component."""

from textual.containers import Container, Vertical
from textual.widgets import Static

from ...cards.models import BasicCard, Card, ClozeCard


class CardViewer(Container):
    """Widget for displaying a card."""

    def __init__(self, card: Card | None, **kwargs) -> None:  # type: ignore
        """Initialize card viewer.

        Args:
            card: Card to display
        """
        super().__init__(**kwargs)
        self.card = card

    def compose(self):
        """Compose card viewer widgets."""
        if not self.card:
            yield Static("No card selected")
            return

        # Header with card info
        card_type = self.card.type.value.capitalize()
        source = self.card.source
        tags_str = ", ".join(self.card.tags) if self.card.tags else "none"

        yield Static(
            f"[{card_type}]  Source: {source}  Tags: {tags_str}",
            classes="card-header",
        )

        # Card content based on type
        if isinstance(self.card, BasicCard):
            yield self._compose_basic_card(self.card)
        else:
            assert isinstance(self.card, ClozeCard)
            yield self._compose_cloze_card(self.card)

    def _compose_basic_card(self, card: BasicCard):
        """Compose basic card display.

        Args:
            card: Basic card to display

        Returns:
            Container with front and back
        """
        with Vertical():
            yield Static("Front", classes="field-label")
            yield Static(card.front, classes="field-content card-front")
            yield Static("")  # Spacer
            yield Static("Back", classes="field-label")
            yield Static(card.back, classes="field-content card-back")

    def _compose_cloze_card(self, card: ClozeCard):
        """Compose cloze card display.

        Args:
            card: Cloze card to display

        Returns:
            Container with cloze text
        """
        with Vertical():
            yield Static("Text", classes="field-label")
            # TODO: Highlight cloze deletions
            yield Static(card.text, classes="field-content card-cloze")
