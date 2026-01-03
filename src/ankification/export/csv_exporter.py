"""CSV export for Anki."""

import csv
from pathlib import Path

from ..cards.models import BasicCard, Card, CardType, ClozeCard


class CSVExporter:
    """Export cards to CSV format for Anki import."""

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize CSV exporter.

        Args:
            output_dir: Directory to save CSV files
        """
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, cards: list[Card], filename: str | None = None) -> Path:
        """Export cards to CSV file.

        Args:
            cards: Cards to export
            filename: Output filename (None for auto-generated)

        Returns:
            Path to created CSV file

        Raises:
            ValueError: If no cards provided
        """
        if not cards:
            raise ValueError("No cards to export")

        # Generate filename if not provided
        if filename is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anki_cards_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Separate basic and cloze cards
        basic_cards = [c for c in cards if c.type == CardType.BASIC]
        cloze_cards = [c for c in cards if c.type == CardType.CLOZE]

        # Export based on card types present
        if basic_cards and not cloze_cards:
            self._export_basic_cards(basic_cards, output_path)
        elif cloze_cards and not basic_cards:
            self._export_cloze_cards(cloze_cards, output_path)
        else:
            # Mixed types - create separate files
            basic_path = output_path.with_stem(f"{output_path.stem}_basic")
            cloze_path = output_path.with_stem(f"{output_path.stem}_cloze")

            if basic_cards:
                self._export_basic_cards(basic_cards, basic_path)
            if cloze_cards:
                self._export_cloze_cards(cloze_cards, cloze_path)

            output_path = basic_path  # Return first file path

        return output_path

    def _export_basic_cards(self, cards: list[Card], output_path: Path) -> None:
        """Export basic cards to CSV.

        Args:
            cards: Basic cards to export
            output_path: Output file path
        """
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")

            for card in cards:
                assert isinstance(card, BasicCard)
                # Format: Front;Back;Tags
                tags_str = " ".join(card.tags) if card.tags else ""
                writer.writerow([card.front, card.back, tags_str])

    def _export_cloze_cards(self, cards: list[Card], output_path: Path) -> None:
        """Export cloze cards to CSV.

        Args:
            cards: Cloze cards to export
            output_path: Output file path
        """
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")

            for card in cards:
                assert isinstance(card, ClozeCard)
                # Format: Text;Tags
                tags_str = " ".join(card.tags) if card.tags else ""
                writer.writerow([card.text, tags_str])

    def export_by_status(
        self, cards: list[Card], status_filter: str | None = None
    ) -> dict[str, Path]:
        """Export cards grouped by status.

        Args:
            cards: Cards to export
            status_filter: Optional status to filter by

        Returns:
            Dictionary mapping status to output file path
        """
        from ..cards.models import CardStatus
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results: dict[str, Path] = {}

        # Group cards by status
        by_status: dict[str, list[Card]] = {}
        for card in cards:
            status = card.status.value
            if status_filter and status != status_filter:
                continue
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(card)

        # Export each status group
        for status, status_cards in by_status.items():
            if status_cards:
                filename = f"anki_cards_{status}_{timestamp}.csv"
                output_path = self.export(status_cards, filename)
                results[status] = output_path

        return results
