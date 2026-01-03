"""Property-based tests for configuration handling."""

import tempfile
from pathlib import Path

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ankification.config import Config
from ankification.config.manager import ConfigManager

from .strategies import (
    config_provider_strategy,
    count_guidance_strategy,
)


class TestConfigDefaults:
    """Property tests for configuration defaults."""

    @given(st.just(None))
    @settings(max_examples=1)
    def test_config_has_default_provider(self, _: None) -> None:
        """Config always has a default provider set."""
        config = Config()
        assert config.llm.default_provider is not None
        assert isinstance(config.llm.default_provider, str)
        assert len(config.llm.default_provider) > 0

    @given(st.just(None))
    @settings(max_examples=1)
    def test_config_has_storage_path(self, _: None) -> None:
        """Config always has a storage path."""
        config = Config()
        assert config.storage.database_path is not None
        assert isinstance(config.storage.database_path, str)


class TestConfigProviderSettings:
    """Property tests for provider configuration."""

    @given(config_provider_strategy())
    @settings(max_examples=10)
    def test_provider_can_be_set(self, provider: str) -> None:
        """Provider can be set to any valid value."""
        config = Config()
        config.llm.default_provider = provider
        assert config.llm.default_provider == provider

    @given(config_provider_strategy())
    @settings(max_examples=10)
    def test_provider_setting_idempotent(self, provider: str) -> None:
        """Setting provider twice has same result."""
        config = Config()
        config.llm.default_provider = provider
        first = config.llm.default_provider
        config.llm.default_provider = provider
        assert config.llm.default_provider == first


class TestConfigCountGuidance:
    """Property tests for count guidance configuration."""

    @given(count_guidance_strategy())
    @settings(max_examples=30)
    def test_count_guidance_format_valid(self, guidance: str) -> None:
        """Count guidance follows min-max format."""
        parts = guidance.split("-")
        assert len(parts) == 2

        min_val = int(parts[0])
        max_val = int(parts[1])

        assert min_val > 0
        assert max_val >= min_val

    @given(count_guidance_strategy())
    @settings(max_examples=20)
    def test_count_guidance_can_be_set(self, guidance: str) -> None:
        """Count guidance can be set on config."""
        config = Config()
        config.generation.count_guidance = guidance
        assert config.generation.count_guidance == guidance


class TestConfigManagerPersistence:
    """Property tests for config manager persistence."""

    @given(config_provider_strategy())
    @settings(max_examples=10, deadline=None)
    def test_config_survives_save_load(self, provider: str) -> None:
        """Config values survive save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path=config_path)

            # Set and save
            config = manager.load()
            config.llm.default_provider = provider
            manager.save(config)

            # Load and verify
            new_manager = ConfigManager(config_path=config_path)
            loaded = new_manager.load()

            assert loaded.llm.default_provider == provider

    @given(count_guidance_strategy())
    @settings(max_examples=10, deadline=None)
    def test_count_guidance_survives_save_load(self, guidance: str) -> None:
        """Count guidance survives save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path=config_path)

            config = manager.load()
            config.generation.count_guidance = guidance
            manager.save(config)

            new_manager = ConfigManager(config_path=config_path)
            loaded = new_manager.load()

            assert loaded.generation.count_guidance == guidance


class TestConfigPathResolution:
    """Property tests for path resolution in config."""

    @given(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=20,
    ))
    @settings(max_examples=20)
    def test_database_path_accepts_strings(self, path_suffix: str) -> None:
        """Database path accepts various string values."""
        config = Config()
        test_path = f"/tmp/{path_suffix}/test.db"
        config.storage.database_path = test_path
        assert config.storage.database_path == test_path


class TestConfigCardTypes:
    """Property tests for card type configuration."""

    @given(st.lists(
        st.sampled_from(["basic", "cloze"]),
        min_size=1,
        max_size=2,
        unique=True,
    ))
    @settings(max_examples=10)
    def test_card_types_can_be_set(self, card_types: list[str]) -> None:
        """Card types can be set on config."""
        config = Config()
        config.generation.card_types = card_types
        assert config.generation.card_types == card_types

    @given(st.lists(
        st.sampled_from(["basic", "cloze"]),
        min_size=1,
        max_size=2,
        unique=True,
    ))
    @settings(max_examples=10, deadline=None)
    def test_card_types_survive_save_load(self, card_types: list[str]) -> None:
        """Card types survive save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path=config_path)

            config = manager.load()
            config.generation.card_types = card_types
            manager.save(config)

            new_manager = ConfigManager(config_path=config_path)
            loaded = new_manager.load()

            assert loaded.generation.card_types == card_types
