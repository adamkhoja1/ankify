"""Tests for tags CLI commands."""

import pytest
from click.testing import CliRunner

from ankification.cli import main


class TestTagsGroup:
    """Tests for tags command group."""

    def test_tags_help(self, runner: CliRunner) -> None:
        """tags --help shows subcommands."""
        result = runner.invoke(main, ["tags", "--help"])

        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_tags_no_subcommand(self, runner: CliRunner) -> None:
        """tags without subcommand shows help."""
        result = runner.invoke(main, ["tags"])

        # Click groups may exit with 0 or 2 depending on configuration
        assert result.exit_code in [0, 2]
        assert "Usage:" in result.output


class TestTagsAdd:
    """Tests for tags add command."""

    def test_tags_add_help(self, runner: CliRunner) -> None:
        """tags add --help shows description."""
        result = runner.invoke(main, ["tags", "add", "--help"])

        assert result.exit_code == 0
        assert "Add" in result.output

    def test_tags_add_requires_tag_names(self, runner: CliRunner) -> None:
        """tags add requires at least one tag name."""
        result = runner.invoke(main, ["tags", "add"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()


class TestTagsList:
    """Tests for tags list command."""

    def test_tags_list_help(self, runner: CliRunner) -> None:
        """tags list --help shows description."""
        result = runner.invoke(main, ["tags", "list", "--help"])

        assert result.exit_code == 0
        assert "List" in result.output


class TestTagsRemove:
    """Tests for tags remove command."""

    def test_tags_remove_help(self, runner: CliRunner) -> None:
        """tags remove --help shows description."""
        result = runner.invoke(main, ["tags", "remove", "--help"])

        assert result.exit_code == 0
        assert "Remove" in result.output

    def test_tags_remove_requires_tag_name(self, runner: CliRunner) -> None:
        """tags remove requires a tag name."""
        result = runner.invoke(main, ["tags", "remove"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()
