"""Configuration fixtures for testing."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from ankification.config import Config
from ankification.config.manager import ConfigManager


@pytest.fixture
def default_config() -> Config:
    """Default configuration with no modifications."""
    return Config()


@pytest.fixture
def config_with_openai(temp_dir: Path) -> Config:
    """Config configured for OpenAI provider."""
    cfg = Config()
    cfg.llm.default_provider = "openai"
    cfg.storage.database_path = str(temp_dir / "openai_test.db")
    return cfg


@pytest.fixture
def config_with_anthropic(temp_dir: Path) -> Config:
    """Config configured for Anthropic provider."""
    cfg = Config()
    cfg.llm.default_provider = "anthropic"
    cfg.storage.database_path = str(temp_dir / "anthropic_test.db")
    return cfg


@pytest.fixture
def config_with_temp_paths(temp_dir: Path) -> Config:
    """Config with all paths pointing to temp directory."""
    cfg = Config()
    cfg.storage.database_path = str(temp_dir / "test.db")
    cfg.export.csv.output_dir = str(temp_dir / "export" / "csv")
    cfg.export.anki.output_dir = str(temp_dir / "export" / "anki")
    return cfg


@pytest.fixture
def config_with_custom_prompts() -> Config:
    """Config with custom generation prompts."""
    cfg = Config()
    cfg.generation.system_prompt = "Custom system prompt for testing"
    cfg.generation.user_directives = ["Test directive 1", "Test directive 2"]
    return cfg


@pytest.fixture
def config_with_high_card_count() -> Config:
    """Config for generating many cards."""
    cfg = Config()
    cfg.generation.count_guidance = "20-30"
    return cfg


@pytest.fixture
def config_with_low_card_count() -> Config:
    """Config for generating few cards."""
    cfg = Config()
    cfg.generation.count_guidance = "1-3"
    return cfg


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_manager_with_temp(temp_config_dir: Path) -> ConfigManager:
    """Config manager pointing to temp config file."""
    config_path = temp_config_dir / "config.yaml"
    return ConfigManager(config_path=config_path)


@pytest.fixture
def config_manager_with_existing_config(temp_config_dir: Path) -> ConfigManager:
    """Config manager with a pre-existing config file."""
    config_path = temp_config_dir / "config.yaml"
    config_path.write_text("""
llm:
  default_provider: anthropic
  openai:
    model: gpt-4
  anthropic:
    model: claude-3-opus-20240229

storage:
  database_path: ~/custom/path/ankification.db

generation:
  count_guidance: "10-20"
  card_types:
    - basic
    - cloze

export:
  csv:
    output_dir: ~/exports/csv
  anki:
    output_dir: ~/exports/anki
""")
    return ConfigManager(config_path=config_path)


@pytest.fixture
def invalid_config_yaml(temp_config_dir: Path) -> Path:
    """Path to an invalid YAML config file."""
    config_path = temp_config_dir / "invalid_config.yaml"
    config_path.write_text("""
llm:
  default_provider: [invalid yaml
  missing: closing bracket
""")
    return config_path


@pytest.fixture
def partial_config_yaml(temp_config_dir: Path) -> Path:
    """Path to a partial config file (some fields only)."""
    config_path = temp_config_dir / "partial_config.yaml"
    config_path.write_text("""
llm:
  default_provider: openai
""")
    return config_path


@pytest.fixture
def empty_config_yaml(temp_config_dir: Path) -> Path:
    """Path to an empty config file."""
    config_path = temp_config_dir / "empty_config.yaml"
    config_path.write_text("")
    return config_path
