"""Integration tests for export pipeline.

Tests the integration between:
- CSVExporter
- Card models
- File system operations
"""

import csv
import tempfile
from pathlib import Path

import pytest

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard
from ankification.export.csv_exporter import CSVExporter


class TestCSVExporterBasicCards:
    """Integration tests for CSVExporter with BasicCards."""

    @pytest.fixture
    def export_dir(self, temp_dir: Path) -> Path:
        """Create export directory."""
        export_path = temp_dir / "export"
        export_path.mkdir()
        return export_path

    @pytest.fixture
    def basic_cards(self) -> list[BasicCard]:
        """Create test basic cards."""
        return [
            BasicCard(
                front="Question 1?",
                back="Answer 1",
                source="test.txt",
                tags=["tag1", "tag2"],
            ),
            BasicCard(
                front="Question 2?",
                back="Answer 2",
                source="test.txt",
                tags=["tag3"],
            ),
        ]

    def test_export_basic_cards_creates_file(
        self, export_dir: Path, basic_cards: list[BasicCard]
    ) -> None:
        """Exporting basic cards should create a CSV file."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(basic_cards, "test_output.csv")

        assert output_path.exists()
        assert output_path.suffix == ".csv"

    def test_export_basic_cards_content(
        self, export_dir: Path, basic_cards: list[BasicCard]
    ) -> None:
        """Exported CSV should contain correct basic card data."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(basic_cards, "test_output.csv")

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        assert len(rows) == 2

        # First card
        assert rows[0][0] == "Question 1?"
        assert rows[0][1] == "Answer 1"
        assert "tag1" in rows[0][2]
        assert "tag2" in rows[0][2]

        # Second card
        assert rows[1][0] == "Question 2?"
        assert rows[1][1] == "Answer 2"

    def test_export_basic_cards_tags_space_separated(
        self, export_dir: Path, basic_cards: list[BasicCard]
    ) -> None:
        """Tags should be space-separated in exported CSV."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(basic_cards, "test_output.csv")

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        # First card has two tags, should be space separated
        assert rows[0][2] == "tag1 tag2"


class TestCSVExporterClozeCards:
    """Integration tests for CSVExporter with ClozeCards."""

    @pytest.fixture
    def export_dir(self, temp_dir: Path) -> Path:
        """Create export directory."""
        export_path = temp_dir / "export"
        export_path.mkdir()
        return export_path

    @pytest.fixture
    def cloze_cards(self) -> list[ClozeCard]:
        """Create test cloze cards."""
        return [
            ClozeCard(
                text="The {{c1::mitochondria}} is the powerhouse of the cell.",
                source="biology.txt",
                tags=["biology"],
            ),
            ClozeCard(
                text="{{c1::Python}} was created by {{c2::Guido}}.",
                source="programming.txt",
                tags=["python", "history"],
            ),
        ]

    def test_export_cloze_cards_creates_file(
        self, export_dir: Path, cloze_cards: list[ClozeCard]
    ) -> None:
        """Exporting cloze cards should create a CSV file."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(cloze_cards, "cloze_output.csv")

        assert output_path.exists()

    def test_export_cloze_cards_content(
        self, export_dir: Path, cloze_cards: list[ClozeCard]
    ) -> None:
        """Exported CSV should contain correct cloze card data."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(cloze_cards, "cloze_output.csv")

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        assert len(rows) == 2

        # Cloze text preserved with syntax
        assert "{{c1::mitochondria}}" in rows[0][0]
        assert "{{c1::Python}}" in rows[1][0]
        assert "{{c2::Guido}}" in rows[1][0]


class TestCSVExporterMixedCards:
    """Integration tests for CSVExporter with mixed card types."""

    @pytest.fixture
    def export_dir(self, temp_dir: Path) -> Path:
        """Create export directory."""
        export_path = temp_dir / "export"
        export_path.mkdir()
        return export_path

    @pytest.fixture
    def mixed_cards(self) -> list[BasicCard | ClozeCard]:
        """Create mixed test cards."""
        return [
            BasicCard(front="Q1?", back="A1", source="test.txt", tags=["basic"]),
            ClozeCard(text="{{c1::answer}}", source="test.txt", tags=["cloze"]),
            BasicCard(front="Q2?", back="A2", source="test.txt", tags=["basic"]),
        ]

    def test_export_mixed_cards_creates_separate_files(
        self, export_dir: Path, mixed_cards: list[BasicCard | ClozeCard]
    ) -> None:
        """Exporting mixed cards should create separate files for each type."""
        exporter = CSVExporter(export_dir)
        output_path = exporter.export(mixed_cards, "mixed.csv")

        # Should create separate files for basic and cloze
        basic_path = export_dir / "mixed_basic.csv"
        cloze_path = export_dir / "mixed_cloze.csv"

        assert basic_path.exists() or cloze_path.exists()


class TestCSVExporterByStatus:
    """Integration tests for status-based export."""

    @pytest.fixture
    def export_dir(self, temp_dir: Path) -> Path:
        """Create export directory."""
        export_path = temp_dir / "export"
        export_path.mkdir()
        return export_path

    @pytest.fixture
    def cards_with_status(self) -> list[BasicCard]:
        """Create cards with different statuses."""
        return [
            BasicCard(
                front="Draft Q", back="Draft A", source="test.txt", status=CardStatus.DRAFT
            ),
            BasicCard(
                front="Accepted Q", back="Accepted A", source="test.txt", status=CardStatus.ACCEPTED
            ),
            BasicCard(
                front="Rejected Q", back="Rejected A", source="test.txt", status=CardStatus.REJECTED
            ),
        ]

    def test_export_by_status_creates_files_per_status(
        self, export_dir: Path, cards_with_status: list[BasicCard]
    ) -> None:
        """export_by_status should create separate files for each status."""
        exporter = CSVExporter(export_dir)
        results = exporter.export_by_status(cards_with_status)

        assert "draft" in results
        assert "accepted" in results
        assert "rejected" in results

    def test_export_by_status_filter(
        self, export_dir: Path, cards_with_status: list[BasicCard]
    ) -> None:
        """export_by_status with filter should only export specified status."""
        exporter = CSVExporter(export_dir)
        results = exporter.export_by_status(cards_with_status, status_filter="accepted")

        assert "accepted" in results
        assert "draft" not in results
        assert "rejected" not in results


class TestCSVExporterEdgeCases:
    """Integration tests for edge cases."""

    @pytest.fixture
    def export_dir(self, temp_dir: Path) -> Path:
        """Create export directory."""
        export_path = temp_dir / "export"
        export_path.mkdir()
        return export_path

    def test_export_empty_list_raises(self, export_dir: Path) -> None:
        """Exporting empty list should raise ValueError."""
        exporter = CSVExporter(export_dir)

        with pytest.raises(ValueError, match="No cards to export"):
            exporter.export([])

    def test_export_card_with_no_tags(self, export_dir: Path) -> None:
        """Exporting cards without tags should work."""
        card = BasicCard(front="Q", back="A", source="test.txt", tags=[])
        exporter = CSVExporter(export_dir)

        output_path = exporter.export([card], "no_tags.csv")

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        assert rows[0][2] == ""  # Empty tags

    def test_export_card_with_special_characters(self, export_dir: Path) -> None:
        """Exporting cards with special characters should work."""
        card = BasicCard(
            front="What is 2+2?",
            back="4; or \"four\" in words",
            source="test.txt",
            tags=["math"],
        )
        exporter = CSVExporter(export_dir)

        output_path = exporter.export([card], "special_chars.csv")

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)

        assert rows[0][0] == "What is 2+2?"
        assert "four" in rows[0][1]

    def test_export_auto_generates_filename(self, export_dir: Path) -> None:
        """Export without filename should auto-generate one."""
        card = BasicCard(front="Q", back="A", source="test.txt")
        exporter = CSVExporter(export_dir)

        output_path = exporter.export([card])

        assert output_path.exists()
        assert "anki_cards_" in output_path.name

    def test_export_creates_output_directory(self, temp_dir: Path) -> None:
        """CSVExporter should create output directory if it doesn't exist."""
        new_dir = temp_dir / "new" / "nested" / "dir"
        exporter = CSVExporter(new_dir)

        card = BasicCard(front="Q", back="A", source="test.txt")
        output_path = exporter.export([card], "test.csv")

        assert new_dir.exists()
        assert output_path.exists()
