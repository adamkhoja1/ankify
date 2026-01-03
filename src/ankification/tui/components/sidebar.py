"""Sidebar component for card list."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from ...cards.models import Card, CardStatus


class CardSidebar(VerticalScroll):
    """Sidebar showing list of cards."""

    def __init__(self, cards: list[Card], **kwargs) -> None:  # type: ignore
        """Initialize sidebar.

        Args:
            cards: List of cards to display
        """
        super().__init__(**kwargs)
        self.cards = cards
        self.current_index = 0

    def compose(self) -> ComposeResult:
        """Compose sidebar widgets."""
        yield Static(f"Cards ({len(self.cards)})", classes="sidebar-header")

        for i, card in enumerate(self.cards):
            status_icon = self._get_status_icon(card.status)
            preview = self._get_card_preview(card)
            classes = "card-item"

            if i == self.current_index:
                classes += " current"

            classes += f" card-status-{card.status.value}"

            yield Static(f"{status_icon} {preview}", classes=classes, id=f"card-{i}")

    def _get_status_icon(self, status: CardStatus) -> str:
        """Get icon for card status.

        Args:
            status: Card status

        Returns:
            Status icon
        """
        if status == CardStatus.ACCEPTED:
            return "✓"
        elif status == CardStatus.REJECTED:
            return "✗"
        else:
            return "•"

    def _get_card_preview(self, card: Card) -> str:
        """Get preview text for card.

        Args:
            card: Card to preview

        Returns:
            Preview string (truncated)
        """
        from ...cards.models import BasicCard, ClozeCard

        if isinstance(card, BasicCard):
            text = card.front
        else:
            assert isinstance(card, ClozeCard)
            # Remove cloze markers for preview
            text = card.text.replace("{{c1::", "").replace("}}", "")

        # Truncate to ~30 chars
        max_len = 30
        if len(text) > max_len:
            return text[:max_len-3] + "..."
        return text
