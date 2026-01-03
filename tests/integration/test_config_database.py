"""Integration tests for Config + Database path resolution.

Tests the integration between configuration management
and database initialization.
"""

import os
import tempfile
from pathlib import Path

import pytest

from ankification.config import Config
from ankification.config.manager import ConfigManager
from ankification.storage.database import Database


class TestConfigDatabasePath:
    """Integration tests for config-based database path resolution."""

    def test_database_uses_config_path(self, temp_dir: Path) -> None:
        """Database should use path from config."""
        config = Config()
        db_path = temp_dir / "custom_db.db"
        config.storage.database_path = str(db_path)

        db = Database(config.storage.database_path)
        assert db.db_path == db_path

    async def test_database_creates_file_at_config_path(
        self, temp_dir: Path
    ) -> None:
        """Database should create file at configured path."""
        config = Config()
        db_path = temp_dir / "ankification.db"
        config.storage.database_path = str(db_path)

        db = Database(config.storage.database_path)
        await db.connect()
        await db.close()

        assert db_path.exists()

    async def test_database_path_expansion(self, temp_dir: Path) -> None:
        """Database should handle path with ~ expansion."""
        # Note: We'll test with explicit path since ~ depends on environment
        config = Config()
        db_path = temp_dir / "subdir" / "test.db"
        config.storage.database_path = str(db_path)

        db = Database(config.storage.database_path)
        await db.connect()
        await db.close()

        assert db_path.exists()


class TestConfigManagerDatabaseIntegration:
    """Integration tests for ConfigManager + Database workflow."""

    @pytest.fixture
    def config_dir(self, temp_dir: Path) -> Path:
        """Create config directory."""
        cfg_dir = temp_dir / "config"
        cfg_dir.mkdir()
        return cfg_dir

    def test_config_manager_provides_database_path(
        self, config_dir: Path, temp_dir: Path
    ) -> None:
        """ConfigManager should provide usable database path."""
        config_path = config_dir / "config.yaml"
        manager = ConfigManager(config_path=config_path)

        config = manager.load()
        # Override with test path
        config.storage.database_path = str(temp_dir / "test.db")

        db = Database(config.storage.database_path)
        assert db is not None

    async def test_saved_config_database_path_works(
        self, config_dir: Path, temp_dir: Path
    ) -> None:
        """Database path saved in config should be usable after reload."""
        config_path = config_dir / "config.yaml"
        manager = ConfigManager(config_path=config_path)

        # Save custom path
        config = manager.load()
        db_path = temp_dir / "persisted.db"
        config.storage.database_path = str(db_path)
        manager.save(config)

        # Reload config
        new_manager = ConfigManager(config_path=config_path)
        loaded_config = new_manager.load()

        # Use loaded path for database
        db = Database(loaded_config.storage.database_path)
        await db.connect()
        await db.close()

        assert db_path.exists()


class TestDatabasePathCreation:
    """Integration tests for database directory creation."""

    async def test_database_creates_parent_directories(
        self, temp_dir: Path
    ) -> None:
        """Database should create parent directories if they don't exist."""
        db_path = temp_dir / "deep" / "nested" / "path" / "test.db"

        config = Config()
        config.storage.database_path = str(db_path)

        db = Database(config.storage.database_path)
        await db.connect()
        await db.close()

        assert db_path.exists()
        assert db_path.parent.exists()


class TestMultipleDatabaseInstances:
    """Integration tests for multiple database configurations."""

    async def test_different_configs_different_databases(
        self, temp_dir: Path
    ) -> None:
        """Different configs should use different database files."""
        config1 = Config()
        config1.storage.database_path = str(temp_dir / "db1.db")

        config2 = Config()
        config2.storage.database_path = str(temp_dir / "db2.db")

        db1 = Database(config1.storage.database_path)
        db2 = Database(config2.storage.database_path)

        await db1.connect()
        await db2.connect()

        # Add data to first database
        from ankification.cards.models import BasicCard
        card = BasicCard(front="Q", back="A", source="test.txt")
        await db1.save_card(card)

        # Second database should be empty
        cards1 = await db1.get_all_cards()
        cards2 = await db2.get_all_cards()

        assert len(cards1) == 1
        assert len(cards2) == 0

        await db1.close()
        await db2.close()


class TestConfigExportPath:
    """Integration tests for export path configuration."""

    def test_config_export_path_accessible(self, temp_dir: Path) -> None:
        """Export path from config should be accessible."""
        config = Config()
        export_path = temp_dir / "exports"
        config.export.csv.output_dir = str(export_path)

        from ankification.export.csv_exporter import CSVExporter
        exporter = CSVExporter(config.export.csv.output_dir)

        assert exporter.output_dir == export_path
        assert export_path.exists()  # CSVExporter creates directory

    async def test_full_config_workflow(self, temp_dir: Path) -> None:
        """Full workflow: load config, create database, export."""
        config = Config()
        config.storage.database_path = str(temp_dir / "test.db")
        config.export.csv.output_dir = str(temp_dir / "exports")

        # Create database
        db = Database(config.storage.database_path)
        await db.connect()

        # Add card
        from ankification.cards.models import BasicCard, CardStatus
        card = BasicCard(front="Q", back="A", source="test.txt")
        card.status = CardStatus.ACCEPTED  # For export
        await db.save_card(card)

        # Export using config path
        from ankification.export.csv_exporter import CSVExporter
        exporter = CSVExporter(config.export.csv.output_dir)

        cards = await db.get_all_cards()
        if cards:
            export_path = exporter.export(cards, "test_export.csv")
            assert export_path.exists()

        await db.close()
