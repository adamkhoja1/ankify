"""Base fetcher interface."""

from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    """Abstract base class for content fetchers."""

    @abstractmethod
    async def fetch(self, source: str) -> str:
        """Fetch and return cleaned text content.

        Args:
            source: Source identifier (URL, file path, etc.)

        Returns:
            Cleaned text content

        Raises:
            ValueError: If source is invalid
            RuntimeError: If fetching fails
        """
        pass

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Check if this fetcher can handle the given source.

        Args:
            source: Source identifier to check

        Returns:
            True if this fetcher can process the source
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this fetcher.

        Returns:
            Fetcher name
        """
        pass
