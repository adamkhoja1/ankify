"""URL content fetcher."""

import httpx
from bs4 import BeautifulSoup

from .base import BaseFetcher


class URLFetcher(BaseFetcher):
    """Fetcher for web content from URLs."""

    def __init__(self, timeout: int = 30) -> None:
        """Initialize URL fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def fetch(self, source: str) -> str:
        """Fetch and extract text from URL.

        Args:
            source: URL to fetch

        Returns:
            Extracted text content

        Raises:
            ValueError: If URL is invalid
            RuntimeError: If request fails
        """
        if not source.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {source}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(source, follow_redirects=True)
                response.raise_for_status()
                html = response.text
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"HTTP error fetching {source}: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Request error fetching {source}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to fetch {source}: {e}") from e

        # Extract text from HTML
        text = self._extract_text(html)

        if not text.strip():
            raise ValueError(f"No text content extracted from {source}")

        return text.strip()

    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML.

        Args:
            html: HTML content

        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "meta", "link"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def can_handle(self, source: str) -> bool:
        """Check if source is a URL.

        Args:
            source: Source to check

        Returns:
            True if source is a valid URL
        """
        return source.startswith(("http://", "https://"))

    @property
    def name(self) -> str:
        """Get fetcher name."""
        return "url"
