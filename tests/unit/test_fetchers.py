"""Unit tests for content fetchers."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ankification.fetchers import (
    EPUBFetcher,
    FetcherManager,
    FileFetcher,
    PDFFetcher,
    TextFetcher,
    URLFetcher,
)


class TestTextFetcher:
    """Tests for TextFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create TextFetcher instance."""
        return TextFetcher()

    @pytest.mark.asyncio
    async def test_fetch_valid_text(self, fetcher):
        """Test fetching valid text."""
        text = "This is some text content"
        result = await fetcher.fetch(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_fetch_strips_whitespace(self, fetcher):
        """Test that whitespace is stripped."""
        text = "  \n  Text with whitespace  \n  "
        result = await fetcher.fetch(text)
        assert result == "Text with whitespace"

    @pytest.mark.asyncio
    async def test_fetch_empty_text_raises(self, fetcher):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await fetcher.fetch("")

    @pytest.mark.asyncio
    async def test_fetch_whitespace_only_raises(self, fetcher):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await fetcher.fetch("   \n\n   ")

    def test_can_handle_any_string(self, fetcher):
        """Test that TextFetcher can handle any string."""
        assert fetcher.can_handle("any text")
        assert fetcher.can_handle("https://example.com")
        assert fetcher.can_handle("/path/to/file.txt")

    def test_name(self, fetcher):
        """Test fetcher name."""
        assert fetcher.name == "text"


class TestFileFetcher:
    """Tests for FileFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create FileFetcher instance."""
        return FileFetcher()

    @pytest.mark.asyncio
    async def test_fetch_text_file(self, fetcher, sample_text_file):
        """Test fetching a text file."""
        result = await fetcher.fetch(str(sample_text_file))
        assert "sample text file" in result
        assert "multiple lines" in result

    @pytest.mark.asyncio
    async def test_fetch_markdown_file(self, fetcher, sample_markdown_file):
        """Test fetching a markdown file."""
        result = await fetcher.fetch(str(sample_markdown_file))
        assert "Sample Markdown" in result
        assert "markdown" in result

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_file_raises(self, fetcher):
        """Test that nonexistent file raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await fetcher.fetch("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_fetch_directory_raises(self, fetcher, temp_dir):
        """Test that directory raises ValueError."""
        with pytest.raises(ValueError, match="not a file"):
            await fetcher.fetch(str(temp_dir))

    @pytest.mark.asyncio
    async def test_fetch_unsupported_extension_raises(self, fetcher, temp_dir):
        """Test that unsupported extension raises ValueError."""
        file_path = temp_dir / "file.xyz"
        file_path.write_text("content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            await fetcher.fetch(str(file_path))

    @pytest.mark.asyncio
    async def test_fetch_empty_file_raises(self, fetcher, empty_file):
        """Test that empty file raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await fetcher.fetch(str(empty_file))

    def test_can_handle_text_files(self, fetcher):
        """Test can_handle for text files."""
        assert fetcher.can_handle("file.txt")
        assert fetcher.can_handle("file.md")
        assert fetcher.can_handle("file.markdown")
        assert fetcher.can_handle("file.rst")

    def test_can_handle_rejects_urls(self, fetcher):
        """Test can_handle rejects URLs."""
        assert not fetcher.can_handle("http://example.com")
        assert not fetcher.can_handle("https://example.com")

    def test_can_handle_rejects_pdfs(self, fetcher):
        """Test can_handle rejects PDFs."""
        assert not fetcher.can_handle("file.pdf")

    def test_name(self, fetcher):
        """Test fetcher name."""
        assert fetcher.name == "file"


class TestURLFetcher:
    """Tests for URLFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create URLFetcher instance."""
        return URLFetcher()

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, sample_html):
        """Test successful URL fetch."""
        mock_response = Mock()
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            result = await fetcher.fetch("https://example.com")

        assert "Main Title" in result
        assert "This is a paragraph" in result
        assert "bold text" in result
        # Scripts and styles should be removed
        assert "console.log" not in result
        assert "color: black" not in result

    @pytest.mark.asyncio
    async def test_fetch_invalid_url_raises(self, fetcher):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            await fetcher.fetch("not-a-url")

    @pytest.mark.asyncio
    async def test_fetch_http_error_raises(self, fetcher):
        """Test that HTTP error raises RuntimeError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            with pytest.raises(RuntimeError, match="HTTP error"):
                await fetcher.fetch("https://example.com/404")

    @pytest.mark.asyncio
    async def test_fetch_request_error_raises(self, fetcher):
        """Test that request error raises RuntimeError."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            with pytest.raises(RuntimeError, match="Request error"):
                await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_empty_content_raises(self, fetcher):
        """Test that empty content raises ValueError."""
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            with pytest.raises(ValueError, match="No text content"):
                await fetcher.fetch("https://example.com")

    def test_can_handle_http_urls(self, fetcher):
        """Test can_handle for HTTP URLs."""
        assert fetcher.can_handle("http://example.com")
        assert fetcher.can_handle("https://example.com")

    def test_can_handle_rejects_non_urls(self, fetcher):
        """Test can_handle rejects non-URLs."""
        assert not fetcher.can_handle("file.txt")
        assert not fetcher.can_handle("/path/to/file")

    def test_name(self, fetcher):
        """Test fetcher name."""
        assert fetcher.name == "url"

    def test_extract_text_removes_scripts_and_styles(self, fetcher, sample_html):
        """Test that script and style tags are removed."""
        text = fetcher._extract_text(sample_html)
        assert "console.log" not in text
        assert "color: black" not in text


class TestPDFFetcher:
    """Tests for PDFFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create PDFFetcher instance."""
        return PDFFetcher()

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_file_raises(self, fetcher):
        """Test that nonexistent file raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await fetcher.fetch("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_fetch_non_pdf_raises(self, fetcher, sample_text_file):
        """Test that non-PDF file raises ValueError."""
        with pytest.raises(ValueError, match="Not a PDF"):
            await fetcher.fetch(str(sample_text_file))

    def test_can_handle_pdf_files(self, fetcher):
        """Test can_handle for PDF files."""
        assert fetcher.can_handle("file.pdf")
        assert fetcher.can_handle("document.PDF")

    def test_can_handle_rejects_non_pdfs(self, fetcher):
        """Test can_handle rejects non-PDFs."""
        assert not fetcher.can_handle("file.txt")
        assert not fetcher.can_handle("https://example.com/file.pdf")

    def test_name(self, fetcher):
        """Test fetcher name."""
        assert fetcher.name == "pdf"


class TestEPUBFetcher:
    """Tests for EPUBFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create EPUBFetcher instance."""
        return EPUBFetcher()

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_file_raises(self, fetcher):
        """Test that nonexistent file raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await fetcher.fetch("/nonexistent/file.epub")

    @pytest.mark.asyncio
    async def test_fetch_non_epub_raises(self, fetcher, sample_text_file):
        """Test that non-EPUB file raises ValueError."""
        with pytest.raises(ValueError, match="Not an EPUB"):
            await fetcher.fetch(str(sample_text_file))

    def test_can_handle_epub_files(self, fetcher):
        """Test can_handle for EPUB files."""
        assert fetcher.can_handle("book.epub")
        assert fetcher.can_handle("document.EPUB")

    def test_can_handle_rejects_non_epubs(self, fetcher):
        """Test can_handle rejects non-EPUBs."""
        assert not fetcher.can_handle("file.txt")
        assert not fetcher.can_handle("https://example.com/book.epub")

    def test_name(self, fetcher):
        """Test fetcher name."""
        assert fetcher.name == "epub"

    def test_extract_text_from_html(self, fetcher, sample_html):
        """Test HTML text extraction."""
        text = fetcher._extract_text_from_html(sample_html.encode())
        assert "Main Title" in text
        assert "This is a paragraph" in text
        assert "console.log" not in text


class TestFetcherManager:
    """Tests for FetcherManager."""

    @pytest.fixture
    def manager(self):
        """Create FetcherManager instance."""
        return FetcherManager()

    def test_get_fetcher_for_url(self, manager):
        """Test getting fetcher for URL."""
        fetcher = manager.get_fetcher("https://example.com")
        assert isinstance(fetcher, URLFetcher)

    def test_get_fetcher_for_pdf(self, manager):
        """Test getting fetcher for PDF."""
        fetcher = manager.get_fetcher("document.pdf")
        assert isinstance(fetcher, PDFFetcher)

    def test_get_fetcher_for_epub(self, manager):
        """Test getting fetcher for EPUB."""
        fetcher = manager.get_fetcher("book.epub")
        assert isinstance(fetcher, EPUBFetcher)

    def test_get_fetcher_for_text_file(self, manager):
        """Test getting fetcher for text file."""
        fetcher = manager.get_fetcher("file.txt")
        assert isinstance(fetcher, FileFetcher)

    def test_get_fetcher_for_plain_text(self, manager):
        """Test getting fetcher for plain text."""
        fetcher = manager.get_fetcher("just some text")
        assert isinstance(fetcher, TextFetcher)

    @pytest.mark.asyncio
    async def test_fetch_delegates_to_fetcher(self, manager, sample_text_file):
        """Test that fetch delegates to correct fetcher."""
        result = await manager.fetch(str(sample_text_file))
        assert "sample text file" in result

    @pytest.mark.asyncio
    async def test_fetch_multiple_success(self, manager, sample_text_file):
        """Test fetching multiple sources successfully."""
        sources = [str(sample_text_file), "plain text content"]
        results = await manager.fetch_multiple(sources)

        assert len(results) == 2
        assert "sample text file" in results[str(sample_text_file)]
        assert results["plain text content"] == "plain text content"

    @pytest.mark.asyncio
    async def test_fetch_multiple_with_errors_raises(self, manager):
        """Test that fetch_multiple raises when any fetch fails."""
        sources = ["/nonexistent/file.txt", "valid text"]

        with pytest.raises(RuntimeError, match="Failed to fetch some sources"):
            await manager.fetch_multiple(sources)
