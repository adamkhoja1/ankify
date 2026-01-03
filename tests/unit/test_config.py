"""Unit tests for configuration management."""

import os
from pathlib import Path

import pytest
import yaml

from ankification.config import Config, ConfigManager


class TestConfigSchema:
    """Tests for Config schema."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = Config.default()

        assert config.llm.default_provider == "openai"
        assert config.generation.auto_determine_count is True
        assert config.tui.keybindings.next == "j"
        assert config.export.default_format == "csv"

    def test_config_validation_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="must be 'openai' or 'anthropic'"):
            Config(llm={"default_provider": "invalid"})

    def test_config_validation_invalid_card_type(self):
        """Test that invalid card type raises error."""
        with pytest.raises(ValueError, match="Invalid card type"):
            Config(generation={"card_types": ["basic", "invalid"]})

    def test_config_validation_invalid_export_format(self):
        """Test that invalid export format raises error."""
        with pytest.raises(ValueError, match="must be 'csv' or 'ankiconnect'"):
            Config(export={"default_format": "invalid"})

    def test_config_path_expansion(self):
        """Test that paths are expanded."""
        config = Config(
            storage={"database_path": "~/test.db"},
            export={"csv": {"output_dir": "~/docs"}},
        )

        assert not config.storage.database_path.startswith("~")
        assert not config.export.csv.output_dir.startswith("~")

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config.default()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert "llm" in data
        assert "generation" in data
        assert data["llm"]["default_provider"] == "openai"


class TestConfigManager:
    """Tests for ConfigManager."""

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a temporary config file."""
        config_path = temp_dir / "config.yaml"
        return config_path

    @pytest.fixture
    def manager(self, config_file):
        """Create ConfigManager with temp config."""
        return ConfigManager(config_path=config_file)

    def test_load_nonexistent_config_returns_default(self, manager):
        """Test loading nonexistent config returns default."""
        config = manager.load()
        assert isinstance(config, Config)
        assert config.llm.default_provider == "openai"

    def test_save_and_load_config(self, manager):
        """Test saving and loading configuration."""
        config = Config.default()
        config.llm.default_provider = "anthropic"
        config.generation.count_guidance = "around 20"

        manager.save(config)
        loaded = manager.load()

        assert loaded.llm.default_provider == "anthropic"
        assert loaded.generation.count_guidance == "around 20"

    def test_get_returns_loaded_config(self, manager):
        """Test that get() returns loaded config."""
        config1 = manager.get()
        config2 = manager.get()
        assert config1 is config2

    def test_set_value_updates_config(self, manager, config_file):
        """Test setting a value by path."""
        manager.set_value("llm.default_provider", "anthropic")

        # Verify in-memory config
        config = manager.get()
        assert config.llm.default_provider == "anthropic"

        # Verify saved to file
        with open(config_file) as f:
            data = yaml.safe_load(f)
        assert data["llm"]["default_provider"] == "anthropic"

    def test_set_value_nested_path(self, manager):
        """Test setting nested configuration value."""
        manager.set_value("tui.keybindings.next", "n")
        config = manager.get()
        assert config.tui.keybindings.next == "n"

    def test_init_config_creates_file(self, manager, config_file):
        """Test initializing new config file."""
        assert not config_file.exists()
        manager.init_config()
        assert config_file.exists()

    def test_init_config_raises_if_exists(self, manager, config_file):
        """Test that init_config raises if file exists."""
        manager.init_config()
        with pytest.raises(FileExistsError):
            manager.init_config()

    def test_show_config_returns_yaml(self, manager):
        """Test showing config as YAML."""
        yaml_str = manager.show_config()
        assert "llm:" in yaml_str
        assert "generation:" in yaml_str
        assert isinstance(yaml_str, str)

    def test_env_var_substitution(self, manager, config_file):
        """Test environment variable substitution."""
        # Create config with env var
        config_data = {
            "llm": {
                "openai": {"api_key": "${TEST_API_KEY}"},
                "anthropic": {"api_key": ""},
            }
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Set env var
        os.environ["TEST_API_KEY"] = "test-key-123"

        # Load config
        config = manager.load()
        assert config.llm.openai.api_key == "test-key-123"

        # Clean up
        del os.environ["TEST_API_KEY"]

    def test_env_var_substitution_missing_var(self, manager, config_file):
        """Test env var substitution with missing variable."""
        config_data = {
            "llm": {
                "openai": {"api_key": "${MISSING_VAR}"},
                "anthropic": {"api_key": ""},
            }
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = manager.load()
        assert config.llm.openai.api_key == ""

    def test_default_config_path(self):
        """Test default config path."""
        manager = ConfigManager()
        expected = Path.home() / ".config" / "ankification" / "config.yaml"
        assert manager.config_path == expected
