"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a sample text file.\nIt has multiple lines.")
    return file_path


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create a sample markdown file."""
    file_path = temp_dir / "sample.md"
    content = """# Sample Markdown

This is a **markdown** file with _formatting_.

## Section 1
Some content here.

## Section 2
More content.
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def empty_file(temp_dir):
    """Create an empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.write_text("")
    return file_path


@pytest.fixture
def sample_html():
    """Sample HTML content."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <script>console.log('test');</script>
        <style>body { color: black; }</style>
    </head>
    <body>
        <h1>Main Title</h1>
        <p>This is a paragraph.</p>
        <p>Another paragraph with <strong>bold text</strong>.</p>
        <div>Some content in a div.</div>
    </body>
    </html>
    """
