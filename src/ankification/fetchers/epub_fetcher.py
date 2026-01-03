"""EPUB content fetcher."""

from pathlib import Path

import ebooklib  # type: ignore[import-untyped]
from bs4 import BeautifulSoup
from ebooklib import epub

from .base import BaseFetcher


class EPUBFetcher(BaseFetcher):
    """Fetcher for EPUB ebooks."""

    async def fetch(self, source: str) -> str:
        """Extract text from EPUB.

        Args:
            source: EPUB file path

        Returns:
            Extracted text content

        Raises:
            ValueError: If file doesn't exist or is not an EPUB
            RuntimeError: If EPUB cannot be read
        """
        path = Path(source).expanduser()

        if not path.exists():
            raise ValueError(f"File not found: {source}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {source}")

        if path.suffix.lower() not in {".epub"}:
            raise ValueError(f"Not an EPUB file: {source}")

        try:
            book = epub.read_epub(str(path))
            text_parts = []

            # Extract text from all document items
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    text = self._extract_text_from_html(content)
                    if text:
                        text_parts.append(text)

            if not text_parts:
                raise ValueError(f"No text content extracted from EPUB: {source}")

            full_text = "\n\n".join(text_parts)
            return full_text.strip()

        except Exception as e:
            raise RuntimeError(f"Failed to read EPUB {source}: {e}") from e

    def _extract_text_from_html(self, html: bytes) -> str:
        """Extract text from HTML content.

        Args:
            html: HTML content as bytes

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
        """Check if source is an EPUB file.

        Args:
            source: Source to check

        Returns:
            True if source is an EPUB file
        """
        try:
            path = Path(source).expanduser()
            return (
                path.suffix.lower() == ".epub"
                and not source.startswith("http://")
                and not source.startswith("https://")
            )
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Get fetcher name."""
        return "epub"
