"""Tests for config CLI commands."""

import pytest
from click.testing import CliRunner

from ankification.cli import main


class TestConfigGroup:
    """Tests for config command group."""

    def test_config_help(self, runner: CliRunner) -> None:
        """config --help shows subcommands."""
        result = runner.invoke(main, ["config", "--help"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert "show" in result.output
        assert "set" in result.output

    def test_config_no_subcommand(self, runner: CliRunner) -> None:
        """config without subcommand shows help."""
        result = runner.invoke(main, ["config"])

        # Click groups may exit with 0 or 2 depending on configuration
        assert result.exit_code in [0, 2]
        assert "Usage:" in result.output


class TestConfigInit:
    """Tests for config init command."""

    def test_config_init_help(self, runner: CliRunner) -> None:
        """config init --help shows description."""
        result = runner.invoke(main, ["config", "init", "--help"])

        assert result.exit_code == 0
        assert "Initialize" in result.output


class TestConfigShow:
    """Tests for config show command."""

    def test_config_show_help(self, runner: CliRunner) -> None:
        """config show --help shows description."""
        result = runner.invoke(main, ["config", "show", "--help"])

        assert result.exit_code == 0
        assert "Show" in result.output


class TestConfigSet:
    """Tests for config set command."""

    def test_config_set_help(self, runner: CliRunner) -> None:
        """config set --help shows description."""
        result = runner.invoke(main, ["config", "set", "--help"])

        assert result.exit_code == 0
        assert "Set" in result.output
        assert "KEY" in result.output
        assert "VALUE" in result.output

    def test_config_set_requires_key_and_value(self, runner: CliRunner) -> None:
        """config set requires both KEY and VALUE."""
        # Missing both
        result = runner.invoke(main, ["config", "set"])
        assert result.exit_code != 0

        # Missing VALUE
        result = runner.invoke(main, ["config", "set", "somekey"])
        assert result.exit_code != 0

    def test_config_set_example_shown(self, runner: CliRunner) -> None:
        """config set help shows example usage."""
        result = runner.invoke(main, ["config", "set", "--help"])

        # Should show example of setting a config value
        assert "Example" in result.output or "llm" in result.output.lower()
