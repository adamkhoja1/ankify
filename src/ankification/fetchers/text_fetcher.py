"""Direct text input fetcher."""

from .base import BaseFetcher


class TextFetcher(BaseFetcher):
    """Fetcher for direct text input."""

    async def fetch(self, source: str) -> str:
        """Return the text as-is.

        Args:
            source: Text content

        Returns:
            The input text
        """
        if not source or not source.strip():
            raise ValueError("Text content cannot be empty")
        return source.strip()

    def can_handle(self, source: str) -> bool:
        """Text fetcher can handle any string.

        Args:
            source: Source to check

        Returns:
            Always True
        """
        return True

    @property
    def name(self) -> str:
        """Get fetcher name."""
        return "text"
