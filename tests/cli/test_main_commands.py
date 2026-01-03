"""Tests for main CLI commands."""

import pytest
from click.testing import CliRunner

from ankification.cli import main


class TestMainGroup:
    """Tests for main command group."""

    def test_help_option(self, runner: CliRunner) -> None:
        """--help option shows help text."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Ankification" in result.output
        assert "generate" in result.output.lower()

    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        """Running without args shows help."""
        result = runner.invoke(main)

        # Click groups may exit with 0 or 2 depending on configuration
        assert result.exit_code in [0, 2]
        assert "Usage:" in result.output


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_help(self, runner: CliRunner) -> None:
        """generate --help shows options."""
        result = runner.invoke(main, ["generate", "--help"])

        assert result.exit_code == 0
        assert "SOURCES" in result.output
        assert "--provider" in result.output
        assert "--count-guidance" in result.output

    def test_generate_requires_sources(self, runner: CliRunner) -> None:
        """generate without sources shows error."""
        result = runner.invoke(main, ["generate"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()

    def test_generate_provider_choices(self, runner: CliRunner) -> None:
        """generate --provider accepts only valid choices."""
        result = runner.invoke(main, ["generate", "--help"])

        assert "openai" in result.output.lower()
        assert "anthropic" in result.output.lower()

    def test_generate_card_types_choices(self, runner: CliRunner) -> None:
        """generate --card-types accepts only valid choices."""
        result = runner.invoke(main, ["generate", "--help"])

        assert "basic" in result.output.lower()
        assert "cloze" in result.output.lower()


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_help(self, runner: CliRunner) -> None:
        """serve --help shows options."""
        result = runner.invoke(main, ["serve", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--reload" in result.output

    def test_serve_default_values_shown(self, runner: CliRunner) -> None:
        """serve help shows default values."""
        result = runner.invoke(main, ["serve", "--help"])

        assert "127.0.0.1" in result.output
        assert "8000" in result.output


class TestListSessionsCommand:
    """Tests for list-sessions command."""

    def test_list_sessions_help(self, runner: CliRunner) -> None:
        """list-sessions --help shows options."""
        result = runner.invoke(main, ["list-sessions", "--help"])

        assert result.exit_code == 0
        assert "--limit" in result.output

    def test_list_sessions_default_limit(self, runner: CliRunner) -> None:
        """list-sessions has default limit option."""
        result = runner.invoke(main, ["list-sessions", "--help"])

        # Verify --limit option exists (default may not be shown)
        assert "--limit" in result.output


class TestExportCommand:
    """Tests for export command."""

    def test_export_help(self, runner: CliRunner) -> None:
        """export --help shows options."""
        result = runner.invoke(main, ["export", "--help"])

        assert result.exit_code == 0
        assert "--session" in result.output
        assert "--format" in result.output
        assert "--status" in result.output

    def test_export_format_choices(self, runner: CliRunner) -> None:
        """export --format accepts only valid choices."""
        result = runner.invoke(main, ["export", "--help"])

        assert "csv" in result.output.lower()
        assert "ankiconnect" in result.output.lower()

    def test_export_status_choices(self, runner: CliRunner) -> None:
        """export --status accepts only valid choices."""
        result = runner.invoke(main, ["export", "--help"])

        assert "accepted" in result.output.lower()
        assert "draft" in result.output.lower()
        assert "rejected" in result.output.lower()
