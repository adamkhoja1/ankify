"""Contract tests for Fetcher interface.

These tests verify that all fetchers correctly implement
the BaseFetcher interface.
"""

import inspect
from abc import ABC

import pytest

from ankification.fetchers.base import BaseFetcher
from ankification.fetchers.text_fetcher import TextFetcher
from ankification.fetchers.file_fetcher import FileFetcher
from ankification.fetchers.url_fetcher import URLFetcher
from ankification.fetchers.pdf_fetcher import PDFFetcher
from ankification.fetchers.epub_fetcher import EPUBFetcher


# All concrete fetchers that should implement the interface
FETCHERS = [TextFetcher, FileFetcher, URLFetcher, PDFFetcher, EPUBFetcher]


class TestBaseFetcherContract:
    """Contract tests for BaseFetcher interface definition."""

    def test_base_fetcher_is_abstract(self) -> None:
        """BaseFetcher should be an abstract base class."""
        assert issubclass(BaseFetcher, ABC)

    def test_fetch_is_abstract(self) -> None:
        """fetch should be an abstract method."""
        assert hasattr(BaseFetcher.fetch, "__isabstractmethod__")
        assert BaseFetcher.fetch.__isabstractmethod__

    def test_can_handle_is_abstract(self) -> None:
        """can_handle should be an abstract method."""
        assert hasattr(BaseFetcher.can_handle, "__isabstractmethod__")
        assert BaseFetcher.can_handle.__isabstractmethod__

    def test_name_property_exists(self) -> None:
        """name property should exist."""
        assert "name" in dir(BaseFetcher)

    def test_fetch_signature(self) -> None:
        """fetch should have the correct signature."""
        sig = inspect.signature(BaseFetcher.fetch)
        params = list(sig.parameters.keys())

        # Should have source parameter (excluding self)
        assert "source" in params

    def test_can_handle_signature(self) -> None:
        """can_handle should have the correct signature."""
        sig = inspect.signature(BaseFetcher.can_handle)
        params = list(sig.parameters.keys())

        assert "source" in params


class TestFetcherImplementations:
    """Contract tests verifying all fetchers implement the interface."""

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_inherits_from_base(self, fetcher_class: type) -> None:
        """Each fetcher should inherit from BaseFetcher."""
        assert issubclass(fetcher_class, BaseFetcher)

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_implements_fetch(self, fetcher_class: type) -> None:
        """Each fetcher should implement fetch."""
        assert hasattr(fetcher_class, "fetch")
        method = getattr(fetcher_class, "fetch")
        assert not getattr(method, "__isabstractmethod__", False)

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_implements_can_handle(self, fetcher_class: type) -> None:
        """Each fetcher should implement can_handle."""
        assert hasattr(fetcher_class, "can_handle")
        method = getattr(fetcher_class, "can_handle")
        assert not getattr(method, "__isabstractmethod__", False)

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_implements_name_property(self, fetcher_class: type) -> None:
        """Each fetcher should implement name property."""
        assert hasattr(fetcher_class, "name")

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetch_is_async(self, fetcher_class: type) -> None:
        """fetch should be an async method."""
        method = getattr(fetcher_class, "fetch")
        assert inspect.iscoroutinefunction(method)

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_can_handle_is_sync(self, fetcher_class: type) -> None:
        """can_handle should be a synchronous method (not async)."""
        method = getattr(fetcher_class, "can_handle")
        assert not inspect.iscoroutinefunction(method)


class TestFetcherCanHandleConsistency:
    """Contract tests for can_handle method consistency."""

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_can_handle_returns_bool(self, fetcher_class: type) -> None:
        """can_handle should return a boolean."""
        fetcher = fetcher_class()
        # Test with an arbitrary string
        result = fetcher.can_handle("test")
        assert isinstance(result, bool)

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_can_handle_empty_string(self, fetcher_class: type) -> None:
        """can_handle should handle empty string without error."""
        fetcher = fetcher_class()
        result = fetcher.can_handle("")
        assert isinstance(result, bool)

    def test_file_fetcher_handles_txt_files(self) -> None:
        """FileFetcher should handle .txt files."""
        fetcher = FileFetcher()
        assert fetcher.can_handle("/path/to/file.txt")
        assert fetcher.can_handle("file.txt")

    def test_url_fetcher_handles_http_urls(self) -> None:
        """URLFetcher should handle HTTP/HTTPS URLs."""
        fetcher = URLFetcher()
        assert fetcher.can_handle("http://example.com")
        assert fetcher.can_handle("https://example.com")
        assert not fetcher.can_handle("file.txt")

    def test_pdf_fetcher_handles_pdf_files(self) -> None:
        """PDFFetcher should handle .pdf files."""
        fetcher = PDFFetcher()
        assert fetcher.can_handle("document.pdf")
        assert fetcher.can_handle("/path/to/file.pdf")

    def test_epub_fetcher_handles_epub_files(self) -> None:
        """EPUBFetcher should handle .epub files."""
        fetcher = EPUBFetcher()
        assert fetcher.can_handle("book.epub")
        assert fetcher.can_handle("/path/to/book.epub")


class TestFetcherReturnTypes:
    """Contract tests for return type specifications."""

    def test_fetch_returns_string(self) -> None:
        """fetch return type should be str."""
        sig = inspect.signature(BaseFetcher.fetch)
        assert sig.return_annotation == str

    def test_can_handle_returns_bool(self) -> None:
        """can_handle return type should be bool."""
        sig = inspect.signature(BaseFetcher.can_handle)
        assert sig.return_annotation == bool


class TestFetcherNaming:
    """Contract tests for fetcher naming."""

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_has_name(self, fetcher_class: type) -> None:
        """Each fetcher should have a name property."""
        fetcher = fetcher_class()
        assert hasattr(fetcher, "name")

    @pytest.mark.parametrize("fetcher_class", FETCHERS)
    def test_fetcher_name_is_string(self, fetcher_class: type) -> None:
        """Fetcher name should be a non-empty string."""
        fetcher = fetcher_class()
        assert isinstance(fetcher.name, str)
        assert len(fetcher.name) > 0


class TestFetcherMutualExclusion:
    """Contract tests verifying fetchers handle distinct source types."""

    def test_url_and_file_mutually_exclusive(self) -> None:
        """URL fetcher and file fetcher should have distinct domains."""
        url_fetcher = URLFetcher()
        file_fetcher = FileFetcher()

        # URL should only match URL fetcher
        assert url_fetcher.can_handle("https://example.com/page")
        assert not file_fetcher.can_handle("https://example.com/page")

        # Local file should only match file fetcher
        assert file_fetcher.can_handle("document.txt")
        assert not url_fetcher.can_handle("document.txt")

    def test_pdf_and_txt_mutually_exclusive(self) -> None:
        """PDF and text fetchers should handle different extensions."""
        pdf_fetcher = PDFFetcher()
        file_fetcher = FileFetcher()

        # PDF should be handled by PDF fetcher
        assert pdf_fetcher.can_handle("document.pdf")
        # Text files by file fetcher
        assert file_fetcher.can_handle("document.txt")
