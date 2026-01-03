"""Fetcher manager for routing sources to appropriate fetchers."""

from .base import BaseFetcher
from .epub_fetcher import EPUBFetcher
from .file_fetcher import FileFetcher
from .pdf_fetcher import PDFFetcher
from .text_fetcher import TextFetcher
from .url_fetcher import URLFetcher


class FetcherManager:
    """Manages and routes to appropriate content fetchers."""

    def __init__(self) -> None:
        """Initialize fetcher manager with default fetchers."""
        self.fetchers: list[BaseFetcher] = [
            URLFetcher(),
            PDFFetcher(),
            EPUBFetcher(),
            FileFetcher(),
            TextFetcher(),  # TextFetcher should be last as it accepts anything
        ]

    def add_fetcher(self, fetcher: BaseFetcher) -> None:
        """Add a custom fetcher.

        Args:
            fetcher: Fetcher instance to add
        """
        self.fetchers.insert(0, fetcher)

    def get_fetcher(self, source: str) -> BaseFetcher:
        """Get appropriate fetcher for source.

        Args:
            source: Source to fetch from

        Returns:
            Appropriate fetcher instance

        Raises:
            ValueError: If no fetcher can handle the source
        """
        for fetcher in self.fetchers:
            if fetcher.can_handle(source):
                return fetcher

        raise ValueError(f"No fetcher available for source: {source}")

    async def fetch(self, source: str) -> str:
        """Fetch content from source using appropriate fetcher.

        Args:
            source: Source to fetch from

        Returns:
            Extracted text content

        Raises:
            ValueError: If no fetcher can handle the source
            RuntimeError: If fetching fails
        """
        fetcher = self.get_fetcher(source)
        return await fetcher.fetch(source)

    async def fetch_multiple(self, sources: list[str]) -> dict[str, str]:
        """Fetch content from multiple sources.

        Args:
            sources: List of sources to fetch

        Returns:
            Dictionary mapping source to content

        Raises:
            RuntimeError: If any fetch fails (collects all errors)
        """
        results: dict[str, str] = {}
        errors: dict[str, Exception] = {}

        for source in sources:
            try:
                content = await self.fetch(source)
                results[source] = content
            except Exception as e:
                errors[source] = e

        if errors:
            error_msg = "\n".join(
                f"{source}: {error}" for source, error in errors.items()
            )
            raise RuntimeError(f"Failed to fetch some sources:\n{error_msg}")

        return results
