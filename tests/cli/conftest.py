"""CLI test fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner

from ankification.cli import main


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def isolated_runner() -> Generator[CliRunner, None, None]:
    """Create Click test runner with isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Path:
    """Create temporary config directory."""
    config_dir = temp_dir / ".ankification"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def cli_with_temp_config(temp_dir: Path, monkeypatch):
    """Set up CLI with temporary configuration."""
    config_path = temp_dir / "config.yaml"

    # Create minimal config
    config_path.write_text(f"""
llm:
  default_provider: openai
storage:
  database_path: {temp_dir / 'test.db'}
export:
  csv:
    output_dir: {temp_dir / 'export'}
""")

    # Monkeypatch ConfigManager to use temp path
    from ankification.config.manager import ConfigManager

    original_init = ConfigManager.__init__

    def patched_init(self, config_path_arg=None):
        original_init(self, config_path=config_path)

    monkeypatch.setattr(ConfigManager, "__init__", patched_init)

    return main
