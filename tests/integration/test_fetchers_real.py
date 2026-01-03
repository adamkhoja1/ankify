"""Integration tests for fetchers with real network requests.

These tests make actual HTTP requests and require network access.
Some tests may be slow or flaky depending on network conditions.

Run with: pytest tests/integration/test_fetchers_real.py -v
"""

import pytest

from ankification.fetchers.manager import FetcherManager
from ankification.fetchers.url_fetcher import URLFetcher


@pytest.mark.integration
class TestURLFetcherReal:
    """Integration tests for URLFetcher with real HTTP requests."""

    @pytest.fixture
    def fetcher(self) -> URLFetcher:
        """Create real URL fetcher."""
        return URLFetcher()

    async def test_fetch_wikipedia_page(self, fetcher: URLFetcher) -> None:
        """URLFetcher should retrieve content from Wikipedia."""
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

        content = await fetcher.fetch(url)

        assert content is not None
        assert len(content) > 1000
        assert "Python" in content
        assert "programming" in content.lower()

    async def test_fetch_returns_text_content(self, fetcher: URLFetcher) -> None:
        """URLFetcher should return readable text, not raw HTML."""
        url = "https://en.wikipedia.org/wiki/Flashcard"

        content = await fetcher.fetch(url)

        # Should not contain raw HTML tags
        assert "<html>" not in content.lower()
        assert "<body>" not in content.lower()
        # Should contain readable content
        assert "flashcard" in content.lower() or "flash card" in content.lower()

    async def test_fetch_handles_redirects(self, fetcher: URLFetcher) -> None:
        """URLFetcher should follow redirects."""
        # Wikipedia short URLs redirect
        url = "https://en.wikipedia.org/wiki/ML"

        content = await fetcher.fetch(url)

        assert content is not None
        assert len(content) > 100

    async def test_fetch_invalid_url_raises(self, fetcher: URLFetcher) -> None:
        """URLFetcher should raise on invalid URLs."""
        with pytest.raises(Exception):  # Could be various error types
            await fetcher.fetch("https://this-domain-definitely-does-not-exist-12345.com")

    async def test_fetch_404_raises(self, fetcher: URLFetcher) -> None:
        """URLFetcher should raise on 404 responses."""
        url = "https://en.wikipedia.org/wiki/This_Page_Definitely_Does_Not_Exist_12345"

        with pytest.raises(Exception):
            await fetcher.fetch(url)


@pytest.mark.integration
class TestFetcherManagerReal:
    """Integration tests for FetcherManager with real operations."""

    @pytest.fixture
    def manager(self) -> FetcherManager:
        """Create fetcher manager."""
        return FetcherManager()

    async def test_fetch_from_url(self, manager: FetcherManager) -> None:
        """FetcherManager should detect and fetch URLs."""
        url = "https://en.wikipedia.org/wiki/Anki_(software)"

        content = await manager.fetch(url)

        assert content is not None
        assert "Anki" in content or "anki" in content.lower()
        assert "spaced repetition" in content.lower() or "flashcard" in content.lower()

    async def test_fetch_from_file(self, manager: FetcherManager, tmp_path) -> None:
        """FetcherManager should read local files."""
        test_file = tmp_path / "test_content.txt"
        test_file.write_text("This is test content for flashcard generation.")

        content = await manager.fetch(str(test_file))

        assert content == "This is test content for flashcard generation."

    async def test_fetch_raw_text(self, manager: FetcherManager) -> None:
        """FetcherManager should pass through raw text."""
        raw_text = "This is raw text content, not a URL or file path."

        content = await manager.fetch(raw_text)

        assert content == raw_text

    def test_fetch_detects_source_type(self, manager: FetcherManager) -> None:
        """FetcherManager should correctly identify source types via get_fetcher."""
        # FetcherManager uses get_fetcher() to select appropriate fetcher
        # Test that it can get fetchers for different source types
        url_fetcher = manager.get_fetcher("https://example.com")
        file_fetcher = manager.get_fetcher("/path/to/file.txt")

        assert url_fetcher is not None
        assert file_fetcher is not None
        # They should be different fetcher types
        assert type(url_fetcher).__name__ != type(file_fetcher).__name__


@pytest.mark.integration
class TestFetcherContentQuality:
    """Tests for content extraction quality."""

    @pytest.fixture
    def fetcher(self) -> URLFetcher:
        """Create web fetcher."""
        return URLFetcher()

    async def test_extracts_main_content(self, fetcher: URLFetcher) -> None:
        """URLFetcher should extract main content, not navigation/ads."""
        url = "https://en.wikipedia.org/wiki/Spaced_repetition"

        content = await fetcher.fetch(url)

        # Should have substantial educational content
        assert len(content) > 500

        # Should contain topic-relevant terms
        content_lower = content.lower()
        assert "spaced repetition" in content_lower or "memory" in content_lower

    async def test_handles_different_encodings(self, fetcher: URLFetcher) -> None:
        """URLFetcher should handle different character encodings."""
        # Wikipedia handles UTF-8 content well
        url = "https://en.wikipedia.org/wiki/Unicode"

        content = await fetcher.fetch(url)

        assert content is not None
        assert "Unicode" in content or "unicode" in content.lower()
